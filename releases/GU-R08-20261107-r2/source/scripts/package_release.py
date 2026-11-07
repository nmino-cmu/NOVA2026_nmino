#!/usr/bin/env python3
"""Build one immutable Ghost Users release candidate and validate it in a new directory."""

from __future__ import annotations

import hashlib
import re
import sys
import json
import os
import shutil
import sqlite3
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "af5a9bca1902c0c26900a3a5c0f9cafa8cf28009"
RELEASE_ID = "GU-R01-20261107-r4"
STAGE = "R01"
LIVE_RUN = "run_c6252c9a4a6e4ba2"
EXPRESS_RUN = "run_f14d218e9d8c4dff"
ORDINARY_RUN = "run_b1a8b04516204ce7"
ZONE = ZoneInfo("America/New_York")


def now() -> str:
    return datetime.now(ZONE).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd, env=env)


def load_run(db: Path, run_id: str) -> dict:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT payload, status FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise SystemExit(f"missing run {run_id}")
    payload = json.loads(row["payload"])
    payload["status"] = row["status"]
    return payload


def main() -> None:
    candidate = ROOT / "releases" / RELEASE_ID
    if candidate.exists():
        raise SystemExit(f"{candidate} already exists; create a new revision instead of editing it")
    data = Path(os.environ.get("GHOST_DATA_DIR") or (ROOT / ".data"))
    db = data / "ghost.sqlite3"
    live = load_run(db, LIVE_RUN)
    created = now()
    source = candidate / "source"
    source.parent.mkdir(parents=True)
    archive = subprocess.check_output(["git", "archive", "--format=tar", SOURCE_REVISION], cwd=ROOT)
    source.mkdir()
    subprocess.run(["tar", "-x", "-C", str(source)], input=archive, check=True)
    if (source / ".git").exists() or (source / ".env").exists():
        raise SystemExit("archive contained git metadata or an env file")

    env = os.environ.copy()
    env.pop("OPENROUTER_API_KEY", None)
    run(["npm", "ci"], source / "frontend", env)
    run(["npm", "run", "build"], source / "frontend", env)
    shutil.rmtree(source / "frontend" / "node_modules")

    playback = candidate / "evidence" / "playback-data"
    playback.mkdir(parents=True)
    checkpoint = sqlite3.connect(db)
    checkpoint.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    checkpoint.close()
    shutil.copy2(db, playback / "ghost.sqlite3")
    evidence_src = data / "evidence"
    if evidence_src.is_dir():
        shutil.copytree(evidence_src, playback / "evidence", symlinks=False)
    for forbidden in ("orbit.token", "audit"):
        target = playback / forbidden
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()

    captures = candidate / "presentation" / "captures"
    captures.mkdir(parents=True)
    capture_ui(captures)
    write_materials(candidate, live, created)
    render_deck(candidate)
    scan_candidate(candidate)
    hashes = hash_tree(candidate)
    manifest_path = candidate / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_body(created, hashes), indent=2) + "\n", encoding="utf-8")
    write_index(sha256_file(manifest_path), created, "candidate")
    subprocess.call([sys.executable, "scripts/manage.py", "stop"], cwd=ROOT)
    validate(candidate)
    print(f"validated {candidate}")


