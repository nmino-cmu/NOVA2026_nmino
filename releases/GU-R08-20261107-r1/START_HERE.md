# Ghost Users GU-R08-20261107-r1

Source revision `9c6fb4735de40c90ff68b86d71f1908a76f394ce`.

This folder is a runnable copy. It does not include an API key. Put `OPENROUTER_API_KEY` in `source/.env` only on the machine that should call OpenRouter. Playback of recorded runs does not need a key. The loopback echo model does not need a key.

## Install

From `source/`:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/manage.py setup
.venv/bin/python scripts/manage.py start
```

- Ghost Users: http://127.0.0.1:8787/
- Orbit Supply: http://127.0.0.1:8788/
- Harbor Goods: http://127.0.0.1:8789/
- Echo model: http://127.0.0.1:8791/v1/models

Stop with `.venv/bin/python scripts/manage.py stop`. That stops only processes this checkout started.

The built interface is already in `frontend/dist`. `npm ci && npm run build` inside `frontend/` rebuilds it.

## What is verified

- Adaptive Orbit search passed an automated replay.
- Express on `orbit-fixed-v1` passed in one action (`run_5acca512515c41a2`), then the fixture returned to the buggy build.
- Harbor Goods checkout measured 4 interactions. Orbit’s shortcut is 3.
- Keyboard Enter confirmation passed.
- `echo-local` returned a structured completion.

No demo video is in this folder. The earlier frozen package `GU-R01-20261107-r4` is a separate directory and is not inside this snapshot.
