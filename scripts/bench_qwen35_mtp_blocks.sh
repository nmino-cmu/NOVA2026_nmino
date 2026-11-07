#!/bin/bash
# ponytail: sweep draft block sizes once weights exist; pick max wall-tok/s from HTTP bench
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${QWEN35_MTP_PORT:-18092}"
URL="http://127.0.0.1:${PORT}/v1/chat/completions"
MODEL_DIR="$HOME/.lmstudio/models/mlx-community/Qwen3.6-35B-A3B-6bit"
DRAFT_DIR="$HOME/.lmstudio/models/mlx-community/Qwen3.6-35B-A3B-MTP-4bit"
test -d "$MODEL_DIR" && test -f "$DRAFT_DIR/model.safetensors"

best_b=2
best_t=0
for b in 2 3 4 5; do
  export QWEN35_MTP_BLOCK="$b"
  pkill -f "qwen_mtp_http.py.*--port ${PORT}" 2>/dev/null || true
  sleep 2
  "$ROOT/scripts/qwen35_mtp_server.sh" >>/tmp/qwen35_mtp.log 2>&1 &
  srv=$!
  for _ in $(seq 1 120); do
    curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null && break
    sleep 5
  done
  curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null || { echo "block=$b server_timeout"; kill $srv 2>/dev/null; continue; }
  curl -sf "$URL" -H 'Content-Type: application/json' -d '{"model":"x","messages":[{"role":"user","content":"hi"}],"max_tokens":8,"enable_thinking":false}' >/dev/null || true
  out=$(curl -sf "$URL" -H 'Content-Type: application/json' -d "$(cat <<EOF
{"model":"x","messages":[{"role":"system","content":"Direct list only. /no_think"},{"role":"user","content":"List 60 short nouns, one per line, numbered 1) through 60)."}],"max_tokens":512,"temperature":0,"enable_thinking":false}
EOF
)")
  comp=$(python3 -c "import json,sys; u=json.loads(sys.argv[1]).get('usage',{}); print(u.get('completion_tokens',0))" "$out")
  wall=$(rg -o 'decode=[0-9]+ @([0-9.]+) tok/s' /tmp/qwen35_mtp.log | tail -1 | rg -o '[0-9.]+$' || echo "")
  if [[ -z "$wall" ]]; then
    wall=$(python3 -c "import json,sys; print(json.loads(sys.argv[1]).get('stats',{}).get('generation_tps',''))" "$out" 2>/dev/null || true)
  fi
  tok_s=$(tail -20 /tmp/qwen35_mtp.log | rg 'wall-tok/s' | tail -1 | rg -o '[0-9.]+ wall-tok/s' | awk '{print $1}' || true)
  echo "block=$b completion_tokens=$comp wall_tok_s=${tok_s:-na}"
  if python3 -c "import sys; sys.exit(0 if float('${tok_s:-0}') > float('${best_t}') else 1)"; then
    best_b=$b
    best_t=${tok_s:-0}
  fi
  kill $srv 2>/dev/null || true
  wait $srv 2>/dev/null || true
  sleep 3
done
echo "BEST_BLOCK=$best_b BEST_WALL_TOK_S=$best_t"
