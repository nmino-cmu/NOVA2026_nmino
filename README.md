# Ghost Users

Ghost Users investigates a browser task with a local browser, keeps the witnessed history, and checks the result again from a fresh start. The answer it stands behind is the best verified workflow under the declared conditions and budget.

Orbit Supply is a controlled demo shop, not a customer deployment. The task is to reach checkout with exactly one Nova Mug and not place an order. A success-looking Express screen is not treated as success unless the registered cart check passes.

## Live demo

Try the public build without cloning this repository:

1. Open **https://nickmino.com/nova2026** (the same app also answers at `/NOVA2026` and `/Nova2026` on that host).
2. Enter any public `http://` or `https://` page URL and start an investigation.

That site runs a live Ghost Users backend against the link you supply. It is not a canned recording or a fixed shop preset. For the Orbit Supply controlled checkout task and full local development, use the steps below.

## Run locally

```bash
uv sync
uv run python scripts/manage.py setup
uv run python scripts/manage.py start
```

A standard virtualenv works too: `python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then `python scripts/manage.py setup`.

- Ghost Users: `http://127.0.0.1:8787/`
- Orbit Supply: `http://127.0.0.1:8788/`
- UI dev server: `cd frontend && npm ci && npm run dev` then `http://127.0.0.1:5173/`

`python scripts/manage.py stop` stops only the processes it started. `reset-fixture` clears the disposable `manual` namespace. `playback RUN_ID` prints the recorded-run URL and does not launch an investigation.

Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY` for a live model investigation. Fixture regression checks and recorded playback do not need it. The key stays on the server.

This tree is the R01 investigation: setup, a model-chosen browser action, evidence, and an independent replay. Later stages are listed in `docs/continuation.md` and are not in the navigation.
