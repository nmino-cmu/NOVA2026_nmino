"""Ghost Users HTTP API. Control requests return before the browser work finishes."""

from __future__ import annotations

import asyncio
import json
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from playwright.async_api import async_playwright

from ghost.accounting.ledger import Ledger
from ghost.config import Settings
from ghost.engine.adaptive import run_adaptive
from ghost.engine.compare import harbor_checkout
from ghost.engine.keyboard import run_keyboard
from ghost.engine.policies import ModelChooser
from ghost.engine.restore import orbit_set_build
from ghost.engine.runner import execute_run
from ghost.engine.verifier import verify_route
from fixtures.orbit.checks import EXPRESS
from ghost.providers import openrouter as provider
from ghost.providers.compatible import complete as compatible_complete
from ghost.registry import EVALUATORS, build_task
from ghost.regressions import POLICIES, Scripted, scripted_for
from ghost.review import brief_markdown, fingerprint, recommendation_for
from ghost.store.projections import playback, snapshot
from ghost.store.sqlite import Store

_KEY = re.compile(r"[A-Za-z0-9_\-]{8,80}")


def _configured() -> bool:
    try:
        import openrouter

        openrouter.load_dotenv()
        return len(openrouter.api_key()) >= 20
    except Exception:
        return False


def _summary(body: dict) -> dict:
    best = body["projection"]["bestVerified"]
    return {
        "id": body["id"],
        "status": body["status"],
        "stopReason": body["stopReason"],
        "label": body["label"],
        "discovery": body["discovery"],
        "policyId": body["policyId"],
        "buildId": body["buildId"],
        "createdAt": body.get("createdAt"),
        "task": body["task"]["task"],
        "bestInteractions": None if not best else best["interactions"],
        "verification": None if not best else best["status"],
    }


