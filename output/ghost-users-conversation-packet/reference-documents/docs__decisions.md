# Decisions

- 2026-11-07 12:47 America/New_York: deadline stays 17:00. About 252 minutes remained at first clock read.
- Runtime is Python 3.12. The default `python3` is 3.14; 3.12 is the locked project interpreter. Node is the installed v25.
- Ports 8787, 8788, and 5173 were free. Both servers bind to 127.0.0.1.
- Qwen on 127.0.0.1:18092 was not listening. It was not started. A 35B weight load would contend with the browser on a 48 GB machine.
- R01 explores one forward history, then replays it from a new reset. The lexicographic frontier waits for R02. The preset's acceptable interaction count is the envelope 12, not a hidden 5-step answer.
- Planner requests send structured controls and visible text. Screenshot bytes are evidence. Image input is probed separately and is off unless `GHOST_PLANNER_IMAGES=1`.
- The UI refetches server snapshots. It does not add its own usage totals.
- Express failure is an unsent cart mutation discarded by navigation, then a checkout refresh at 900 ms. The fixed build, `orbit-fixed-v1`, waits for the commit. The default build is `orbit-buggy-v1`.
- Figma was not available as a design blocker. `docs/ui.md` is the working visual sheet until a verified Figma file exists.
