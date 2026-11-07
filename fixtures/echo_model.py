"""Local OpenAI-compatible model. It picks from the candidate list it is shown."""

from __future__ import annotations

import json
import os

from fastapi import FastAPI, Request

app = FastAPI()

# The local stand-in prefers a control whose name is in this list. It never invents a control.
_PREFERENCE = (
    "Continue to checkout",
    "Add to cart",
    "View cart",
    "Nova Mug",
    "Catalog",
    "Nova Mug checkout",
    "Quick order",
    "More",
)


@app.get("/health")
def health():
    return {"ok": True, "model": "echo-local"}


@app.get("/v1/models")
def models():
    return {"data": [{"id": "echo-local"}]}


@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    text = "".join((message.get("content") or "") for message in body.get("messages") or [])
    content = '{"word":"ok"}'
    if '"candidates"' in text:
        start, end = text.find("{"), text.rfind("}")
        try:
            payload = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            payload = {}
        pairs = [(item.get("id"), item.get("name")) for item in payload.get("candidates") or [] if item.get("id")]
        chosen = pairs[0][0] if pairs else None
        for want in _PREFERENCE:
            match = next((cid for cid, name in pairs if name == want), None)
            if match:
                chosen = match
                break
        content = json.dumps(
            {"candidate_id": chosen, "rationale": "Selected an eligible control from the supplied list."}
        )
    return {
        "model": "echo-local",
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 8, "total_tokens": 19},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("ECHO_PORT", "8791")))