async def _job(app: FastAPI, run_id: str) -> None:
    settings: Settings = app.state.settings
    store: Store = app.state.store
    async with app.state.lease:
        run = store.get_run(run_id)
        if run["status"] not in {"queued", "running"}:
            return
        task = store.get_task(run["taskId"])

        if run["policyId"] == "adaptive-v1":
            await run_adaptive(settings, store, app.state.browser, run_id)
            return
        if run["policyId"] == "keyboard.confirm.v1":
            await run_keyboard(settings, store, app.state.browser, run_id)
            return

        def factory(ledger: Ledger):
            if run["policyId"] == "ordinary-model-v1":
                return ModelChooser(settings, store, ledger, run_id, task)
            return scripted_for(run["policyId"])

        await execute_run(settings, store, app.state.browser, run_id, factory)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    store = Store(settings.data_dir)
    store.recover()
    app.state.store = store
    app.state.lease = asyncio.Semaphore(2)
    playwright = await async_playwright().start()
    app.state.playwright = playwright
    app.state.browser = await playwright.chromium.launch(headless=True)
    yield
    await app.state.browser.close()
    await playwright.stop()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(lifespan=lifespan, title="Ghost Users")
    app.state.settings = settings

    @app.get("/api/health")
    def health():
        return {"ok": True, "product": "Ghost Users", "schema": 1}

    @app.get("/api/capabilities")
    def capabilities():
        return {
            "product": "Ghost Users",
            "schema": 1,
            "features": {
                "investigation": True,
                "playback": True,
                "fixtureChecks": True,
                "adaptive": True,
                "recommendations": True,
                "comparison": True,
                "provider": True,
                "keyboard": True,
                "workers": 2,
            },
            "provider": {"configured": _configured(), "model": settings.model, "verified": False},
            "fixture": {
                "name": "Orbit Supply",
                "label": "Controlled demo application",
                "url": settings.orbit_origin + "/",
            },
            "limits": {"wallMs": 180000, "requests": 12, "totalTokens": 60000, "browserActions": 180, "resets": 12, "routeActions": 12},
        }

    @app.get("/api/evaluators")
    def evaluators():
        return {"evaluators": EVALUATORS}

    @app.post("/api/task-drafts")
    def task_draft(body: dict):
        try:
            draft = build_task(body, orbit_origin=settings.orbit_origin, model=settings.model)
        except (ValueError, TypeError) as exc:
            raise HTTPException(400, str(exc)) from exc
        checks = [
            {
                "id": item["id"],
                "name": item.get("label") or item["id"],
                "status": "pending",
                "detail": "",
            }
            for item in draft.get("checks") or []
        ]
        return {**draft, "checks": checks}

    @app.post("/api/tasks")
    def create_task(body: dict):
        try:
            spec = build_task(body, orbit_origin=settings.orbit_origin, model=settings.model)
        except (ValueError, TypeError) as exc:
            raise HTTPException(400, str(exc)) from exc
        return app.state.store.create_task(spec)

    @app.post("/api/runs")
    async def create_run(request: Request, body: dict):
        policy_id = body.get("policyId") or ""
        if policy_id not in POLICIES:
            raise HTTPException(400, "Unknown policy.")
        key = body.get("idempotencyKey") or ""
        if not _KEY.fullmatch(key):
            raise HTTPException(400, "idempotencyKey must be 8 to 80 letters, numbers, underscores, or hyphens.")
        try:
            task = app.state.store.get_task(body["taskId"])
        except KeyError:
            raise HTTPException(404, "Task not found.") from None
        if int(body.get("taskVersion") or 0) != task["version"]:
            raise HTTPException(409, "Task version does not match.")
        label, discovery, _kind = POLICIES[policy_id]
        run = app.state.store.create_run(
            task_id=task["id"],
            policy_id=policy_id,
            idempotency_key=key,
            discovery=discovery,
            label=label,
        )
        if run["status"] == "queued":
            asyncio.create_task(_job(request.app, run["id"]))
        return {"id": run["id"], "status": run["status"]}

    @app.post("/api/fixture-checks")
    async def fixture_checks(request: Request, body: dict):
        kind = body.get("kind")
        policy_id = {"ordinary": "regression.ordinary.v1", "shortcut": "regression.shortcut.v1", "express": "regression.express.v1"}.get(kind or "")
        if not policy_id:
            raise HTTPException(400, "kind must be ordinary, shortcut, or express.")
        key = body.get("idempotencyKey") or ""
        if not _KEY.fullmatch(key):
            raise HTTPException(400, "idempotencyKey must be 8 to 80 letters, numbers, underscores, or hyphens.")
        spec = build_task({"mode": "orbit"}, orbit_origin=settings.orbit_origin, model=settings.model)
        task = app.state.store.create_task(spec)
        label, discovery, _kind = POLICIES[policy_id]
        run = app.state.store.create_run(
            task_id=task["id"],
            policy_id=policy_id,
            idempotency_key=key,
            discovery=discovery,
            label=label,
        )
        if run["status"] == "queued":
            asyncio.create_task(_job(request.app, run["id"]))
        return {"id": run["id"], "status": run["status"], "label": label, "discovery": False}

    @app.get("/api/runs")
    def list_runs():
        store: Store = app.state.store
        return [_summary(snapshot(store, run["id"])) for run in store.list_runs()]

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        try:
            return snapshot(app.state.store, run_id)
        except KeyError:
            raise HTTPException(404, "Run not found.") from None

    @app.get("/api/runs/{run_id}/events")
    async def events(run_id: str, request: Request, after: int = 0, format: str | None = None):
        try:
            app.state.store.get_run(run_id)
        except KeyError:
            raise HTTPException(404, "Run not found.") from None
        header = request.headers.get("last-event-id")
        if header and header.isdigit():
            after = max(after, int(header))
        if format == "json":
            return app.state.store.events_after(run_id, after)

        async def stream():
            cursor = after
            while True:
                batch = app.state.store.events_after(run_id, cursor)
                for event in batch:
                    cursor = event["seq"]
                    yield f"id: {cursor}\ndata: {json.dumps(event)}\n\n"
                current = app.state.store.get_run(run_id)
                if current["status"] not in {"queued", "running"} and cursor >= current["throughSeq"]:
                    break
                await asyncio.sleep(0.4)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post("/api/runs/{run_id}/stop")
    def stop(run_id: str):
        try:
            app.state.store.get_run(run_id)
        except KeyError:
            raise HTTPException(404, "Run not found.") from None
        app.state.store.request_stop(run_id)
        return {"id": run_id, "stopRequested": True}

    @app.get("/api/evidence/{evidence_id}")
    def evidence(evidence_id: str):
        try:
            path, media = app.state.store.evidence_file(evidence_id)
        except KeyError:
            raise HTTPException(404, "Evidence not found.") from None
        if not path.is_file():
            raise HTTPException(404, "Evidence file is missing.")
        return FileResponse(path, media_type=media)

    @app.get("/api/routes/{route_id}")
    def get_route(route_id: str):
        try:
            return app.state.store.find("route", route_id)
        except KeyError:
            raise HTTPException(404, "Route not found.") from None

    @app.get("/api/verifications/{verification_id}")
    def get_verification(verification_id: str):
        try:
            return app.state.store.find("verification", verification_id)
        except KeyError:
            raise HTTPException(404, "Verification not found.") from None

    @app.post("/api/routes/{route_id}/verify")
    async def rerun(request: Request, route_id: str):
        try:
            route = app.state.store.find("route", route_id)
        except KeyError:
            raise HTTPException(404, "Route not found.") from None
        asyncio.create_task(_rerun(request.app, route))
        return {"routeId": route_id, "status": "queued"}

    @app.get("/api/playback/{run_id}")
    def get_playback(run_id: str):
        try:
            return playback(app.state.store, run_id)
        except KeyError:
            raise HTTPException(404, "Run not found.") from None

    @app.post("/api/providers/test")
    async def provider_test():
        if not _configured():
            raise HTTPException(400, "OpenRouter is not configured.")
        result = await provider.complete_json(
            settings,
            purpose="task_draft",
            system="Return JSON only. Do not write code.",
            user='{"word":"ok"} is the required shape. Reply with that object.',
            required=["word"],
            schema_name="probe",
        )
        observed = next((item.get("modelObserved") for item in result.attempts if item.get("modelObserved")), None)
        return {"ok": result.ok, "modelObserved": observed, "error": None if result.ok else "The provider test did not return valid data."}

    @app.post("/api/recommendations")
    def recommend(body: dict):
        run_id = body.get("runId") or ""
        try:
            run = app.state.store.get_run(run_id)
        except KeyError:
            raise HTTPException(404, "Run not found.") from None
        failed = [item for item in app.state.store.records(run_id, "verification") if item.get("status") == "failed"]
        if not failed:
            raise HTTPException(400, "A recommendation needs a failed verification.")
        evidence_ids = [item["id"] for item in app.state.store.evidence_list(run_id)]
        recommendation = recommendation_for(failed[-1], evidence_ids)
        recommendation["runId"] = run_id
        recommendation["buildId"] = run.get("buildId")
        app.state.store.apply(run_id, records=[("recommendation", recommendation["id"], recommendation)], event_type="finding_recorded", entity_id=recommendation["id"], summary="Recorded an evidence-linked recommendation")
        return recommendation

    @app.post("/api/briefs")
    def export_brief(body: dict):
        run_id = body.get("runId") or ""
        recommendation_id = body.get("recommendationId") or ""
        try:
            recommendation = app.state.store.find("recommendation", recommendation_id)
        except KeyError:
            raise HTTPException(404, "Recommendation not found.") from None
        if recommendation.get("runId") != run_id:
            raise HTTPException(400, "That recommendation is not part of this run.")
        markdown = brief_markdown(recommendation, recommendation.get("buildId") or "unknown")
        saved = app.state.store.save_evidence(run_id, "brief", markdown.encode(), "text/markdown", "Implementation brief")
        return {"evidenceId": saved["id"], "markdown": markdown}

    @app.post("/api/retests")
    async def retest(body: dict):
        if body.get("build") != "orbit-fixed-v1":
            raise HTTPException(400, "Name the changed build. This retest only accepts orbit-fixed-v1.")
        task = app.state.store.create_task(build_task({"mode": "orbit"}, orbit_origin=settings.orbit_origin, model=settings.model))
        run = app.state.store.create_run(task_id=task["id"], policy_id="regression.express.v1", idempotency_key=body.get("idempotencyKey") or task["id"], discovery=False, label="Express retest")
        before = body.get("beforeRunId")
        asyncio.create_task(_retest(app, run["id"], before))
        return {"id": run["id"], "status": "queued", "build": "orbit-fixed-v1"}

    @app.post("/api/comparisons")
    async def compare():
        harbor = os.environ.get("HARBOR_ORIGIN", "http://127.0.0.1:8789")
        result = await harbor_checkout(app.state.browser, harbor)
        return {
            "harbor": result,
            "orbitShortcutInteractions": 3,
            "comparable": result.get("status") == "passed",
            "reason": "Both tasks start logged out and ask for checkout with one Nova Mug. The routes are measured separately." if result.get("status") == "passed" else result.get("detail"),
        }

    @app.post("/api/provider/test")
    async def provider_compatible(body: dict):
        base = (body.get("baseUrl") or "").strip()
        model_name = (body.get("model") or "echo-local").strip()
        key = os.environ.get("OPENROUTER_API_KEY", "")
        return await compatible_complete(base, model_name, key)

    @app.get("/demo/keyboard")
    def keyboard_page():
        from fastapi.responses import HTMLResponse

        from ghost.engine.keyboard import PAGE

        return HTMLResponse(PAGE)

    @app.post("/api/keyboard-checks")
    def keyboard_check(body: dict):
        task = app.state.store.create_task(
            build_task(
                {"mode": "supplied", "url": "http://127.0.0.1:8787/demo/keyboard", "targetName": "Desk confirmed", "restoration": "fresh_context", "objective": "Confirm the desk with the keyboard."},
                orbit_origin=settings.orbit_origin,
                model=settings.model,
            )
        )
        run = app.state.store.create_run(task_id=task["id"], policy_id="keyboard.confirm.v1", idempotency_key=body.get("idempotencyKey") or task["id"], discovery=False, label="Keyboard check")
        asyncio.create_task(_job(app, run["id"]))
        return {"id": run["id"], "status": run["status"]}

    dist = settings.repo_root / "frontend" / "dist"
    index = dist / "index.html"
    if index.is_file():
        from fastapi.staticfiles import StaticFiles
        from starlette.exceptions import HTTPException as StarletteHTTPException

        class _Spa(StaticFiles):
            async def get_response(self, path: str, scope):
                try:
                    return await super().get_response(path, scope)
                except StarletteHTTPException as exc:
                    if exc.status_code == 404 and "." not in Path(path).name:
                        return await super().get_response("index.html", scope)
                    raise

        app.mount("/", _Spa(directory=dist, html=True), name="ui")
    else:
        @app.get("/")
        def root():
            return {"product": "Ghost Users", "ui": "http://127.0.0.1:5173"}

    return app


