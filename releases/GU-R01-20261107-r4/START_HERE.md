# GU-R01-20261107-r4

Stage R01. Ghost Users investigates a browser task with a local browser, keeps the witnessed history, and checks that history again from a fresh start.

Tested on macOS arm64 with Python 3.12 and Node 25. The receiving machine needs Python 3.11 or newer, Node 20 or newer for a source build, and network access only for the first dependency install and for a live model run.

## Install

```bash
cd source
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

`uv sync` also works when uv is installed. The frontend is already built in `source/frontend/dist`. To rebuild it: `cd source/frontend && npm ci && npm run build`.

## Fresh live run

Copy `source/.env.example` to `source/.env` and set `OPENROUTER_API_KEY` on the server. Do not commit that file.

```bash
cd source
python scripts/manage.py setup
python scripts/manage.py start
```

- Ghost Users: http://127.0.0.1:8787/
- Orbit Supply, the controlled demo shop: http://127.0.0.1:8788/

`python scripts/manage.py stop` stops only the processes this checkout started. `python scripts/manage.py reset-fixture` clears the disposable `manual` namespace on Orbit Supply: cart, commits, and the reset generation. It does not place an order.

## Recorded playback

Playback does not call a model and does not need a key.

```bash
cd source
GHOST_DATA_DIR="$PWD/../evidence/playback-data" python scripts/manage.py start
```

Open http://127.0.0.1:8787/playback/run_c6252c9a4a6e4ba2

The ribbon reads `Recorded investigation`. Playback does not dispatch browser actions.

## Included evidence

- Live model investigation `run_c6252c9a4a6e4ba2`: verified 6-interaction route on build `orbit-buggy-v1`.
- Fixture regression `run_b1a8b04516204ce7`: the five-step catalog route, passed.
- Fixture regression `run_f14d218e9d8c4dff`: Express Nova Mug, replay failed because the authoritative cart stayed empty.

## Limits

This release follows one witnessed path and then replays it. It does not search for a shorter route. Orbit Supply is a controlled demo, not a customer store. A fresh checkout does not prove every operating system. Video was not recorded in this package. See `demo/recording-agent-prompt.md`.
