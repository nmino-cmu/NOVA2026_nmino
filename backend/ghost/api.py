"""Ghost Users HTTP API. Control requests return before the browser work finishes."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

import httpx
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from playwright.async_api import async_playwright

from ghost import conversation
from ghost.accounting.ledger import Ledger
from ghost.config import Settings
from ghost.engine.adaptive import run_adaptive
from ghost.engine.keyboard import run_keyboard
from ghost.engine.personas import PERSONAS, SHOP_TASK
from ghost.engine.policies import CompatibleChooser, ModelChooser
from ghost.engine.restore import orbit_set_build
from ghost.engine.runner import execute_run
from ghost.engine.verifier import verify_route
from fixtures.orbit.checks import SHORTCUT
from ghost.ids import new_id
from ghost.providers import openrouter as provider
from ghost.providers.compatible import complete as compatible_complete
from ghost.providers.selection import load_selection, save_selection
from ghost.registry import BUDGET_CAPS, EVALUATORS, LIMITS, build_task
from ghost.regressions import POLICIES, Scripted, scripted_for
from ghost.review import brief_markdown, comparability, fingerprint, freshness, recommendation_for
from ghost.store.projections import playback, snapshot
from ghost.store.sqlite import Store

_KEY = re.compile(r"[A-Za-z0-9_\-]{8,80}")
log = logging.getLogger("ghost.api")


def _echo_selected(data_dir: Path) -> bool:
    selected = load_selection(data_dir)
    if not selected:
        return False
    return selected.get("model") == "echo-local" or selected.get("fixture") == "echo-local"


async def _watch_report(app: FastAPI, conv_id: str, run_ids: list[str]) -> None:
    settings: Settings = app.state.settings
    store: Store = app.state.store
    facts: dict = {"personas": []}
    try:
        while True:
            await asyncio.sleep(2)
            try:
                states = [store.get_run(run_id)["status"] for run_id in run_ids]
            except KeyError:
                return
            if any(state in {"queued", "running"} for state in states):
                continue
            break
        current = conversation.load_conversation(settings.data_dir, conv_id)
        if current.get("runIds") != run_ids:
            return

        def mark_writing(record: dict) -> None:
            if record.get("runIds") == run_ids:
                record["reportStatus"] = "writing"

        conversation.mutate_conversation(settings.data_dir, conv_id, mark_writing)
        facts = conversation.dossier(store, run_ids)
        images = conversation.report_images(store, facts)
        completion = await provider.complete_document(
            settings,
            purpose="persona_report",
            system=conversation.REPORT_SYSTEM,
            user=conversation.report_user(facts),
            images=images,
                max_tokens=6000,
            )
        if not completion.ok and images:
            retry = await provider.complete_document(
                settings,
                purpose="persona_report",
                system=conversation.REPORT_SYSTEM,
                user=conversation.report_user(facts),
                max_tokens=6000,
            )
            if retry.ok:
                retry.attempts = completion.attempts + retry.attempts
                completion = retry
            else:
                completion.attempts.extend(retry.attempts)
        if completion.ok and completion.data:
            report = conversation.ground_report(completion.data, facts, screenshot_count=len(images))
            status = "ready"
        else:
            report = conversation.failed_report(facts, completion.error or "model_failed", len(images))
            status = "failed"

        def save_report(record: dict) -> None:
            if record.get("runIds") != run_ids:
                return
            record["report"] = report
            record["reportStatus"] = status
            record["usage"] = (record.get("usage") or []) + completion.attempts

        conversation.mutate_conversation(settings.data_dir, conv_id, save_report)
    except Exception as exc:
        log.exception("report failed for %s", conv_id)
        try:
            error = provider.redact(str(exc))[:300]

            def save_error(record: dict) -> None:
                if record.get("runIds") != run_ids:
                    return
                record["reportStatus"] = "failed"
                record["report"] = conversation.failed_report(facts, error, 0)

            conversation.mutate_conversation(settings.data_dir, conv_id, save_error)
        except Exception:
            log.exception("could not store report failure for %s", conv_id)


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

        selected = load_selection(settings.data_dir)
        versions = dict(run["versions"])
        if run["policyId"] == "ordinary-model-v1" and selected and selected.get("kind") == "compatible":
            versions["model"] = selected["model"]
            versions["provider"] = selected["baseUrl"]
        elif run["policyId"] == "ordinary-model-v1":
            versions["model"] = settings.model
            versions["provider"] = "openrouter"
        store.update_run(run_id, versions=versions)

        def factory(ledger: Ledger):
            if run["policyId"] == "ordinary-model-v1" and selected and selected.get("kind") == "compatible":
                return CompatibleChooser(selected["baseUrl"], store, ledger, run_id, task, model=selected["model"])
            if run["policyId"] == "ordinary-model-v1":
                return ModelChooser(settings, store, ledger, run_id, task)
            if run["policyId"] == "compatible-v1":
                base = os.environ.get("GHOST_COMPATIBLE_BASE", "http://127.0.0.1:8791/v1")
                return CompatibleChooser(base, store, ledger, run_id, task, model=os.environ.get("GHOST_COMPATIBLE_MODEL", "echo-local"))
            return scripted_for(run["policyId"])

        await execute_run(settings, store, app.state.browser, run_id, factory)


def _schedule_report(app: FastAPI, conv_id: str, run_ids: list[str]) -> None:
    if not run_ids:
        return
    jobs = getattr(app.state, "report_jobs", None)
    if not isinstance(jobs, dict):
        jobs = {}
        app.state.report_jobs = jobs
    key = tuple(run_ids)
    if jobs.get(conv_id) == key:
        return
    jobs[conv_id] = key

    async def job() -> None:
        try:
            await _watch_report(app, conv_id, run_ids)
        finally:
            if jobs.get(conv_id) == key:
                jobs.pop(conv_id, None)

    asyncio.create_task(job())


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    store = Store(settings.data_dir)
    store.recover()
    app.state.store = store
    app.state.lease = asyncio.Semaphore(2)
    app.state.report_jobs = {}
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
    if settings.public_demo:
        origins = [item.strip() for item in os.environ.get("GHOST_CORS_ORIGINS", "https://nickmino.com,https://www.nickmino.com").split(",") if item.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        canned = {"/api/fixture-checks", "/api/persona-runs", "/api/keyboard-checks", "/api/comparisons"}

        @app.middleware("http")
        async def _no_canned_demos(request: Request, call_next):
            if request.method == "POST" and request.url.path in canned:
                return JSONResponse({"detail": "Provide a public link to investigate."}, status_code=404)
            return await call_next(request)

    def _public_url(url: str) -> None:
        if not settings.public_demo or not (url or "").strip():
            return
        reason = conversation.public_target_error(url)
        if reason:
            raise HTTPException(400, reason)

    @app.get("/api/health")
    def health():
        module = Path(__file__).resolve()
        return {
            "ok": True,
            "product": "Ghost Users",
            "schema": 1,
            "module": str(module),
            "mtime": module.stat().st_mtime,
            "publicDemo": settings.public_demo,
        }

    @app.get("/api/capabilities")
    def capabilities():
        return {
            "product": "Ghost Users",
            "schema": 1,
            "features": {
                "investigation": True,
                "playback": True,
                "fixtureChecks": not settings.public_demo,
                "adaptive": True,
                "recommendations": True,
                "comparison": not settings.public_demo,
                "provider": True,
                "keyboard": not settings.public_demo,
                "workers": 2,
                "invalidation": True,
            },
            "provider": {"configured": _configured(), "model": settings.model, "verified": False},
            "fixture": None if settings.public_demo else {
                "name": "Orbit Supply",
                "label": "Controlled demo application",
                "url": settings.orbit_origin + "/",
            },
            "limits": {**BUDGET_CAPS, "routeActions": LIMITS["routeActions"]},
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
        _public_url(str(draft.get("url") or ""))
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
        _public_url(str(spec.get("url") or ""))
        return app.state.store.create_task(spec)

    @app.post("/api/runs")
    async def create_run(request: Request, body: dict):
        policy_id = body.get("policyId") or ""
        if policy_id not in POLICIES:
            raise HTTPException(400, "Unknown policy.")
        if settings.public_demo and (
            policy_id.startswith("regression.") or policy_id.startswith("compare.") or policy_id.startswith("keyboard.")
        ):
            raise HTTPException(404, "Provide a public link to investigate.")
        key = body.get("idempotencyKey") or ""
        if not _KEY.fullmatch(key):
            raise HTTPException(400, "idempotencyKey must be 8 to 80 letters, numbers, underscores, or hyphens.")
        try:
            task = app.state.store.get_task(body["taskId"])
        except KeyError:
            raise HTTPException(404, "Task not found.") from None
        if int(body.get("taskVersion") or 0) != task["version"]:
            raise HTTPException(409, "Task version does not match.")
        _public_url(str(task.get("url") or ""))
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
        policy_id = {"ordinary": "regression.ordinary.v1", "shortcut": "regression.shortcut.v1"}.get(kind or "")
        if not policy_id:
            raise HTTPException(400, "kind must be ordinary or shortcut.")
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

    @app.post("/api/persona-runs")
    async def persona_runs(request: Request, body: dict):
        site = body.get("site") or ""
        if site == "shop":
            url, target = settings.orbit_origin + "/shop", "Cart ready"
        elif site == "amazon":
            url, target = "https://www.amazon.com/", "Shopping Cart"
        else:
            raise HTTPException(400, "site must be shop or amazon.")
        labels = {
            "price": "Price shopper",
            "browse": "Browser",
            "search": "Searcher",
            "careful": "Careful shopper",
            "hurried": "Hurried shopper",
        }
        created = []
        for persona, label in labels.items():
            if persona not in PERSONAS:
                continue
            spec = build_task(
                {
                    "mode": "supplied",
                    "url": url,
                    "targetName": target,
                    "restoration": "fresh_context",
                    "objective": f"{label}: notebook, pen, and mug. Search, browse, and drag the price down.",
                    "task": SHOP_TASK,
                    "queries": ["notebook"],
                    "persona": persona,
                },
                orbit_origin=settings.orbit_origin,
                model=settings.model,
            )
            task = app.state.store.create_task(spec)
            run = app.state.store.create_run(
                task_id=task["id"],
                policy_id="ordinary-model-v1",
                idempotency_key=f"persona-{site}-{persona}-{new_id('k').split('_', 1)[1]}",
                discovery=True,
                label=label,
            )
            if run["status"] == "queued":
                asyncio.create_task(_job(request.app, run["id"]))
            created.append({"id": run["id"], "persona": persona, "label": label, "status": run["status"]})
        return {"site": site, "runs": created}

    @app.get("/api/personas")
    def personas():
        return conversation.public_profiles()

    @app.post("/api/conversations")
    async def discuss(body: dict):
        text = str(body.get("text") or "").strip()
        url = str(body.get("url") or "").strip()
        if not text and not url:
            raise HTTPException(400, "Describe what you want investigated.")
        if _echo_selected(settings.data_dir):
            raise HTTPException(409, "The selected provider is the echo fixture. Choose a reasoning model before planning an investigation.")
        conv_id = str(body.get("conversationId") or "")
        if conv_id:
            try:
                conversation.load_conversation(settings.data_dir, conv_id)
            except KeyError:
                raise HTTPException(404, "Conversation not found.") from None
        else:
            created_record = conversation.new_conversation()
            conversation.save_conversation(settings.data_dir, created_record)
            conv_id = created_record["id"]

        def add_user(record: dict) -> None:
            record["messages"].append(conversation.message("user", text or url, "request"))
            if url:
                record["draftUrl"] = url

        conversation.mutate_conversation(settings.data_dir, conv_id, add_user)
        current = conversation.load_conversation(settings.data_dir, conv_id)
        target = url or (current.get("plan") or {}).get("url") or current.get("draftUrl") or ""
        _public_url(target)
        cached = current.get("site") or {}
        if target.startswith(("http://", "https://")) and cached.get("requestedUrl") == target and cached.get("ok"):
            site = cached
        elif target.startswith(("http://", "https://")):
            site = await conversation.inspect_site(app.state.browser, target)
            _public_url(str(site.get("finalUrl") or ""))

            def save_site(record: dict) -> None:
                record["site"] = site

            conversation.mutate_conversation(settings.data_dir, conv_id, save_site)
            current = conversation.load_conversation(settings.data_dir, conv_id)
        else:
            site = cached
        completion = None
        error = None
        try:
            completion = await provider.complete_document(
                settings,
                purpose="investigation_plan",
                system=conversation.PLAN_SYSTEM,
                user=conversation.plan_user(url or target, text, current, site),
                max_tokens=2000,
            )
        except Exception as exc:
            error = provider.redact(str(exc))[:300]

        def apply_plan(record: dict) -> None:
            if completion and completion.ok and completion.data:
                reply, plan = conversation.interpret_plan(
                    completion.data,
                    url=url or (record.get("plan") or {}).get("url") or record.get("draftUrl") or "",
                    user_text=text,
                    prior_user_turns=sum(1 for item in record.get("messages") or [] if item.get("role") == "user"),
                )
                record["messages"].append(conversation.message("assistant", reply, "plan"))
                if plan:
                    conversation.remember_plan(record, plan)
                record["planSource"] = "model"
                record["planModel"] = settings.model
            else:
                reason = error or (completion.error if completion else "model_failed")
                plan = conversation.fallback_plan(url or (record.get("plan") or {}).get("url") or "", text)
                record["messages"].append(
                    conversation.message(
                        "assistant",
                        "The reasoning model did not return a plan. This draft is only what you wrote, plus the built-in personas. Edit it before launch. "
                        + reason,
                        "plan",
                    )
                )
                conversation.remember_plan(record, plan)
                record["planSource"] = "draft"
            if completion:
                record["usage"] = (record.get("usage") or []) + completion.attempts

        conversation.mutate_conversation(settings.data_dir, conv_id, apply_plan)
        return conversation.present(settings.data_dir, app.state.store, conv_id)

    @app.get("/api/conversations/{conv_id}")
    async def get_conversation(request: Request, conv_id: str):
        try:
            record = conversation.load_conversation(settings.data_dir, conv_id)
        except KeyError:
            raise HTTPException(404, "Conversation not found.") from None
        if record.get("runIds") and not record.get("report") and record.get("reportStatus") != "failed":
            _schedule_report(request.app, conv_id, list(record.get("runIds") or []))
        return conversation.present(settings.data_dir, app.state.store, conv_id)

    @app.post("/api/conversations/{conv_id}/plan")
    def save_plan(conv_id: str, body: dict):
        incoming = body.get("plan")
        if not isinstance(incoming, dict):
            raise HTTPException(400, "Send the plan.")
        try:
            conversation.load_conversation(settings.data_dir, conv_id)
        except KeyError:
            raise HTTPException(404, "Conversation not found.") from None
        plan = conversation.normalize_plan(incoming, url=str(incoming.get("url") or ""), user_text=str(incoming.get("task") or ""))
        _public_url(plan["url"])

        def apply(record: dict) -> None:
            conversation.remember_plan(record, plan)
            record["planSource"] = "edited"

        conversation.mutate_conversation(settings.data_dir, conv_id, apply)
        return conversation.present(settings.data_dir, app.state.store, conv_id)

    @app.post("/api/conversations/{conv_id}/launch")
    async def launch_conversation(request: Request, conv_id: str, body: dict):
        if _echo_selected(settings.data_dir):
            raise HTTPException(409, "The selected provider is the echo fixture. Choose a reasoning model before launching personas.")
        incoming = body.get("plan")
        if not isinstance(incoming, dict):
            raise HTTPException(400, "Send the plan to launch.")
        plan = conversation.normalize_plan(incoming, url=str(incoming.get("url") or ""), user_text=str(incoming.get("task") or ""))
        if not plan["url"].startswith(("http://", "https://")):
            raise HTTPException(400, "The plan needs an http or https URL.")
        _public_url(plan["url"])
        if not plan["task"].strip():
            raise HTTPException(400, "The plan needs a task.")
        if not plan["personas"]:
            raise HTTPException(400, "Choose at least one persona.")
        if any(not item["profile"].strip() for item in plan["personas"]):
            raise HTTPException(400, "Each persona needs a profile.")
        try:
            current = conversation.load_conversation(settings.data_dir, conv_id)
        except KeyError:
            raise HTTPException(404, "Conversation not found.") from None
        store: Store = app.state.store
        for run_id in current.get("runIds") or []:
            try:
                status = store.get_run(run_id)["status"]
            except KeyError:
                continue
            if status in {"queued", "running"}:
                raise HTTPException(409, "Personas are still investigating. Stop them before launching again.")
        wave = int(current.get("wave") or 0) + 1
        created = []
        drafts = conversation.drafts_for(plan)
        if not drafts:
            raise HTTPException(400, "The plan has no task to launch.")
        for item in drafts:
            try:
                spec = build_task(item["draft"], orbit_origin=settings.orbit_origin, model=settings.model)
            except (ValueError, TypeError) as exc:
                raise HTTPException(400, str(exc)) from exc
            _public_url(str(spec.get("url") or ""))
            task = store.create_task(spec)
            run = store.create_run(
                task_id=task["id"],
                policy_id="ordinary-model-v1",
                idempotency_key=f"w{wave}{item['personaId']}{new_id('k').split('_', 1)[1]}",
                discovery=True,
                label=item["label"],
            )
            if run["status"] == "queued":
                asyncio.create_task(_job(request.app, run["id"]))
            created.append(run["id"])

        def apply(record: dict) -> None:
            if record.get("runIds"):
                record["previous"] = {
                    "runIds": list(record["runIds"]),
                    "report": record.get("report"),
                    "wave": record.get("wave") or 0,
                }
            record["runIds"] = created
            record["wave"] = wave
            record["report"] = None
            record["reportStatus"] = None
            conversation.remember_plan(record, plan)
            record["messages"].append(
                conversation.message(
                    "assistant",
                    f"Launched {len(created)} investigations. Each one has its own browser. "
                    f"The plan has {len(plan.get('tasks') or [])} task(s). This launch uses the plan as it is now.",
                    "launch",
                )
            )

        conversation.mutate_conversation(settings.data_dir, conv_id, apply)
        _schedule_report(request.app, conv_id, created)
        return conversation.present(settings.data_dir, app.state.store, conv_id)

    @app.post("/api/conversations/{conv_id}/followup")
    async def follow_up(conv_id: str, body: dict):
        text = str(body.get("text") or "").strip()
        if not text:
            raise HTTPException(400, "Ask a question about the recorded investigation.")
        try:
            current = conversation.load_conversation(settings.data_dir, conv_id)
        except KeyError:
            raise HTTPException(404, "Conversation not found.") from None
        if not current.get("runIds") and not current.get("plan"):
            raise HTTPException(400, "Discuss a plan before asking a follow-up.")
        store: Store = app.state.store
        facts = conversation.dossier(store, current.get("runIds") or [])
        previous_ids = (current.get("previous") or {}).get("runIds") or []
        previous = conversation.dossier(store, previous_ids) if previous_ids else None
        completion = None
        error = None
        try:
            completion = await provider.complete_document(
                settings,
                purpose="followup",
                system=conversation.FOLLOWUP_SYSTEM,
                user=conversation.followup_user(text, facts, previous, current.get("report"), current.get("plan")),
                max_tokens=1800,
            )
        except Exception as exc:
            error = provider.redact(str(exc))[:300]

        def apply(record: dict) -> None:
            record["messages"].append(conversation.message("user", text, "followup"))
            if completion and completion.ok:
                reply = conversation.apply_followup(record, completion.data)
            else:
                reason = error or (completion.error if completion else "model_failed")
                reply = "The reasoning model did not answer from the record. " + reason
            record["messages"].append(conversation.message("assistant", reply, "followup"))
            if completion:
                record["usage"] = (record.get("usage") or []) + completion.attempts

        conversation.mutate_conversation(settings.data_dir, conv_id, apply)
        return conversation.present(settings.data_dir, app.state.store, conv_id)

    @app.post("/api/conversations/{conv_id}/findings/{finding_id}")
    def edit_conversation_finding(conv_id: str, finding_id: str, body: dict):
        try:
            conversation.load_conversation(settings.data_dir, conv_id)
        except KeyError:
            raise HTTPException(404, "Conversation not found.") from None
        try:
            conversation.mutate_conversation(
                settings.data_dir,
                conv_id,
                lambda record: conversation.edit_finding(record, finding_id, body),
            )
        except KeyError:
            raise HTTPException(404, "Finding not found.") from None
        return conversation.present(settings.data_dir, app.state.store, conv_id)

    @app.get("/api/conversations/{conv_id}/brief")
    def conversation_brief(conv_id: str):
        try:
            record = conversation.load_conversation(settings.data_dir, conv_id)
        except KeyError:
            raise HTTPException(404, "Conversation not found.") from None
        return PlainTextResponse(conversation.brief_markdown(record), media_type="text/markdown; charset=utf-8")

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

    @app.post("/api/runs/{run_id}/invalidation")
    def invalidate(run_id: str, body: dict):
        build = str(body.get("build") or "")
        if not build:
            raise HTTPException(400, "Name the build that should be current.")
        try:
            app.state.store.get_run(run_id)
        except KeyError:
            raise HTTPException(404, "Run not found.") from None
        marked = []
        stale_ids = set()
        for row in app.state.store.records(run_id, "verification"):
            state = freshness(row.get("buildId"), build)
            row["stale"] = state == "stale"
            app.state.store.replace_record("verification", row["id"], row)
            marked.append({"id": row["id"], "freshness": state})
            if row["stale"]:
                stale_ids.add(row["id"])
        stale_costs = {
            row.get("interactions")
            for row in app.state.store.records(run_id, "verification")
            if row.get("id") in stale_ids and row.get("status") == "passed"
        }
        reconsidered = []
        for decision in app.state.store.records(run_id, "decision"):
            if decision.get("kind") != "bound":
                continue
            linked = decision.get("verificationId")
            tied = linked in stale_ids or (linked is None and decision.get("U") in stale_costs)
            if not tied:
                continue
            reactivation = {
                "id": new_id("dec"),
                "kind": "reactivated",
                "candidateId": decision.get("candidateId"),
                "verificationId": decision.get("verificationId"),
                "reason": "The verified incumbent is no longer current, so this exclusion has to be reconsidered.",
                "action": decision.get("action"),
            }
            app.state.store.apply(
                run_id,
                records=[("decision", reactivation["id"], reactivation)],
                event_type="branch_reactivated",
                entity_id=reactivation["id"],
                summary=f"Reconsidered the exclusion of {decision.get('action') or 'a candidate'}",
            )
            reconsidered.append(reactivation["id"])
        app.state.store.add_event(
            run_id,
            "finding_recorded",
            run_id,
            {"summary": f"Checked {len(marked)} verification(s) against {build}"},
        )
        return {"build": build, "verifications": marked, "reconsidered": reconsidered}

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
        task = app.state.store.get_task(run["taskId"])
        recommendation = recommendation_for(failed[-1], evidence_ids, task)
        recommendation["runId"] = run_id
        recommendation["buildId"] = run.get("buildId")
        app.state.store.apply(run_id, records=[("recommendation", recommendation["id"], recommendation)], event_type="finding_recorded", entity_id=recommendation["id"], summary="Recorded an evidence-linked recommendation")
        return recommendation

    @app.post("/api/recommendations/{recommendation_id}")
    def edit_recommendation(recommendation_id: str, body: dict):
        try:
            row = app.state.store.find("recommendation", recommendation_id)
        except KeyError:
            raise HTTPException(404, "Recommendation not found.") from None
        status = body.get("status") or row.get("status")
        if status not in {"proposed", "edited", "rejected", "accepted"}:
            raise HTTPException(400, "Status must be proposed, edited, rejected, or accepted.")
        if "claim" in body:
            row["claim"] = str(body.get("claim") or "")[:2000]
        if "proposed" in body:
            row["proposed"] = str(body.get("proposed") or "")[:2000]
        if "acceptance" in body:
            row["acceptance"] = [str(item)[:160] for item in body.get("acceptance") or []][:12]
        row["status"] = status
        app.state.store.replace_record("recommendation", recommendation_id, row)
        run_id = row.get("runId")
        if run_id:
            app.state.store.add_event(run_id, "finding_recorded", recommendation_id, {"summary": f"Recommendation {status}"})
        return row

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
        before = body.get("beforeRunId") or ""
        try:
            before_run = app.state.store.get_run(before)
            before_task = app.state.store.get_task(before_run["taskId"])
        except KeyError:
            raise HTTPException(400, "A retest needs the stored before run. Missing or unknown ids are not comparable.") from None
        actions = _stored_actions(app.state.store, before)
        if not actions:
            raise HTTPException(400, "The before run has no stored action sequence. A retest will not invent one.")
        if (before_task.get("reset") or {}).get("id") != "orbit.reset.v1":
            raise HTTPException(400, "orbit-fixed-v1 is the Orbit fixture build. This before run does not use that reset, so it is not comparable.")
        spec = {key: value for key, value in before_task.items() if key != "id"}
        task = app.state.store.create_task(spec)
        run = app.state.store.create_run(
            task_id=task["id"],
            policy_id=before_run.get("policyId") or "retest",
            idempotency_key=body.get("idempotencyKey") or task["id"],
            discovery=False,
            label="Retest of stored actions",
        )
        asyncio.create_task(_retest(app, run["id"], before, actions))
        return {"id": run["id"], "status": "queued", "build": "orbit-fixed-v1"}

    @app.get("/api/provider")
    def provider_selection():
        selected = load_selection(settings.data_dir)
        return selected or {
            "kind": "openrouter",
            "baseUrl": "https://openrouter.ai/api/v1",
            "model": settings.model,
            "label": "OpenRouter",
            "honest": "The server holds the key. This page never receives it.",
        }

    @app.post("/api/provider")
    def provider_save(body: dict):
        try:
            saved = save_selection(settings.data_dir, str(body.get("baseUrl") or ""), str(body.get("model") or ""), str(body.get("kind") or ""))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return saved

    @app.post("/api/comparisons")
    async def compare():
        harbor_origin = os.environ.get("HARBOR_ORIGIN", "http://127.0.0.1:8789")
        store: Store = app.state.store
        orbit_spec = build_task({"mode": "orbit"}, orbit_origin=settings.orbit_origin, model=settings.model)
        orbit_spec["actionPolicy"] = {"id": "compare.checkout.v1", "version": 1}
        orbit_task = store.create_task(orbit_spec)
        orbit_run = store.create_run(
            task_id=orbit_task["id"],
            policy_id="compare.orbit.v1",
            idempotency_key="compare-orbit-" + orbit_task["id"],
            discovery=False,
            label="Orbit comparison",
        )
        harbor_run = None
        harbor_note = "Harbor Goods is not running."
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                health = await client.get(harbor_origin.rstrip("/") + "/health")
            harbor_up = health.status_code == 200
        except Exception:
            harbor_up = False
        if harbor_up:
            harbor_spec = build_task(
                {
                    "mode": "supplied",
                    "url": harbor_origin.rstrip("/") + "/",
                    "targetName": "Checkout ready",
                    "restoration": "fresh_context",
                    "objective": "Reach checkout with exactly one Nova Mug. Do not place an order.",
                    "task": "Starting logged out with an empty cart, reach checkout with exactly one Nova Mug. Do not place an order.",
                    "cartIncludes": ["Nova Mug × 1"],
                    "namespaceHeader": "X-Harbor-Namespace",
                },
                orbit_origin=settings.orbit_origin,
                model=settings.model,
            )
            harbor_spec["actionPolicy"] = {"id": "compare.checkout.v1", "version": 1}
            harbor_task = store.create_task(harbor_spec)
            harbor_run = store.create_run(
                task_id=harbor_task["id"],
                policy_id="compare.harbor.v1",
                idempotency_key="compare-harbor-" + harbor_task["id"],
                discovery=False,
                label="Harbor comparison",
            )
        else:
            harbor_task = None
        async with app.state.lease:
            await execute_run(settings, store, app.state.browser, orbit_run["id"], lambda ledger: Scripted(SHORTCUT))
            if harbor_run is not None:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.post(harbor_origin.rstrip("/") + "/control/reset", json={"namespace": f"ns_{harbor_run['id']}"})
                    await client.post(harbor_origin.rstrip("/") + "/control/reset", json={"namespace": f"ns_{harbor_run['id']}_verify"})
                harbor_actions = [
                    {"kind": "activate", "target": {"role": "link", "name": "Catalog"}},
                    {"kind": "activate", "target": {"role": "link", "name": "Nova Mug"}},
                    {"kind": "activate", "target": {"role": "button", "name": "Add to cart"}},
                    {"kind": "activate", "target": {"role": "link", "name": "Continue to checkout"}},
                ]
                await execute_run(settings, store, app.state.browser, harbor_run["id"], lambda ledger: Scripted(harbor_actions))
        orbit_body = snapshot(store, orbit_run["id"])
        harbor_body = None if harbor_run is None else snapshot(store, harbor_run["id"])
        orbit_best = orbit_body["projection"]["bestVerified"]
        harbor_best = None if harbor_body is None else harbor_body["projection"]["bestVerified"]
        both = orbit_body["status"] == "passed" and harbor_body is not None and harbor_body["status"] == "passed"
        checklist = [
            {"name": "product", "ok": True, "detail": "Both sides ask for one Nova Mug."},
            {"name": "quantity", "ok": True, "detail": "Exactly one."},
            {"name": "account", "ok": True, "detail": "Logged out. No order is placed."},
            {"name": "terminal", "ok": True, "detail": "Checkout ready is the terminal milestone."},
            {"name": "viewport", "ok": True, "detail": "1440×900."},
            {"name": "action policy", "ok": True, "detail": "compare.checkout.v1 on both sides."},
            {"name": "resource caps", "ok": harbor_task is not None and orbit_spec["budget"] == harbor_task["budget"], "detail": "Default route, request, and browser-action caps."},
        ]
        if harbor_body is None:
            harbor_note = "Harbor Goods is not running, so this comparison is unavailable."
        elif not both:
            harbor_note = "One side did not pass its own acceptance check."
        else:
            harbor_note = "Both sides used a fresh namespace, the same caps, and an independent frozen replay."
        return {
            "comparable": both and all(item["ok"] for item in checklist),
            "reason": harbor_note,
            "checks": checklist,
            "orbit": {
                "runId": orbit_run["id"],
                "status": orbit_body["status"],
                "interactions": None if not orbit_best else orbit_best["interactions"],
                "detail": (orbit_body["projection"].get("latestVerification") or {}).get("detail"),
                "build": orbit_body.get("buildId"),
            },
            "harbor": {
                "runId": None if harbor_run is None else harbor_run["id"],
                "status": "unavailable" if harbor_body is None else harbor_body["status"],
                "interactions": None if not harbor_best else harbor_best["interactions"],
                "detail": harbor_note if harbor_body is None else (harbor_body["projection"].get("latestVerification") or {}).get("detail"),
                "build": None if harbor_body is None else harbor_body.get("buildId"),
            },
        }

    @app.post("/api/provider/test")
    async def provider_compatible(body: dict):
        base = (body.get("baseUrl") or "").strip()
        model_name = (body.get("model") or "").strip()
        if not model_name:
            raise HTTPException(400, "Name the model.")
        key = os.environ.get("OPENROUTER_API_KEY", "")
        result = await compatible_complete(base, model_name, key)
        if model_name == "echo-local":
            result["kind"] = "echo-fixture"
            result["label"] = "Deterministic echo fixture"
            result["honest"] = "This fixture picks an id from the candidate list it is shown. It is not a general model."
        return result

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
            records=[("verification", result["id"], {**result, "buildId": run.get("buildId")})],
            event_type="route_verified",
            entity_id=result["id"],
            summary=f"Replay {result['status']}",
            extra={"status": result["status"]},
        )


def _stored_actions(store: Store, run_id: str) -> list[dict]:
    for kind in ("verification", "route"):
        for row in reversed(store.records(run_id, kind)):
            actions = row.get("actions") or []
            if actions:
                return actions
    return []


async def _retest(app: FastAPI, run_id: str, before_run_id: str, actions: list[dict]) -> None:
    settings: Settings = app.state.settings
    store: Store = app.state.store
    async with app.state.lease:
        switched = await orbit_set_build(settings.orbit_origin, settings.control_token, "orbit-fixed-v1")
        if not switched.get("ok"):
            store.finish(run_id, status="error", stopReason="infrastructure_failure", error="Could not select the fixed fixture build.")
            return
        try:
            await execute_run(settings, store, app.state.browser, run_id, lambda ledger: Scripted(actions))
            current = snapshot(store, run_id)
            best = current["projection"]["bestVerified"]
            task = store.get_task(store.get_run(run_id)["taskId"])
            action_hash = "" if not best else best["actionSequenceHash"]
            before_build = None
            before_hash = None
            before_interactions = None
            before_rows = []
            try:
                before_rows = store.records(before_run_id, "verification")
                before_snap = snapshot(store, before_run_id)
                before_build = before_snap.get("buildId")
                prior = next((row for row in reversed(before_rows) if row.get("actionSequenceHash")), None)
                if prior:
                    before_hash = prior["actionSequenceHash"]
                    before_interactions = prior.get("interactions")
            except KeyError:
                before_rows = []
            if not before_hash or not action_hash:
                relation = "not_comparable"
            else:
                relation = comparability(
                    before_build or "",
                    current.get("buildId") or "",
                    fingerprint(task, before_hash),
                    fingerprint(task, action_hash),
                )
            if relation == "comparable_build_change":
                for row in before_rows:
                    row["stale"] = True
                    store.replace_record("verification", row["id"], row)
            record = {
                "id": run_id,
                "beforeRunId": before_run_id,
                "afterRunId": run_id,
                "beforeBuild": before_build,
                "afterBuild": current.get("buildId"),
                "fingerprint": fingerprint(task, action_hash),
                "status": current["status"],
                "interactions": None if not best else best["interactions"],
                "beforeInteractions": before_interactions,
                "comparable": relation == "comparable_build_change",
                "relation": relation,
            }
            store.apply(run_id, records=[("retest", run_id, record)], event_type="finding_recorded", entity_id=run_id, summary="Recorded the retest of the stored actions")
        finally:
            await orbit_set_build(settings.orbit_origin, settings.control_token, "orbit-buggy-v1")


app = create_app()
