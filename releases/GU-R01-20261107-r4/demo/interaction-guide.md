# Interaction guide — GU-R01-20261107-r4

| Field | Value |
|---|---|
| Release | GU-R01-20261107-r4 |
| Source | af5a9bca1902c0c26900a3a5c0f9cafa8cf28009 |
| Build | orbit-buggy-v1 |
| Live run | run_c6252c9a4a6e4ba2 |
| Express check | run_f14d218e9d8c4dff |
| Ordinary check | run_b1a8b04516204ce7 |
| Model | anthropic/claude-sonnet-4.6, text planner |
| Start | `cd source && python scripts/manage.py setup && python scripts/manage.py start` |
| URLs | http://127.0.0.1:8787/ and http://127.0.0.1:8788/ |
| Playback | `GHOST_DATA_DIR=../evidence/playback-data` then http://127.0.0.1:8787/playback/run_c6252c9a4a6e4ba2 |
| Capture | 1920x1080 video, app at 100% zoom, fixture viewport 1440x900 |
| Initial state | Logged out, empty cart, no orders. Reset before a live shot. |
| Setup | Use Orbit Supply preset, continue through Goal, Budget, Review, Launch investigation |
| Reveal | Select Express Nova Mug in the witness, then open `run_f14d218e9d8c4dff` and read the failed cart check |
| Slides | presentation/slides.pdf and slide-01.png through slide-04.png |
| Output | GU-R01-20261107-r4-demo-1920x1080.mp4 |
| Recovery | If inference stalls, cut to the recorded playback. If reset fails, do not claim a new live run. |
