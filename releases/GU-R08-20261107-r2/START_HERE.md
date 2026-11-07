# Ghost Users GU-R08-20261107-r2

Source revision `c8ab5a3d4d6d801c21960689080fcffb1d1ad621`.

This folder is a runnable copy of the later checkpoints. It does not include an API key. Put `OPENROUTER_API_KEY` in `source/.env` only on the machine that should call OpenRouter. Playback and the loopback echo model do not need a key.

The frozen R01 package stays `GU-R01-20261107-r4`. It is not inside this folder.

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

## Checkpoints in this folder

- R02: adaptive search records fairness, tuple, and exclusion decisions. The inspector lists them.
- R03: a failed verification can become a recommendation and a brief. The brief is not permission to edit a repository. Express on `orbit-fixed-v1` is a full replay.
- R04: an exact action is dispatched once, and a candidate that cannot beat a verified route is excluded.
- R05: one comparison measures Harbor Goods (4 interactions) and the Orbit shortcut (3).
- R06: the loopback model can complete an investigation by choosing an id from the list it is shown.
- R07: keyboard Enter confirmation, run search, and a build change that marks the older verification stale.
- R08: two investigations can run together, and separate fixture namespaces keep separate carts.

The automated suite on this revision was 24 passed. No demo video is in this folder.