async def _rerun(app: FastAPI, route: dict) -> None:
    settings: Settings = app.state.settings
    store: Store = app.state.store
    async with app.state.lease:
        run = store.get_run(route["runId"])
        task = store.get_task(run["taskId"])
        current = snapshot(store, run["id"])
        ledger = Ledger.from_task(task)
        ledger.used_browser = current["usage"]["browserActions"]
        ledger.used_resets = current["usage"]["resets"]
        if not ledger.can_verify(len(route.get("actions") or [])):
            return
        result = await verify_route(
            settings=settings,
            store=store,
            browser=app.state.browser,
            run_id=run["id"],
            task=task,
            actions=route["actions"],
            ledger=ledger,
            baseline_orders=0,
            expected_build=run.get("buildId"),
            prefix_ids=route.get("prefixIds") or [],
            route_id=route["id"],
        )
        store.apply(
            run["id"],
            records=[("verification", result["id"], result)],
            event_type="route_verified",
            entity_id=result["id"],
            summary=f"Replay {result['status']}",
            extra={"status": result["status"]},
        )


async def _retest(app: FastAPI, run_id: str, before_run_id: str | None) -> None:
    settings: Settings = app.state.settings
    store: Store = app.state.store
    async with app.state.lease:
        switched = await orbit_set_build(settings.orbit_origin, settings.control_token, "orbit-fixed-v1")
        if not switched.get("ok"):
            store.finish(run_id, status="error", stopReason="infrastructure_failure", error="Could not select the fixed fixture build.")
            return
        try:
            await execute_run(settings, store, app.state.browser, run_id, lambda ledger: Scripted(EXPRESS))
            current = snapshot(store, run_id)
            best = current["projection"]["bestVerified"]
            task = store.get_task(store.get_run(run_id)["taskId"])
            action_hash = "" if not best else best["actionSequenceHash"]
            record = {
                "id": run_id,
                "beforeRunId": before_run_id,
                "afterRunId": run_id,
                "beforeBuild": "orbit-buggy-v1",
                "afterBuild": current.get("buildId"),
                "fingerprint": fingerprint(task, action_hash),
                "status": current["status"],
                "interactions": None if not best else best["interactions"],
                "comparable": True,
            }
            store.apply(run_id, records=[("retest", run_id, record)], event_type="finding_recorded", entity_id=run_id, summary="Recorded the Express retest")
        finally:
            await orbit_set_build(settings.orbit_origin, settings.control_token, "orbit-buggy-v1")


app = create_app()