def capture_ui(captures: Path) -> None:
    shots = {
        "01-setup.png": "http://127.0.0.1:8787/",
        "02-workspace.png": f"http://127.0.0.1:8787/runs/{LIVE_RUN}",
        "03-witness.png": f"http://127.0.0.1:8787/runs/{LIVE_RUN}",
        "04-stage-result.png": f"http://127.0.0.1:8787/runs/{EXPRESS_RUN}",
        "playback.png": f"http://127.0.0.1:8787/playback/{LIVE_RUN}",
    }
    try:
        urllib.request.urlopen("http://127.0.0.1:8787/api/health", timeout=2)
    except Exception:
        subprocess.check_call([sys.executable, "scripts/manage.py", "start"], cwd=ROOT)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for name, url in shots.items():
            page.goto(url, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(500)
            if name == "01-setup.png":
                page.get_by_role("button", name="Use Orbit Supply preset").click()
                page.get_by_role("button", name="Continue").click()
                page.get_by_role("button", name="Continue").click()
                page.wait_for_timeout(300)
            page.screenshot(path=str(captures / name))
        browser.close()


def write_materials(candidate: Path, live: dict, created: str) -> None:
    demo = candidate / "demo"
    presentation = candidate / "presentation"
    submission = candidate / "submission"
    for folder in (demo, presentation, submission, candidate / "presentation" / "editable-local-source"):
        folder.mkdir(parents=True, exist_ok=True)
    (candidate / "START_HERE.md").write_text(start_here(), encoding="utf-8")
    (candidate / "CAPABILITIES_AND_LIMITATIONS.md").write_text(capabilities(live), encoding="utf-8")
    (candidate / "checks.json").write_text(json.dumps(checks(created), indent=2) + "\n", encoding="utf-8")
    (demo / "storyboard.md").write_text(storyboard(live), encoding="utf-8")
    (demo / "interaction-guide.md").write_text(guide(live), encoding="utf-8")
    (demo / "recording-agent-prompt.md").write_text(recording_prompt(), encoding="utf-8")
    (demo / "voiceover-notes.md").write_text(voiceover(live), encoding="utf-8")
    (demo / "shot-list.json").write_text(json.dumps(shots(), indent=2) + "\n", encoding="utf-8")
    (demo / "recovery.md").write_text(recovery(), encoding="utf-8")
    (presentation / "speaker-notes.md").write_text(voiceover(live), encoding="utf-8")
    (presentation / "source-reference.json").write_text(
        json.dumps(
            {
                "figma_source": "unavailable",
                "fallback": "presentation/editable-local-source/deck.html",
                "note": "Slides were rendered locally. There is no Figma file for this release.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (submission / "description.md").write_text(description(live), encoding="utf-8")
    (submission / "attribution.md").write_text(
        "Ghost Users application code in this release is MIT licensed. Third-party packages keep their own licenses. See source/THIRD_PARTY_NOTICES.md.\n",
        encoding="utf-8",
    )
    (submission / "measured-results.csv").write_text(measured_csv(), encoding="utf-8")
    deck = deck_html(live)
    (presentation / "editable-local-source" / "deck.html").write_text(deck, encoding="utf-8")


def start_here() -> str:
    return f"""# {RELEASE_ID}

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
GHOST_DATA_DIR=\"$PWD/../evidence/playback-data\" python scripts/manage.py start
```

Open http://127.0.0.1:8787/playback/{LIVE_RUN}

The ribbon reads `Recorded investigation`. Playback does not dispatch browser actions.

## Included evidence

- Live model investigation `{LIVE_RUN}`: verified 6-interaction route on build `orbit-buggy-v1`.
- Fixture regression `{ORDINARY_RUN}`: the five-step catalog route, passed.
- Fixture regression `{EXPRESS_RUN}`: Express Nova Mug, replay failed because the authoritative cart stayed empty.

## Limits

This release follows one witnessed path and then replays it. It does not search for a shorter route. Orbit Supply is a controlled demo, not a customer store. A fresh checkout does not prove every operating system. Video was not recorded in this package. See `demo/recording-agent-prompt.md`.
"""


def capabilities(live: dict) -> str:
    return f"""# Capabilities and limitations

Shipped and reachable in the UI:

- Guided setup for Orbit Supply and for a supplied URL with a visible milestone.
- One model-chosen browser path. The model may return only a candidate id from the controls on the page.
- Independent replay from a new fixture reset. A pass requires the registered cart check, not a success-looking screen.
- Fixture regression checks for the ordinary, shortcut, and Express routes. They are labeled fixture checks.
- Run library, evidence screenshots, and read-only playback.
- Stop. A stop during setup ends as `stopped_by_user`.

The accepted live run is `{LIVE_RUN}`, status `{live.get("status")}`, stop `{live.get("stopReason")}`, build `{live.get("buildId")}`.

Not in this release: adaptive search, prefix exclusion, recommendation review, retest after a fix, competitor comparison, a custom model endpoint, keyboard-only checks, and multiple runtime workers.

Provider: OpenRouter `anthropic/claude-sonnet-4.6` for browser planning, text only. Screenshots are stored and are not sent to the model. No dollar cap is configured; reported spend is shown and unknown spend stays unknown. Playback does not need the key.

Restoration is the Orbit reset adapter for the demo shop, and a fresh browser context for a supplied page. A supplied page without a server reset is not a strict comparable replay when restoration is unknown.
"""


def checks(created: str) -> list[dict]:
    return [
        {
            "name": "pytest-r01",
            "command": "uv run pytest -q tests",
            "result": "passed",
            "at": "2026-11-07T13:18:00-05:00",
            "detail": "11 tests: units, Orbit routes, ordinary/shortcut/express replay, supplied milestone.",
        },
        {
            "name": "openrouter-structured-completion",
            "result": "passed",
            "at": "2026-11-07T13:20:00-05:00",
            "detail": "anthropic/claude-sonnet-4.6 returned word=ok. Cost reported. Key not printed.",
        },
        {
            "name": "live-model-investigation",
            "result": "passed",
            "at": "2026-11-07T13:22:00-05:00",
            "run_id": LIVE_RUN,
            "detail": "Verified 6 interactions. Replay passed. Express was the first click and did not by itself satisfy the cart check.",
        },
        {
            "name": "express-regression",
            "result": "passed",
            "at": "2026-11-07T13:21:00-05:00",
            "run_id": EXPRESS_RUN,
            "detail": "Expected failure. Authoritative cart was not one Nova Mug.",
        },
        {
            "name": "stop",
            "result": "passed",
            "at": "2026-11-07T13:26:00-05:00",
            "run_id": "run_38c72d89d7c34524",
            "detail": "stopped_by_user before a model request.",
        },
        {
            "name": "clean-start",
            "result": "pending-validation",
            "at": created,
            "detail": "Filled by the validation copy.",
        },
    ]


def storyboard(live: dict) -> str:
    return f"""# 300-second storyboard — {RELEASE_ID}

| Time | Picture | Narration purpose |
|---|---|---|
| 00:00–00:18 | Slide 1 | A success screen is not a verified workflow |
| 00:18–00:55 | New investigation, Orbit preset, review, launch | What the developer declares |
| 00:55–01:45 | Playback of `{LIVE_RUN}` with the recorded ribbon | Local investigation and the budget |
| 01:45–02:05 | Slide 2 | Witness, then a fresh replay |
| 02:05–03:20 | Open the 6-step witness, then the failed Express check `{EXPRESS_RUN}` | The verified route and the trap |
| 03:20–04:05 | Evidence screenshot and usage | The result is inspectable |
| 04:05–04:30 | Slide 3 | 6 verified interactions, one limitation |
| 04:30–04:45 | Reopen the run from the library | Persisted result |
| 04:45–05:00 | Slide 4 | This release and what it does not claim |

Run status `{live.get("status")}`, stop `{live.get("stopReason")}`. Do not invent a shorter discovery. This run's verified cost is 6 interactions.
"""


def guide(live: dict) -> str:
    return f"""# Interaction guide — {RELEASE_ID}

| Field | Value |
|---|---|
| Release | {RELEASE_ID} |
| Source | {SOURCE_REVISION} |
| Build | orbit-buggy-v1 |
| Live run | {LIVE_RUN} |
| Express check | {EXPRESS_RUN} |
| Ordinary check | {ORDINARY_RUN} |
| Model | anthropic/claude-sonnet-4.6, text planner |
| Start | `cd source && python scripts/manage.py setup && python scripts/manage.py start` |
| URLs | http://127.0.0.1:8787/ and http://127.0.0.1:8788/ |
| Playback | `GHOST_DATA_DIR=../evidence/playback-data` then http://127.0.0.1:8787/playback/{LIVE_RUN} |
| Capture | 1920x1080 video, app at 100% zoom, fixture viewport 1440x900 |
| Initial state | Logged out, empty cart, no orders. Reset before a live shot. |
| Setup | Use Orbit Supply preset, continue through Goal, Budget, Review, Launch investigation |
| Reveal | Select Express Nova Mug in the witness, then open `{EXPRESS_RUN}` and read the failed cart check |
| Slides | presentation/slides.pdf and slide-01.png through slide-04.png |
| Output | {RELEASE_ID}-demo-1920x1080.mp4 |
| Recovery | If inference stalls, cut to the recorded playback. If reset fails, do not claim a new live run. |
"""


def recording_prompt() -> str:
    return f"""You are preparing and recording Ghost Users release {RELEASE_ID}. The user has selected the release at [user-selected absolute path]. Your inspection authorization covers only that release and your own output directory. Do not list its parent, discover siblings, open other releases, inspect the development checkout, or modify the frozen original.

Read this release’s START_HERE, manifest, checks, capabilities, demo interaction guide, storyboard and speaker notes. Make a disposable execution copy in a new recording-output directory outside the frozen source. Install and run from that copy. Put environments, data, browser profiles, screenshots, source captures and exported video outside the frozen original. Do not write credentials into tracked or frozen files.

Preflight actual Python/Node/browser compatibility, disk/memory, screen/browser control, screen-recording permission, fonts, capture dimensions and available recording/encoding tools. Ask only for a genuinely missing credential or OS permission required for the chosen capture mode.

Confirm the health/build identity and checked fixture reset. Reproduce the guide’s initial state and one accepted result path. Test included genuine playback with no inference key. For fresh-live capture, configure credentials separately and use the release’s model and task. Never weaken checks to rescue a shot.

Follow the included 300-second, four-slide storyboard at 1920x1080, 30 fps. Use 100% browser zoom. Move the cursor deliberately and leave space for the user’s voiceover. Do not synthesize or impersonate the user's voice.

Prefer actual application interaction. For predictable pacing use the included genuine event playback with the visible Recorded investigation ribbon, run id {LIVE_RUN}, and build orbit-buggy-v1. If fresh inference stalls, cut to that recorded run. Never invent browser activity.

When the user supplies a narration file, combine it and inspect synchronization. If narration is not supplied, label the output visual-only.

Export {RELEASE_ID}-demo-1920x1080.mp4. Target 300 seconds and never exceed 300.0 seconds. Inspect the file by playing it. Save recording-verification.md. State “video ready” only after a playable file exists and has been inspected. Leave the frozen source untouched. Do not submit or upload without the user's explicit instruction.
"""


def voiceover(live: dict) -> str:
    return f"""# Speaker notes — {RELEASE_ID}

Opening: Ghost Users investigates browser workflows and keeps the evidence behind its answers. Here the task is to reach checkout with exactly one mug, without placing an order.

Setup: We declare the starting state, allowed interactions, goal checks and budget before the run.

Investigation: The browser runs locally. The model picks one of the controls on the page. Ordinary local code stores the observations, the costs, and the history.

Verification: This result is one witnessed sequence. Ghost Users resets the shop and replays those exact actions. The live run {LIVE_RUN} verified 6 interactions. The first click was Express Nova Mug. The cart check did not pass on that click. The later catalog steps did, and the whole sequence passed on replay. Stop reason: {live.get("stopReason")}.

Express check: A separate fixture check repeats only Express. The screen can say checkout is ready. The registered check fails because the cart is empty. That check is {EXPRESS_RUN}.

Close: This release is self-hostable and includes its evidence. These results apply to this task, this build, and this budget. This release does not search for a shorter route, and it does not claim the six-step path is optimal.
"""


def recovery() -> str:
    return """# Recovery

- Live inference timeout: switch to the named playback URL. Keep the Recorded investigation ribbon visible.
- Missing credential: playback still runs. Do not start a fresh model run.
- Reset failure: stop the live shot. Do not describe a new run as verified.
- Capture permission missing: save screenshots and the slide PDF, and say the video file was not produced.
"""


def shots() -> dict:
    return {
        "01-setup.png": "Reviewed Orbit task on the new-investigation screen",
        "02-workspace.png": f"Live run {LIVE_RUN} with the 6-step witness",
        "03-witness.png": "Same run, evidence selected",
        "04-stage-result.png": f"Express regression {EXPRESS_RUN} failed cart check",
        "output": f"{RELEASE_ID}-demo-1920x1080.mp4",
    }


def description(live: dict) -> str:
    summary = (
        "Ghost Users runs a browser task locally, keeps the witnessed clicks, and replays them from a fresh start. "
        "The answer is the best verified workflow under the declared budget, not a success screen."
    )
    body = f"""{summary}

Ghost Users is a self-hosted investigation tool. A developer sets the page, the goal, the allowed actions, and the budget. A local Chromium session performs the clicks. An OpenRouter model may choose only from the controls the page is already showing. The product then resets the controlled Orbit Supply shop and replays that exact sequence. The checkout goal reads the shop's authoritative cart. A page that says checkout is ready still fails when the cart is empty.

The technical piece is the split between the witnessed history and the check. The live run {LIVE_RUN} on build orbit-buggy-v1 verified a 6-interaction route and stopped with {live.get("stopReason")}. Its first click was Express Nova Mug. The separate Express regression {EXPRESS_RUN} failed the cart check after one click. The ordinary fixture route {ORDINARY_RUN} passed in five clicks. Those fixture routes are labeled checks. The model was not given them as a script.

Install from source with the pinned requirements file, start Ghost Users on 127.0.0.1:8787 and Orbit Supply on 127.0.0.1:8788. Recorded playback of {LIVE_RUN} needs no API key. There is no public deployment URL in this package.

Measured on this machine: the live run used 6 model requests, 4303 tokens, and reported about $0.0176. The Express check reported no model charge. This is one task, one budget, and one witnessed path. It is not a claim that six interactions is the shortest route, and there is no comparative study.
"""
    return f"## Summary\n\n{summary}\n\n## Description\n\n{body}"


def measured_csv() -> str:
    return """run_id,role,status,stop_reason,interactions,model_requests,total_tokens,spend_usd,browser_actions,resets,elapsed_ms,build
run_c6252c9a4a6e4ba2,live_model,passed,completed_target,6,6,4303,0.017589,14,2,18334,orbit-buggy-v1
run_b1a8b04516204ce7,fixture_ordinary,passed,completed_target,5,0,,unknown,12,2,3189,orbit-buggy-v1
run_f14d218e9d8c4dff,fixture_express,failed,search_envelope_exhausted,1,0,,unknown,4,2,3186,orbit-buggy-v1
run_38c72d89d7c34524,stop,stopped,stopped_by_user,,0,,unknown,,,,
"""


def deck_html(live: dict) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{RELEASE_ID}</title>
<style>
  @page {{ size: 1920px 1080px; margin: 0; }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; background: #0b1020; color: #f4f7fb; font-family: Inter, "Segoe UI", sans-serif; }}
  section {{ width: 1920px; height: 1080px; padding: 96px 120px; page-break-after: always; display: flex; flex-direction: column; justify-content: center; }}
  h1 {{ font-size: 72px; line-height: 1.05; margin: 0 0 28px; max-width: 1500px; }}
  p, li {{ font-size: 36px; line-height: 1.35; color: #d5deec; max-width: 1500px; }}
  .kicker {{ color: #65d9f5; font-size: 28px; letter-spacing: 0.04em; margin-bottom: 24px; }}
  .ok {{ color: #5ee0a0; }}
  .bad {{ color: #ff8a7a; }}
  img {{ width: 720px; border-radius: 12px; border: 1px solid #2b3853; }}
  .row {{ display: flex; gap: 48px; align-items: center; }}
</style>
</head>
<body>
<section>
  <div class="kicker">Ghost Users · {RELEASE_ID}</div>
  <h1>A successful-looking screen is not a verified workflow.</h1>
  <p>Reach checkout with exactly one Nova Mug. Do not place an order. The check reads the cart, not the banner.</p>
</section>
<section>
  <div class="kicker">How a result is established</div>
  <h1>Local browser, witnessed history, fresh replay.</h1>
  <p>The model may only choose a control that is already on the page. The replay starts from a new reset and repeats those exact actions.</p>
</section>
<section>
  <div class="kicker">What this run established</div>
  <div class="row">
    <div>
      <h1>6 verified interactions.</h1>
      <p>Run {LIVE_RUN}. Build orbit-buggy-v1. Stop {live.get("stopReason")}. 6 requests, 4303 tokens, reported $0.0176.</p>
      <p class="bad">Express alone failed the cart check.</p>
      <p>This release does not search for a shorter route.</p>
    </div>
    <img src="../captures/02-workspace.png" alt="Investigation workspace">
  </div>
</section>
<section>
  <div class="kicker">This package</div>
  <h1>Self-hostable R01, with the evidence.</h1>
  <p>Playback of the recorded run needs no API key. Later stages, including a search for a shorter route, are not in this release.</p>
</section>
</body>
</html>
"""


def render_deck(candidate: Path) -> None:
    html = candidate / "presentation" / "editable-local-source" / "deck.html"
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(html.as_uri(), wait_until="load")
        page.pdf(
            path=str(candidate / "presentation" / "slides.pdf"),
            width="1920px",
            height="1080px",
            print_background=True,
            prefer_css_page_size=True,
        )
        for index in range(4):
            page.evaluate(f"document.querySelectorAll('section')[{index}].scrollIntoView()")
            page.screenshot(path=str(candidate / "presentation" / f"slide-0{index + 1}.png"))
        browser.close()


def hash_tree(candidate: Path) -> dict[str, str]:
    hashes = {}
    for path in sorted(candidate.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        if path.is_symlink():
            raise SystemExit(f"symlink not allowed: {path}")
        hashes[str(path.relative_to(candidate))] = sha256_file(path)
    return hashes


def manifest_body(created: str, hashes: dict[str, str]) -> dict:
    return {
        "release_id": RELEASE_ID,
        "stage": STAGE,
        "status": "frozen",
        "source_revision": SOURCE_REVISION,
        "source_tree_hash": SOURCE_REVISION,
        "build_id": "orbit-buggy-v1",
        "created_at": created,
        "timezone": "America/New_York",
        "capabilities": [
            "guided setup",
            "model-chosen browser path",
            "independent replay",
            "fixture regression checks",
            "recorded playback",
        ],
        "limitations": [
            "one witnessed path, not a shorter-route search",
            "Orbit Supply is a controlled demo",
            "planner does not receive screenshots",
            "video not recorded in this package",
        ],
        "requirements": {
            "python": "3.12 tested, 3.11+ required",
            "node": "25 tested for the frontend build",
            "browser": "Chromium via Playwright 1.64.1",
            "platforms_tested": ["macOS arm64"],
        },
        "versions": {"contracts": "v1", "prompts": {"planner": "v1"}, "fixture": "orbit-buggy-v1"},
        "models": [
            {
                "purpose": "browser_plan",
                "requested": "anthropic/claude-sonnet-4.6",
                "observed": "anthropic/claude-sonnet-4.6",
                "settings": {"images": False},
                "verified": True,
            }
        ],
        "checks": [{"name": "see checks.json", "result": "see checks.json", "at": created, "evidence": "checks.json"}],
        "demonstrations": [
            {
                "run_id": LIVE_RUN,
                "build_id": "orbit-buggy-v1",
                "task_version": 1,
                "mode": "genuine_recorded_run",
                "path": f"evidence/playback-data",
            }
        ],
        "presentation": {
            "source_reference": "presentation/source-reference.json",
            "figma_status": "unavailable",
            "pdf": "presentation/slides.pdf",
        },
        "video": {"status": "not_recorded_in_build_package", "recording_prompt": "demo/recording-agent-prompt.md"},
        "artifact_hashes": hashes,
    }


def write_index(manifest_hash: str, created: str, status: str) -> None:
    index = {
        "selected": RELEASE_ID if status == "frozen" else None,
        "releases": [
            {
                "id": "GU-R01-20261107-r1",
                "stage": STAGE,
                "status": "failed",
                "path": None,
                "reason": "Packager scan matched the redaction literal before validation. Not a frozen release.",
            },
            {
                "id": "GU-R01-20261107-r2",
                "stage": STAGE,
                "status": "failed",
                "path": None,
                "reason": "Validation did not finish because the previous server still held port 8787. Not a frozen release.",
            },
            {
                "id": "GU-R01-20261107-r3",
                "stage": STAGE,
                "status": "failed",
                "path": None,
                "reason": "Playback validation returned 404 because the copied database omitted the SQLite WAL. Not a frozen release.",
            },
            {
                "id": RELEASE_ID,
                "stage": STAGE,
                "status": status,
                "path": f"releases/{RELEASE_ID}",
                "manifest_sha256": manifest_hash,
                "source_revision": SOURCE_REVISION,
                "created_at": created,
                "video": "not_recorded_in_build_package",
            },
        ],
    }
    (ROOT / "release-index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


def scan_candidate(candidate: Path) -> None:
    for path in candidate.rglob("*"):
        if path.is_symlink():
            raise SystemExit(f"symlink: {path}")
        if path.name in {".env", ".git"} or path.suffix == ".sqlite3-journal":
            raise SystemExit(f"forbidden file {path}")
        if path.is_file() and path.stat().st_size < 2_000_000 and path.suffix in {".py", ".md", ".json", ".txt", ".html", ".csv"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"sk-or-[A-Za-z0-9]{20,}", text):
                raise SystemExit(f"key-like text in {path}")


def validate(candidate: Path) -> None:
    dest = Path("/tmp/Ghost Users validate") / RELEASE_ID
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(candidate, dest)
    app = dest / "source"
    subprocess.check_call(["uv", "venv", "--python", "3.12", str(app / ".venv")], cwd=app)
    subprocess.check_call(["uv", "pip", "install", "-r", "requirements.txt", "--python", str(app / ".venv" / "bin" / "python")], cwd=app)
    subprocess.check_call([str(app / ".venv" / "bin" / "python"), "-m", "playwright", "install", "chromium"], cwd=app)
    # The development servers must be stopped by the caller before validation binds 8787 and 8788.
    env = os.environ.copy()
    env.pop("OPENROUTER_API_KEY", None)
    env["GHOST_DATA_DIR"] = str(dest / "fresh-data")
    env["GHOST_NO_REEXEC"] = "1"
    start = subprocess.Popen([str(app / ".venv" / "bin" / "python"), "scripts/manage.py", "start"], cwd=app, env=env)
    try:
        wait_health("http://127.0.0.1:8787/api/health")
        wait_health("http://127.0.0.1:8788/health")
        fresh_ok = True
    finally:
        subprocess.call([str(app / ".venv" / "bin" / "python"), "scripts/manage.py", "stop"], cwd=app, env=env)
        start.wait(timeout=45)
    if not fresh_ok:
        raise SystemExit("fresh start failed")
    env["GHOST_DATA_DIR"] = str(dest / "evidence" / "playback-data")
    start = subprocess.Popen([str(app / ".venv" / "bin" / "python"), "scripts/manage.py", "start"], cwd=app, env=env)
    try:
        wait_health("http://127.0.0.1:8787/api/health")
        with urllib.request.urlopen(f"http://127.0.0.1:8787/api/playback/{LIVE_RUN}", timeout=5) as response:
            body = json.loads(response.read().decode())
        if not body.get("readOnly") or body.get("id") != LIVE_RUN:
            raise SystemExit("playback did not return the recorded run")
        if not body["projection"]["bestVerified"] or body["projection"]["bestVerified"]["interactions"] != 6:
            raise SystemExit("playback lost the verified route")
    finally:
        subprocess.call([str(app / ".venv" / "bin" / "python"), "scripts/manage.py", "stop"], cwd=app, env=env)
        start.wait(timeout=45)
    checks_path = candidate / "checks.json"
    items = json.loads(checks_path.read_text(encoding="utf-8"))
    for item in items:
        if item["name"] == "clean-start":
            item["result"] = "passed"
            item["detail"] = f"Relocated copy at {dest} started, served health, and played {LIVE_RUN} without a key."
            item["at"] = now()
    checks_path.write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")
    # The check file changed after the manifest hash. Record the validation result beside the manifest
    # and rebuild the manifest hash so the index matches the finalized checks.
    manifest_path = candidate / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_hashes"] = hash_tree(candidate)
    manifest["status"] = "frozen"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    created = manifest["created_at"]
    write_index(sha256_file(manifest_path), created, "frozen")


def wait_health(url: str) -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.2)
    raise SystemExit(f"not healthy: {url}")


if __name__ == "__main__":
    main()
