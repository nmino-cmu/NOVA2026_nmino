#!/bin/bash
# 35B 6-bit target + MTP-4bit drafter via mlx_vlm (speculative decode), loopback only.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HTTP_PY="/Users/nicholasmino/ProgrammingFiles/Local_AI_Systems/Gateway Router/scripts/qwen_mtp_http.py"
AMPHIBIAN="$HOME/.lmstudio/extensions/backends/vendor/_amphibian"
MODEL="$HOME/.lmstudio/models/mlx-community/Qwen3.6-35B-A3B-6bit"
DRAFT="$HOME/.lmstudio/models/mlx-community/Qwen3.6-35B-A3B-MTP-4bit"
HOST="127.0.0.1"
PORT="${QWEN35_MTP_PORT:-18092}"
# ponytail: local A/B 2026-11-07: block 3 beat 2/4/5 on 512-token list decode (~66 tok/s)
BLOCK="${QWEN35_MTP_BLOCK:-3}"
KV="${QWEN35_MTP_KV:-32768}"

for d in "$MODEL" "$DRAFT"; do
  test -d "$d" || { echo "MISSING_WEIGHTS $d" >&2; exit 1; }
done
test -f "$HTTP_PY" || { echo "MISSING $HTTP_PY" >&2; exit 1; }

best=""
best_n=-1
for p in "$AMPHIBIAN"/app-mlx-generate-mac14-arm64@*/bin/python; do
  n="${p#*@}"; n="${n%%/*}"
  if (( n > best_n )); then best_n=$n; best="$p"; fi
done
test -n "$best" || { echo "mlx_vlm python not under $AMPHIBIAN" >&2; exit 1; }

exec "$best" "$HTTP_PY" \
  --host "$HOST" \
  --port "$PORT" \
  --model "$MODEL" \
  --draft-model "$DRAFT" \
  --draft-block-size "$BLOCK" \
  --max-kv-size "$KV"
