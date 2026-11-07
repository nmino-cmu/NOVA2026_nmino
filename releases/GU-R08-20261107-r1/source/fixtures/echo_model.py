"""Local OpenAI-compatible echo. It returns product data and never code."""

from __future__ import annotations

import os

from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"ok": True, "model": "echo-local"}


@app.get("/v1/models")
def models():
    return {"data": [{"id": "echo-local"}]}


@app.post("/v1/chat/completions")
def chat():
    return {
        "model": "echo-local",
        "choices": [{"message": {"content": '{"word":"ok"}'}}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("ECHO_PORT", "8791")))
