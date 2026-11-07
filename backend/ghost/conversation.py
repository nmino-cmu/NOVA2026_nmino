"""Investigation conversations. Plans, persona runs, and reports persist as JSON."""

from __future__ import annotations

import ipaddress
import json
import re
import socket
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from ghost.engine.personas import PROFILES, REVIEW_PROFILES
from ghost.ids import new_id
from ghost.store.projections import snapshot

def local_fixture_shop(url: str) -> bool:
    parts = urlsplit(url or "")
    return parts.path.rstrip("/") == "/shop" and (parts.hostname or "").lower() in {"127.0.0.1", "localhost"}


def _blocked_ip(addr: ipaddress._BaseAddress) -> bool:
    return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast or addr.is_unspecified


def public_target_error(url: str) -> str | None:
    """Reject links a public demo must not open. None means the link is a public http(s) URL."""
    parts = urlsplit((url or "").strip())
    host = (parts.hostname or "").lower().rstrip(".")
    if parts.scheme not in {"http", "https"} or not host:
        return "Use an http or https link."
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".localhost", ".internal")):
        return "Use a public website link."
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            return "That link did not resolve."
        addresses = []
        for info in infos:
            try:
                addresses.append(ipaddress.ip_address(info[4][0]))
            except ValueError:
                continue
    if not addresses or any(_blocked_ip(addr) for addr in addresses):
        return "Use a public website link."
    return None


_ID = re.compile(r"conv_[a-f0-9]{16}")
_SLUG = re.compile(r"[^a-z0-9_-]")
_LOCK = threading.Lock()
_BUDGET_CAPS = {"requests": 20, "browserActions": 180, "wallMs": 360_000}
_BUDGET_DEFAULTS = {"requests": 8, "browserActions": 16, "wallMs": 180_000}
_KINDS = {"fact", "inference", "recommendation"}
_FINDING_STATUSES = {"proposed", "edited", "rejected", "accepted"}
_KINDS_PLAN = {"review", "workflow", "focused"}
_CHECKS = {"shop", "heading", "explore"}
WIDGETS = (
    "journey",
    "roster",
    "screenshots",
    "milestones",
    "coverage",
    "search",
    "funnel",
    "personas",
    "recommendations",
    "evidence",
)
_WIDGET_DEFAULTS = {
    "review": ["journey", "roster", "screenshots", "coverage", "recommendations", "evidence"],
    "workflow": ["journey", "roster", "screenshots", "milestones", "funnel", "personas", "recommendations", "evidence"],
    "focused": ["journey", "roster", "screenshots", "search", "recommendations", "evidence"],
}
_STOPWORDS = {
    "this", "that", "with", "from", "have", "been", "when", "they", "their", "after", "before",
    "page", "check", "goal", "both", "into", "only", "than", "then", "also", "does", "were",
    "what", "which", "would", "could", "should", "about", "there", "where", "while",
}

TESTABLE = [
    "Which controls each persona chooses from the controls actually on the page.",
    "Whether the shared acceptance check passes, and which actions and screenshots led there.",
    "Retries after a control is missing, blocked, or outside the viewport.",
    "Differences in action count, blocked attempts, repeated pages, and wall-clock time.",
]
UNCERTAIN = [
    "How a real person would feel, or how many people would abandon the task. One run is not a population.",
    "Whether a missing control is a product defect, a popup, a changed page, or a target the browser could not resolve.",
    "Behavior the page never offered a control for.",
    "Conversion, revenue, or time spent by a person. The elapsed time includes model and orchestration latency.",
]
FACTS_NOTE = (
    "elapsedMs is wall time for the whole investigation, including model calls and orchestration. "
    "browserActions counts page actions only. requests counts model calls. "
    "Do not treat elapsedMs as time a person spent on the page. "
    "backtracks counts a return to an earlier URL and does not explain why. "
    "One run is not a population. A missing or blocked control is a limit of this attempt, not by itself a usability defect."
)

PLAN_SYSTEM = (
    "You plan a browser investigation. You do not write application code or widget components. "
    "The user describes a website and what they want to understand. "
    "For a broad request, ask at most three concise questions about the audience, the site's purpose, the outcome they care about, or the budget. "
    "Set needsClarification true while those answers are missing. You may include a partial plan and label its open points as assumptions. "
    "Use the supplied site inspection. Propose tasks from pages and links it actually lists. Do not invent a purchase flow, a search box, or a control the inspection did not show. "
    "Do not treat every website as a shop. The supplied profiles price, browse, search, careful, and hurried are shoppers. Use them only when the user is asking about shopping or the inspected site is a shop. "
    "For a general review, UI feedback, scan, onboarding, landing page, or navigation question, define three or four distinct personas. "
    "Each profile must be at least two sentences: who they are, how they browse, and what they notice. "
    "Prefer review personas (executive skimmer, accessibility-focused, mobile-first, skeptical evaluator) over shopper profiles unless the user asked about shopping. "
    "Return one JSON object with keys reply, needsClarification, questions, and plan. "
    "plan keys: url, kind, task, objective, assumptions, audience, purpose, tasks, personas, startingConditions, constraints, successCriteria, scope, visibleOutcome, queries, budget, dashboard, outputs. "
    "kind is review, workflow, or focused. "
    "tasks is a list of at most three objects with name, url, intent, check, heading, queries, and paths. "
    "check is shop, heading, or explore. "
    "Use shop only for a cart task whose url path is /shop. A request to add items or meet a price ceiling on /shop is one shop task, not several explore tasks. "
    "Use heading only for a success heading that is absent on the starting page. "
    "Use explore for a review. paths lists paths from the inspection. Coverage is counted from visited URLs. Do not look for a heading named Done. "
    "personas is a list of objects with id, name, profile, and priorities. "
    "dashboard.widgets is a list drawn only from: journey, roster, screenshots, milestones, coverage, search, funnel, personas, recommendations, evidence. "
    "A review includes coverage. A comparison of shoppers includes personas and funnel. A search or navigation request includes search. "
    "outputs lists, in plain language, what the user will receive. "
    "budget has requests, browserActions, and wallMs. Keep requests at or below 8 and browserActions at or below 16 unless the user asked for a longer look. "
    "Do not invent a different route for each persona. A profile is a preference among visible controls. Shared constraints win. "
    "Return only the JSON object, with no markdown fence."
)
REPORT_SYSTEM = (
    "You analyze recorded browser investigations. You do not write code. "
    "Use only the JSON dossier and the attached screenshots. The attached screenshots are samples from the run, not only the final page. A step visible list is the controls after that action, and alerts is error or status text. If visible shows a new control, describe it. Do not say the page was unchanged. Quote alerts. A repeated URL does not mean the content stayed the same. "
    "Return one JSON object with keys summary, personas, findings, and comparison. "
    "summary is a short overview. findings carry the detail. "
    "personas is a list of objects with name, completed, conditions, difficulties, and findings. "
    "Set completed true only when that persona's recorded status is passed. "
    "Write one finding for each supported issue. Do not stop at a fixed count, and do not squeeze a finding into one sentence. "
    "Omit an issue you cannot support from the dossier. "
    "A finding has title, where, observed, personas, goal, impact, change, why, tradeoff, acceptance, retest, severity, confidence, priority, kind, and evidenceIds. "
    "kind is fact, inference, or recommendation. "
    "where names the page and the element or step. observed quotes an action, a goalAttempts detail, or a screenshot label from the dossier. "
    "evidenceIds may cite screenshots whose labels match that observation. An id whose label is unrelated does not support the claim. "
    "The goal check runs before the budget stop. If goalAttempts or the goal check detail exists, the check ran. "
    "Do not say the budget prevented evaluation when a failed detail is recorded. "
    "If checkAlignment is present, explain that unmet requirement before suggesting a larger budget. A larger budget does not change a price ceiling the check already measured. "
    "Separate a product problem from a budget limit, an automation failure, and an uncertain interpretation. "
    "A missing heading or a failed locator is not, by itself, a usability defect. "
    "Do not invent measurements, quotes, conversion gains, or psychological claims. "
    "comparison has completed, pathDifferences, commonFriction, personaSpecific, counts, evidence, priorities, tradeoffs, and gaps. "
    "If the action lists match, say so. Do not invent a difference between personas. "
    "counts must use the recorded action, blocked, backtrack, request, and elapsed figures. elapsedMs includes model time. "
    "One run is not a population. State what was not visited. "
    "Return only the JSON object, with no markdown fence."
)
FOLLOWUP_SYSTEM = (
    "You answer from a recorded investigation and its plan. You do not write application code. "
    "Decide what the user is asking. Return one JSON object with keys reply, action, dashboard, and plan. "
    "action is answer, present, revise, or investigate. "
    "answer: the dossier already contains the answer. dashboard and plan are null. "
    "present: only the dashboard widgets should change. dashboard is an object with widgets drawn only from "
    "journey, roster, screenshots, milestones, coverage, search, funnel, personas, recommendations, evidence. plan is null. "
    "revise: pending work should change, and no new run is required yet. plan is a full replacement plan. "
    "investigate: recorded evidence is not enough, or the user asked to test a change. plan is a concrete revised plan. "
    "Do not tell the user to rerun the unchanged plan. If new work is needed, put the changed tasks, checks, and budget in plan. "
    "Keep checks comparable when the user asks for a retest, and say which task or budget changed. "
    "Reply in plain text. Separate observed facts from inferences. Say when the record is insufficient. "
    "Do not invent measurements, quotes, conversion gains, or psychological explanations. "
    "Do not claim the product changed unless the dossier says so. "
    "Return only the JSON object, with no markdown fence."
)


def stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def public_profiles() -> list[dict]:
    keys = ("id", "name", "profile", "priorities", "canTest", "uncertain")
    seen = set()
    out = []
    for item in REVIEW_PROFILES + PROFILES:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        out.append({key: item[key] for key in keys})
    return out


def new_conversation() -> dict:
    return {
        "id": new_id("conv"),
        "messages": [],
        "plan": None,
        "planRevisions": [],
        "planSource": None,
        "planModel": None,
        "runIds": [],
        "previous": None,
        "report": None,
        "reportStatus": None,
        "wave": 0,
        "createdAt": stamp(),
    }


def message(role: str, text: str, kind: str = "") -> dict:
    return {"id": new_id("msg"), "role": role, "text": text[:8000], "at": stamp(), "kind": kind}


def _path(data_dir: Path, conv_id: str) -> Path:
    if not _ID.fullmatch(conv_id):
        raise KeyError(conv_id)
    return Path(data_dir) / "conversations" / f"{conv_id}.json"


def _write(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record), encoding="utf-8")
    temporary.replace(path)


def save_conversation(data_dir: Path, record: dict) -> None:
    path = _path(data_dir, record["id"])
    with _LOCK:
        _write(path, record)


def load_conversation(data_dir: Path, conv_id: str) -> dict:
    path = _path(data_dir, conv_id)
    with _LOCK:
        if not path.is_file():
            raise KeyError(conv_id)
        return json.loads(path.read_text(encoding="utf-8"))


def mutate_conversation(data_dir: Path, conv_id: str, change) -> dict:
    path = _path(data_dir, conv_id)
    with _LOCK:
        if not path.is_file():
            raise KeyError(conv_id)
        record = json.loads(path.read_text(encoding="utf-8"))
        change(record)
        _write(path, record)
        return record


def _text(value, width: int) -> str:
    if isinstance(value, list):
        value = ". ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()[:width]


def _lines(value, limit: int, width: int) -> list[str]:
    if isinstance(value, str):
        value = [line.strip(" -\t") for line in value.splitlines()]
    if not isinstance(value, list):
        return []
    lines = []
    for item in value:
        text = str(item).strip()[:width]
        if text:
            lines.append(text)
        if len(lines) >= limit:
            break
    return lines


def _budget(raw) -> dict:
    source = raw if isinstance(raw, dict) else {}
    budget = {}
    for key, default in _BUDGET_DEFAULTS.items():
        try:
            value = int(source.get(key, default))
        except (TypeError, ValueError):
            value = default
        if key == "wallMs":
            value = max(value, 90_000)
        budget[key] = max(1, min(value, _BUDGET_CAPS[key]))
    return budget


def _known(persona_id: str) -> dict | None:
    key = persona_id.strip().lower()
    return next((item for item in REVIEW_PROFILES + PROFILES if item["id"] == key), None)


def _personas(raw) -> list[dict]:
    items = []
    seen = set()
    source = raw if isinstance(raw, list) else []
    for entry in source[:8]:
        if isinstance(entry, str):
            entry = {"id": entry}
        if not isinstance(entry, dict):
            continue
        known = _known(str(entry.get("id") or ""))
        name = str(entry.get("name") or (known["name"] if known else "")).strip()[:80]
        slug = _SLUG.sub("", str(entry.get("id") or name).lower().replace(" ", "-"))[:24]
        if not slug:
            slug = f"custom{len(items) + 1}"
        if slug in seen:
            continue
        profile = _text(entry.get("profile") or (known["profile"] if known else ""), 1200)
        priorities = _text(entry.get("priorities") or (known["priorities"] if known else ""), 800)
        if not name and not profile:
            continue
        seen.add(slug)
        items.append(
            {
                "id": slug,
                "name": name or slug,
                "profile": profile,
                "priorities": priorities,
                "known": bool(known),
                "canTest": known["canTest"] if known else "Which visible controls this profile chooses, and whether the shared acceptance check passes.",
                "uncertain": known["uncertain"] if known else "Whether a real person matching this description would behave the same way.",
            }
        )
    return items


def automated_check(plan: dict) -> str:
    lines = []
    for task in plan.get("tasks") or []:
        check = task.get("check")
        if check == "shop":
            lines.append(
                f"{task.get('name')}: the acceptance check reads the cart text. It passes only when the cheaper notebook, "
                "ballpoint pen, and ceramic mug are present, the expensive alternatives are absent, and the price ceiling "
                "is at most 40. A heading by itself does not pass."
            )
        elif check == "heading":
            lines.append(
                f"{task.get('name')}: the check looks for a heading named {task.get('heading')!r}. "
                "A missing heading is a failed check, not by itself a usability defect."
            )
        else:
            paths = ", ".join(task.get("paths") or []) or "the pages the agent can open"
            lines.append(
                f"{task.get('name')}: explore {paths}. Coverage is the URLs visited. "
                "This review does not pass because one heading is visible."
            )
    if lines:
        return " ".join(lines)
    return "No task check has been declared yet."


def ceiling_note(attempts: list[dict]) -> str:
    required = ("Field notebook $4", "Basic ballpoint pen $2", "Ceramic mug $6")
    for item in attempts:
        text = item.get("cartText") or ""
        if not all(name in text for name in required):
            continue
        try:
            ceiling = float(item.get("priceCeiling"))
        except (TypeError, ValueError):
            continue
        if ceiling > 40:
            return (
                f"The cart text contained the three cheaper items while the price ceiling was {ceiling:g}. "
                "The shop check requires that ceiling to be at most 40, and this attempt already failed for that reason. "
                "A larger investigation budget does not move the ceiling."
            )
    return ""


def _dashboard(raw, kind: str) -> dict:
    source = raw.get("widgets") if isinstance(raw, dict) else raw
    chosen = []
    if isinstance(source, list):
        for item in source:
            name = str(item).strip()
            if name in WIDGETS and name not in chosen:
                chosen.append(name)
    if not chosen:
        chosen = list(_WIDGET_DEFAULTS.get(kind, _WIDGET_DEFAULTS["review"]))
    return {
        "widgets": chosen,
        "unavailable": [
            "Conversion, revenue, and how a person felt are not measured.",
            "Elapsed time includes model and orchestration latency.",
        ],
    }


def _tasks(raw, *, url: str, fallback_queries: list[str]) -> list[dict]:
    tasks = []
    source = raw if isinstance(raw, list) else []
    origin = urlsplit(url)
    allowed = f"{origin.scheme}://{origin.netloc}" if origin.netloc else ""
    for entry in source[:3]:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()[:80]
        if not name:
            continue
        task_url = str(entry.get("url") or url).strip()[:500]
        parts = urlsplit(task_url)
        if allowed and f"{parts.scheme}://{parts.netloc}" != allowed:
            task_url = url
            parts = origin
        check = str(entry.get("check") or "explore").strip()
        if check not in _CHECKS:
            check = "explore"
        if check == "shop" and parts.path.rstrip("/") != "/shop":
            check = "explore"
        heading = str(entry.get("heading") or "").strip()[:80]
        if check == "heading" and not heading:
            check = "explore"
        slug = _SLUG.sub("", name.lower().replace(" ", "-"))[:24] or f"task{len(tasks) + 1}"
        tasks.append(
            {
                "id": slug,
                "name": name,
                "url": task_url or url,
                "intent": str(entry.get("intent") or "").strip()[:400],
                "check": check,
                "heading": heading,
                "queries": _lines(entry.get("queries"), 3, 80) if isinstance(entry.get("queries"), list) else (_lines(entry.get("queries"), 3, 80) or list(fallback_queries)),
                "paths": _lines(entry.get("paths"), 8, 120),
            }
        )
    return tasks


def _kind(source: dict, text: str, shop: bool) -> str:
    named = str(source.get("kind") or "").strip().lower()
    if named in _KINDS_PLAN:
        return named
    blob = text.lower()
    if shop or "shopper" in blob or "checkout" in blob:
        return "workflow"
    if any(word in blob for word in ("search", "navigation", "onboarding", "landing", "clarity")):
        return "focused"
    return "review"


_VISITOR = {
    "id": "visitor",
    "name": "First-time visitor",
    "profile": "Open the site without an account. Read the first screen, then follow the most visible way to understand the product and start the requested task.",
    "priorities": "Prefer the primary heading, navigation, and calls to action that are actually on the page.",
}


def normalize_plan(raw, *, url: str, user_text: str) -> dict:
    source = raw if isinstance(raw, dict) else {}
    chosen = str(source.get("url") or url or "").strip()[:500]
    shop = local_fixture_shop(chosen)
    task = str(source.get("task") or user_text or "").strip()[:2000]
    constraints = _lines(source.get("constraints"), 8, 200)
    if not constraints:
        constraints = (
            ["Do not sign in.", "Do not place an order."]
            if shop
            else [
                "Stay on the same origin unless a visible link clearly belongs to the same product.",
                "Do not submit payments or create accounts unless the task explicitly requires it.",
            ]
        )
    criteria = _lines(source.get("successCriteria"), 6, 300)
    if not criteria:
        criteria = ["The shared task is satisfied in the recorded page."]
    start = _text(source.get("startingConditions"), 500)
    if "browser" not in start.lower():
        isolation = (
            "Each persona starts in a new browser context on this URL. A cart stored in that browser stays separate. "
            "A cart stored only on a shared account may not."
        )
        start = f"{start} {isolation}".strip()
    queries = _lines(source.get("queries"), 3, 80)
    kind = _kind(source, f"{task}\n{user_text}", shop)
    tasks = _tasks(source.get("tasks"), url=chosen, fallback_queries=queries)
    if not tasks and chosen:
        path = urlsplit(chosen).path or "/"
        heading = str(source.get("visibleOutcome") or "").strip()[:80]
        if shop:
            tasks = _tasks(
                [{"name": "Cart", "url": chosen, "intent": task, "check": "shop", "queries": queries or ["notebook"], "paths": ["/shop"]}],
                url=chosen,
                fallback_queries=queries or ["notebook"],
            )
        elif heading and heading.lower() != "done":
            tasks = _tasks(
                [{"name": "Milestone", "url": chosen, "intent": task, "check": "heading", "heading": heading, "paths": [path]}],
                url=chosen,
                fallback_queries=queries,
            )
        else:
            tasks = _tasks(
                [{"name": "Review the starting page", "url": chosen, "intent": task, "check": "explore", "paths": [path]}],
                url=chosen,
                fallback_queries=queries,
            )
    plan = {
        "url": chosen,
        "kind": kind,
        "task": task,
        "objective": str(source.get("objective") or task).strip()[:400],
        "assumptions": _lines(source.get("assumptions"), 6, 240),
        "audience": str(source.get("audience") or "").strip()[:200],
        "purpose": str(source.get("purpose") or "").strip()[:200],
        "scope": str(source.get("scope") or "").strip()[:400],
        "tasks": tasks,
        "personas": _personas(source.get("personas")),
        "startingConditions": start,
        "constraints": constraints,
        "successCriteria": criteria,
        "visibleOutcome": str(source.get("visibleOutcome") or "").strip()[:80],
        "queries": queries,
        "budget": _budget(source.get("budget")),
        "dashboard": _dashboard(source.get("dashboard"), kind),
        "outputs": _lines(source.get("outputs"), 6, 200),
        "testable": list(TESTABLE),
        "uncertain": list(UNCERTAIN),
    }
    if not plan["outputs"]:
        plan["outputs"] = ["A recorded journey, the checks that ran, and recommendations tied to those records."]
    plan["automatedCheck"] = automated_check(plan)
    return plan


def _ui_review_intent(user_text: str) -> bool:
    blob = user_text.lower()
    return any(
        word in blob
        for word in (
            "ui",
            "ux",
            "usability",
            "scan",
            "layout",
            "design",
            "accessibility",
            "a11y",
            "visual",
            "heuristic",
            "first impression",
            "friction",
            "hierarchy",
            "clarity",
            "feedback",
        )
    )


def _broad_opening(user_text: str) -> bool:
    text = user_text.lower()
    if _ui_review_intent(text):
        return False
    if any(word in text for word in ("shopper", "checkout", "search", "onboarding", "navigation", "landing")):
        return False
    return any(
        phrase in text
        for phrase in ("generally", "in general", "general review", "review this website", "review this site", "review the website", "review the site")
    )


def interpret_plan(data: dict, *, url: str, user_text: str, prior_user_turns: int = 2) -> tuple[str, dict | None]:
    reply = str(data.get("reply") or "").strip()[:2000]
    needs = data.get("needsClarification")
    if isinstance(needs, str):
        needs = needs.lower() in {"true", "yes", "1"}
    questions = _lines(data.get("questions"), 4, 300)
    opening = _broad_opening(user_text) and prior_user_turns <= 1
    if opening and not questions:
        questions = [
            "Who is this for, and what should they be able to do?",
            "Which outcome matters: clarity, a completed task, or a comparison?",
            "Which pages or journeys matter, and how long should the look be?",
        ]
    if questions:
        reply = (reply + "\n\n" if reply else "") + "\n".join(f"- {item}" for item in questions)
    if opening:
        return reply or "A few answers will shape the plan.", None
    plan_raw = data.get("plan") if isinstance(data.get("plan"), dict) else None
    if needs and not plan_raw:
        return reply or "I need a little more before I can propose a plan.", None
    plan = normalize_plan(plan_raw or {}, url=url, user_text=user_text)
    if not plan["personas"]:
        shop = local_fixture_shop(plan["url"])
        if shop or plan["kind"] == "workflow":
            plan["personas"] = _personas([item["id"] for item in PROFILES])
            note = "The model did not name personas. These shopper profiles are a starting point you can edit, add to, or remove."
        elif plan["kind"] == "review" or _ui_review_intent(user_text):
            plan["personas"] = _personas([item["id"] for item in REVIEW_PROFILES])
            note = "These four review personas are a starting point. Edit names and profiles before launch."
        else:
            plan["personas"] = _personas([_VISITOR])
            note = "The model did not name a persona. A first-time visitor is a starting point you can edit."
        reply = (reply + "\n\n" if reply else "") + note
    if not plan["url"]:
        return reply or "The plan still needs a URL.", None
    return reply or "Here is a plan you can edit before launch.", plan


def fallback_plan(url: str, user_text: str) -> dict:
    shop = local_fixture_shop(url)
    if shop:
        personas = [item["id"] for item in PROFILES]
        constraints = ["Do not sign in.", "Do not place an order."]
    elif _ui_review_intent(user_text) or _kind({}, user_text, shop) == "review":
        personas = [item["id"] for item in REVIEW_PROFILES]
        constraints = [
            "Stay on the same origin unless a visible link clearly belongs to the same product.",
            "Do not submit payments or create accounts unless the task explicitly requires it.",
        ]
    else:
        personas = [_VISITOR["id"]]
        constraints = [
            "Stay on the same origin unless a visible link clearly belongs to the same product.",
            "Do not submit payments or create accounts unless the task explicitly requires it.",
        ]
    return normalize_plan(
        {
            "url": url,
            "kind": "review" if not shop and (_ui_review_intent(user_text) or _kind({}, user_text, shop) == "review") else None,
            "task": user_text,
            "objective": user_text[:240],
            "personas": personas,
            "constraints": constraints,
            "successCriteria": ["The requested outcome is visible in the recorded page."],
            "queries": ["notebook"] if shop else [],
        },
        url=url,
        user_text=user_text,
    )


def remember_plan(record: dict, plan: dict) -> None:
    record["plan"] = plan
    revisions = list(record.get("planRevisions") or [])
    revisions.append({"at": stamp(), "plan": plan})
    record["planRevisions"] = revisions[-20:]


def plan_user(url: str, text: str, record: dict, site: dict | None = None) -> str:
    history = [{"role": item.get("role"), "text": item.get("text")} for item in (record.get("messages") or [])[-8:]]
    return json.dumps(
        {
            "url": url,
            "message": text,
            "history": history,
            "currentPlan": record.get("plan"),
            "site": site or record.get("site") or {},
            "profiles": [
                {"id": item["id"], "name": item["name"], "profile": item["profile"], "priorities": item["priorities"]}
                for item in REVIEW_PROFILES + PROFILES
            ],
            "widgets": list(WIDGETS),
        }
    )


def drafts_for(plan: dict) -> list[dict]:
    lines = [plan["task"].strip(), "", "Constraints:"]
    lines.extend(f"- {item}" for item in plan["constraints"])
    lines.extend(["", "Success:"])
    lines.extend(f"- {item}" for item in plan["successCriteria"])
    shared = "\n".join(lines)[:1800]
    budget = {
        "requests": plan["budget"]["requests"],
        "browserActions": plan["budget"]["browserActions"],
        "wallMs": plan["budget"]["wallMs"],
        "totalTokens": 60_000,
        "resets": 4,
    }
    tasks = plan.get("tasks") or []
    many = len(tasks) > 1
    drafts = []
    for task in tasks:
        check = task.get("check") or "explore"
        heading = task.get("heading") or ""
        target = "Cart ready" if check == "shop" else (heading or "Review")
        intent = task.get("intent") or plan["task"]
        text = f"{shared}\n\nThis run: {task.get('name')}. {intent}"[:2500]
        for persona in plan["personas"]:
            if len(drafts) >= 4:
                return drafts
            profile = persona["profile"]
            if persona.get("priorities"):
                profile = f"{profile}\nPriorities: {persona['priorities']}"
            drafts.append(
                {
                    "label": f"{persona['name']} · {task['name']}" if many else persona["name"],
                    "personaId": persona["id"],
                    "taskId": task.get("id"),
                    "draft": {
                        "mode": "supplied",
                        "url": task.get("url") or plan["url"],
                        "targetName": target,
                        "heading": heading,
                        "check": check,
                        "paths": task.get("paths") or [],
                        "restoration": "fresh_context",
                        "objective": intent[:240] or plan["objective"],
                        "task": text,
                        "queries": task.get("queries") or plan["queries"],
                        "budget": budget,
                        "persona": persona["id"],
                        "personaProfile": profile[:1200],
                        "personaName": persona["name"],
                        "personaPriorities": persona.get("priorities") or "",
                    },
                }
            )
    return drafts


def count_backtracks(urls: list[str]) -> int:
    """A return to an earlier URL counts as one backtrack.

    ponytail: this does not know why the page was revisited. Upgrade by classifying the action that left and returned.
    """
    seen: list[str] = []
    count = 0
    for url in urls:
        if not url:
            continue
        if url in seen and seen[-1] != url:
            count += 1
        seen.append(url)
    return count


def plain_state(body: dict) -> tuple[str, str]:
    status = body.get("status") or ""
    projection = body.get("projection") or {}
    phase = projection.get("phase") or ""
    reason = body.get("stopReason") or ""
    checks = projection.get("checks") or []
    goal = next((item for item in checks if item.get("id") == "goal"), {})
    detail = goal.get("detail") or body.get("error") or ""
    if status == "queued":
        return "queued", "Waiting for a free browser. Up to two investigations run at once."
    if status == "running" and phase == "verify":
        return "verifying", "Replaying the route from a fresh start to check it."
    if status == "running":
        action = projection.get("currentAction") or {}
        name = action.get("name") or "the next step"
        why = action.get("reason") or "The model is choosing from the controls on the page."
        return "running", f"Working on {name}. {why}"
    if status == "passed":
        return "completed", "The acceptance check passed. The report can still describe extra steps or unclear controls."
    if status == "failed":
        return "failed", detail or "The acceptance check did not pass."
    if status in {"error", "inconclusive"}:
        return "blocked", detail or reason or "The investigation could not establish the conditions it needed."
    if reason == "stopped_by_user":
        return "stopped", "You stopped this persona."
    if reason == "budget_exhausted":
        if "heading named Done" in detail or detail.startswith("Coverage is counted"):
            return "stopped", "The review budget ran out. Coverage is the URLs visited. This check does not pass by finding a heading."
        if goal.get("status") == "failed" and detail:
            return "stopped", f"The budget ran out after the goal check had already failed: {detail}"
        if goal.get("status") == "pending":
            return "stopped", "The budget ran out before a goal result was recorded."
        return "stopped", detail or "The budget ran out."
    if reason == "search_envelope_exhausted":
        return "stopped", detail or "No further visible action was available, and the acceptance check had not passed."
    return "stopped", detail or reason or "The investigation stopped."


def agent_card(body: dict) -> dict:
    projection = body.get("projection") or {}
    state, explanation = plain_state(body)
    activity = [
        item
        for item in projection.get("activity") or []
        if item.get("type") != "usage_updated" and item.get("summary") != "Recorded browser work"
    ]
    images = [item for item in projection.get("evidence") or [] if str(item.get("mediaType") or "").startswith("image")]
    latest = images[-1] if images else None
    current = projection.get("currentAction") or {}
    usage = body.get("usage") or {}
    budget = body.get("budget") or {}
    latest_action = activity[-1] if activity else {}
    return {
        "id": body["id"],
        "label": body.get("label") or "Persona",
        "state": state,
        "explanation": explanation,
        "status": body.get("status"),
        "stopReason": body.get("stopReason"),
        "phase": projection.get("phase"),
        "currentAction": current.get("name") or latest_action.get("summary") or "",
        "reason": current.get("reason") or latest_action.get("reason") or "",
        "elapsedMs": usage.get("elapsedMs") or 0,
        "browserActions": usage.get("browserActions") or 0,
        "browserBudget": budget.get("browserActions"),
        "requests": usage.get("requests") or 0,
        "requestBudget": budget.get("requests"),
        "screenshotId": None if latest is None else latest.get("id"),
        "screenshotLabel": "" if latest is None else latest.get("label") or "",
        "screenshotAt": None if latest is None else latest.get("capturedAt"),
        "actions": activity[-40:],
        "checks": projection.get("checks") or [],
        "goalAttempts": projection.get("goalAttempts") or [],
        "coverage": _coverage(projection),
        "error": body.get("error"),
    }


def _coverage(projection: dict) -> dict:
    visited = []
    for item in projection.get("activity") or []:
        url = item.get("url") or ""
        if not url:
            continue
        path = urlsplit(url).path or "/"
        if path not in visited:
            visited.append(path)
    planned = [str(item) for item in projection.get("coveragePaths") or []]
    seen = {path.rstrip("/") or "/" for path in visited}
    return {
        "planned": planned,
        "visited": visited,
        "unvisited": [item for item in planned if (item.rstrip("/") or "/") not in seen],
    }


def _cards(store, run_ids: list[str]) -> list[dict]:
    cards = []
    for run_id in run_ids:
        try:
            cards.append(agent_card(snapshot(store, run_id)))
        except KeyError:
            cards.append(
                {
                    "id": run_id,
                    "label": run_id,
                    "state": "blocked",
                    "explanation": "This run is no longer in the store.",
                    "actions": [],
                    "checks": [],
                }
            )
    return cards


def present(data_dir: Path, store, conv_id: str) -> dict:
    record = load_conversation(data_dir, conv_id)
    body = dict(record)
    plan = body.get("plan")
    if isinstance(plan, dict) and not (plan.get("dashboard") or {}).get("widgets"):
        kind = str(plan.get("kind") or ("workflow" if "shopper" in (plan.get("task") or "").lower() else "review"))
        plan = {**plan, "kind": kind, "dashboard": _dashboard(plan.get("dashboard"), kind)}
        body["plan"] = plan
    body["agents"] = _cards(store, record.get("runIds") or [])
    previous = record.get("previous") or {}
    body["previousAgents"] = _cards(store, previous.get("runIds") or [])
    body["profiles"] = public_profiles()
    return body


def persona_facts(store, run_id: str) -> dict:
    body = snapshot(store, run_id)
    steps = []
    decisions = []
    urls = []
    blocked = 0
    for event in store.events_after(run_id, 0):
        payload = event.get("payload") or {}
        if event["type"] == "candidate_selected":
            decisions.append({"summary": payload.get("summary") or "", "reason": (payload.get("reason") or "")[:300]})
        elif event["type"] == "transition_observed":
            url = payload.get("url") or ""
            outcome = payload.get("outcome") or ""
            if outcome == "blocked":
                blocked += 1
            if url:
                urls.append(url)
            steps.append(
                {
                    "summary": payload.get("summary") or "",
                    "reason": (payload.get("reason") or "")[:300],
                    "outcome": outcome,
                    "url": url,
                    "screenshotId": payload.get("screenshotId") or "",
                    "visible": [str(name)[:80] for name in (payload.get("visible") or [])][:8],
                    "alerts": [str(item)[:160] for item in (payload.get("alerts") or [])][:3],
                }
            )
    images = [
        item for item in body["projection"].get("evidence") or [] if str(item.get("mediaType") or "").startswith("image")
    ]
    checks = [
        {"name": item.get("name") or item.get("id"), "status": item.get("status"), "detail": item.get("detail") or ""}
        for item in body["projection"].get("checks") or []
    ]
    usage = body.get("usage") or {}
    return {
        "runId": run_id,
        "name": body.get("label") or run_id,
        "status": body.get("status"),
        "stopReason": body.get("stopReason"),
        "error": body.get("error"),
        "checks": checks,
        "actionCount": len(steps),
        "blockedCount": blocked,
        "backtracks": count_backtracks(urls),
        "modelChoices": len(decisions),
        "elapsedMs": usage.get("elapsedMs"),
        "requests": usage.get("requests"),
        "browserActions": usage.get("browserActions"),
        "steps": steps[-30:],
        "decisions": decisions[-24:],
        "goalAttempts": list(body.get("projection", {}).get("goalAttempts") or [])[-16:],
        "evidence": [
            {"id": item["id"], "label": item.get("label") or "", "capturedAt": item.get("capturedAt") or ""}
            for item in _spread(images, 8)
        ],
    }


def _spread(items: list, count: int) -> list:
    if len(items) <= count:
        return list(items)
    if count <= 1:
        return [items[-1]]
    picked = []
    seen = set()
    last = count - 1
    for index in range(count):
        item = items[round(index * (len(items) - 1) / last)]
        marker = id(item)
        if marker in seen:
            continue
        seen.add(marker)
        picked.append(item)
    return picked


def dossier(store, run_ids: list[str]) -> dict:
    people = []
    for run_id in run_ids:
        try:
            people.append(persona_facts(store, run_id))
        except KeyError:
            people.append(
                {
                    "runId": run_id,
                    "name": run_id,
                    "status": "missing",
                    "error": "This run is no longer in the store.",
                    "steps": [],
                    "evidence": [],
                    "checks": [],
                }
            )
    notes = []
    for person in people:
        note = ceiling_note(person.get("goalAttempts") or [])
        if note:
            notes.append(f"{person.get('name')}: {note}")
    return {"personas": people, "note": FACTS_NOTE, "checkAlignment": " ".join(notes)}


def report_images(store, facts: dict) -> list[str]:
    import base64

    images = []
    for person in facts.get("personas") or []:
        evidence = _spread(person.get("evidence") or [], 3)
        for item in evidence:
            try:
                path, media = store.evidence_file(item["id"])
            except KeyError:
                continue
            if not str(media).startswith("image") or not path.is_file():
                continue
            data = path.read_bytes()
            if len(data) > 500_000:
                continue
            images.append(f"data:{media};base64,{base64.standard_b64encode(data).decode('ascii')}")
            if len(images) >= 4:
                return images
    return images


def report_user(facts: dict) -> str:
    return json.dumps(facts)


def _compact(facts: dict) -> list[dict]:
    rows = []
    for person in facts.get("personas") or []:
        goal = next((item.get("detail") for item in person.get("checks") or [] if item.get("name") == "Goal"), "")
        rows.append(
            {
                "name": person.get("name"),
                "runId": person.get("runId"),
                "status": person.get("status"),
                "stopReason": person.get("stopReason"),
                "error": person.get("error"),
                "actionCount": person.get("actionCount"),
                "blockedCount": person.get("blockedCount"),
                "backtracks": person.get("backtracks"),
                "elapsedMs": person.get("elapsedMs"),
                "requests": person.get("requests"),
                "browserActions": person.get("browserActions"),
                "goal": goal,
                "goalStatus": next((item.get("status") for item in person.get("checks") or [] if item.get("name") == "Goal"), ""),
                "evidenceIds": [item.get("id") for item in person.get("evidence") or []],
            }
        )
    return rows


def _match_person(item: dict, people: list[dict]) -> dict | None:
    name = str(item.get("name") or "").lower()
    run_id = str(item.get("runId") or "")
    for person in people:
        if run_id and person.get("runId") == run_id:
            return person
        if name and name == str(person.get("name") or "").lower():
            return person
    if len(people) == 1:
        return people[0]
    return None


def _finding(item: dict, index: int, known_ids: set[str], seen: set[str]) -> dict | None:
    finding_id = re.sub(r"[^A-Za-z0-9_-]", "", str(item.get("id") or ""))[:40] or f"f{index}"
    if finding_id in seen:
        finding_id = f"f{index}"
    seen.add(finding_id)
    finding = {"id": finding_id, "status": "proposed"}
    for key in ("title", "where", "observed", "goal", "impact", "change", "why", "tradeoff", "acceptance", "retest", "severity", "confidence", "priority"):
        finding[key] = str(item.get(key) or "")[:1200]
    personas = item.get("personas")
    if isinstance(personas, list):
        finding["personas"] = ", ".join(str(value) for value in personas)[:200]
    else:
        finding["personas"] = str(personas or "")[:200]
    kind = str(item.get("kind") or "").lower()
    finding["kind"] = kind if kind in _KINDS else "unspecified"
    evidence = item.get("evidenceIds") if isinstance(item.get("evidenceIds"), list) else []
    finding["evidenceIds"] = [str(value)[:40] for value in evidence if str(value) in known_ids][:8]
    if not finding["title"] and not finding["observed"]:
        return None
    return finding


def _missing_labels(observed: str, blob: str) -> list[str]:
    labels = re.findall(r"(?:Add )?[A-Z][a-z]+(?: [a-z]+){0,3} \$\d+", observed)
    labels = [label for label in labels if re.search(r"\b(?:Add|notebook|pen|mug)\b", label, re.I)]
    lowered = blob.lower()
    missing = []
    for label in labels:
        if label.lower() not in lowered and label not in missing:
            missing.append(label)
    return missing


def _claims_unchanged(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in ("no observable", "identical", "did not visibly", "no expanded", "no change", "unchanged", "nothing happened"))


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9$]{4,}", text.lower()) if token not in _STOPWORDS}


def _dossier_text(people: list[dict]) -> str:
    parts = []
    for person in people:
        for step in person.get("steps") or []:
            parts.extend([step.get("summary") or "", step.get("url") or "", step.get("reason") or "", " ".join(step.get("visible") or []), " ".join(step.get("alerts") or [])])
        for check in person.get("checks") or []:
            parts.extend([check.get("detail") or "", check.get("name") or ""])
        for attempt in person.get("goalAttempts") or []:
            parts.extend([attempt.get("detail") or "", attempt.get("cartText") or "", attempt.get("url") or "", str(attempt.get("priceCeiling") or "")])
        for item in person.get("evidence") or []:
            parts.append(item.get("label") or "")
    return " ".join(parts)


def _plain(value) -> str:
    if isinstance(value, list):
        return " ".join(item if isinstance(item, str) else _plain(item) for item in value)
    if isinstance(value, dict):
        return "; ".join(f"{key}: {_plain(item)}" for key, item in value.items())
    if value is None:
        return ""
    return str(value)


def ground_report(data: dict, facts: dict, *, screenshot_count: int) -> dict:
    source = data if isinstance(data, dict) else {}
    recorded_people = list(facts.get("personas") or [])
    people = []
    for item in (source.get("personas") or [])[:8]:
        if not isinstance(item, dict):
            continue
        recorded = _match_person(item, recorded_people)
        completed = bool(recorded) and recorded.get("status") == "passed"
        conditions = str(item.get("conditions") or "")[:600]
        if recorded and not completed and not conditions:
            conditions = f"Recorded status {recorded.get('status')}, stop {recorded.get('stopReason')}."
        people.append(
            {
                "name": str(item.get("name") or (recorded or {}).get("name") or "")[:80],
                "completed": completed,
                "conditions": conditions,
                "difficulties": str(item.get("difficulties") or "")[:800],
                "findings": str(item.get("findings") or "")[:800],
            }
        )
    if not people:
        for recorded in recorded_people:
            people.append(
                {
                    "name": recorded.get("name") or "",
                    "completed": recorded.get("status") == "passed",
                    "conditions": f"Recorded status {recorded.get('status')}.",
                    "difficulties": "",
                    "findings": "",
                }
            )
    labels = {
        item["id"]: item.get("label") or item["id"]
        for person in recorded_people
        for item in person.get("evidence") or []
    }
    known = set(labels)
    blob = _dossier_text(recorded_people)
    seen: set[str] = set()
    findings = []
    # ponytail: eight findings keeps the report inside the model token budget. Raise the cap if reviews routinely need more.
    for index, item in enumerate((source.get("findings") or [])[:8], start=1):
        if not isinstance(item, dict):
            continue
        finding = _finding(item, index, known, seen)
        if not finding:
            continue
        observed_tokens = _tokens(finding["observed"] + " " + finding["title"] + " " + finding["where"])
        finding["supported"] = bool(observed_tokens & _tokens(blob))
        missing = _missing_labels(finding["observed"], blob)
        if finding["supported"] and missing:
            finding["supported"] = False
            finding["observed"] = (
                finding["observed"] + " The record does not list " + ", ".join(missing) + "."
            ).strip()
        if finding["supported"] and _claims_unchanged(finding["observed"]) and not _claims_unchanged(blob):
            finding["supported"] = False
            finding["observed"] = (
                finding["observed"] + " The action executed. The record does not say the page content stayed the same."
            ).strip()
        matched = [
            evidence_id
            for evidence_id in finding["evidenceIds"]
            if _tokens(labels.get(evidence_id, "")) & observed_tokens
        ]
        if not finding["supported"]:
            matched = []
            finding["observed"] = (finding["observed"] + " The recorded dossier does not contain this observation.").strip()
        finding["evidenceIds"] = matched
        finding["evidence"] = [{"id": evidence_id, "label": labels.get(evidence_id) or evidence_id} for evidence_id in matched]
        if finding["supported"] and finding.get("evidenceIds") == [] and item.get("evidenceIds"):
            finding["evidenceNote"] = "No cited screenshot label matches this observation."
        findings.append(finding)
    comparison = source.get("comparison") if isinstance(source.get("comparison"), dict) else {}
    keys = ("completed", "pathDifferences", "commonFriction", "personaSpecific", "counts", "evidence", "priorities", "tradeoffs", "gaps")
    comparison_text = {key: _plain(comparison.get(key))[:800] for key in keys}
    if not comparison_text["completed"]:
        comparison_text["completed"] = "; ".join(
            f"{person.get('name')} recorded status {person.get('status')}" for person in recorded_people
        )
    alignment = str(facts.get("checkAlignment") or "")
    summary = str(source.get("summary") or source.get("reply") or "")[:4000]
    if alignment and alignment not in summary:
        summary = f"{alignment}\n\n{summary}".strip()
    return {
        "ok": True,
        "source": "model",
        "summary": summary,
        "checkAlignment": alignment,
        "personas": people,
        "findings": findings,
        "comparison": comparison_text,
        "recorded": _compact(facts),
        "screenshotCount": screenshot_count,
        "note": FACTS_NOTE,
    }


def failed_report(facts: dict, error: str, screenshot_count: int) -> dict:
    return {
        "ok": False,
        "source": "unavailable",
        "error": (error or "model_failed")[:300],
        "checkAlignment": facts.get("checkAlignment") or "",
        "summary": "The reasoning model did not return an analysis. The recorded section is what the agents did.",
        "personas": [],
        "findings": [],
        "comparison": {},
        "recorded": _compact(facts),
        "screenshotCount": screenshot_count,
        "note": FACTS_NOTE,
    }


def followup_user(question: str, facts: dict, previous: dict | None, report: dict | None, plan: dict | None = None) -> str:
    analysis = {}
    if report:
        analysis = {
            "summary": report.get("summary"),
            "findings": [
                {"id": item.get("id"), "title": item.get("title"), "observed": item.get("observed"), "supported": item.get("supported")}
                for item in (report.get("findings") or [])[:8]
            ],
            "comparison": report.get("comparison"),
            "source": report.get("source"),
        }
    current_plan = plan or {}
    return json.dumps(
        {
            "question": question,
            "current": facts,
            "previous": previous,
            "analysis": analysis,
            "plan": {
                "url": current_plan.get("url"),
                "kind": current_plan.get("kind"),
                "task": current_plan.get("task"),
                "tasks": current_plan.get("tasks"),
                "personas": [
                    {"id": item.get("id"), "name": item.get("name")}
                    for item in (current_plan.get("personas") or [])
                ],
                "dashboard": current_plan.get("dashboard"),
                "budget": current_plan.get("budget"),
            },
            "widgets": list(WIDGETS),
        }
    )


def apply_followup(record: dict, data: dict | None) -> str:
    if not isinstance(data, dict):
        return ""
    action = str(data.get("action") or "answer").lower()
    if action not in {"answer", "present", "revise", "investigate"}:
        action = "answer"
    reply = followup_text(data)
    plan = record.get("plan") or {}
    if action == "present" and isinstance(data.get("dashboard"), dict):
        updated = dict(plan)
        updated["dashboard"] = _dashboard(data["dashboard"], str(updated.get("kind") or "review"))
        remember_plan(record, updated)
        reply = (reply + "\n\n" if reply else "") + "The dashboard widgets were updated. This did not start a new investigation."
    elif action in {"revise", "investigate"} and isinstance(data.get("plan"), dict):
        merged = {**plan, **data["plan"]}
        updated = normalize_plan(
            merged,
            url=str(merged.get("url") or plan.get("url") or ""),
            user_text=str(merged.get("task") or plan.get("task") or ""),
        )
        remember_plan(record, updated)
        record["planSource"] = "model"
        note = (
            "A revised plan is in the editor. Launch it to record the new work on this conversation."
            if action == "investigate"
            else "The pending plan was revised. Launch it when you want that work recorded."
        )
        reply = (reply + "\n\n" if reply else "") + note
    elif action in {"revise", "investigate"}:
        reply = (reply + "\n\n" if reply else "") + "New work was requested, but no revised plan came back. The current plan is unchanged."
    record["lastFollowupAction"] = action
    return reply or "The model returned an empty answer."


async def inspect_site(browser, url: str) -> dict:
    target = (url or "").strip()
    if not target.startswith(("http://", "https://")):
        return {"ok": False, "requestedUrl": target, "detail": "There is no http or https URL to inspect."}
    context = None
    try:
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(target, wait_until="domcontentloaded", timeout=8000)
        data = await page.evaluate(
            """() => {
              const text = (el) => (el.innerText || "").trim().replace(/\\s+/g, " ").slice(0, 80);
              return {
                title: document.title,
                headings: [...document.querySelectorAll("h1, h2")].map(text).filter(Boolean).slice(0, 12),
                links: [...document.querySelectorAll("a")].map((el) => ({name: text(el), href: el.getAttribute("href") || ""})).filter((item) => item.name && item.href && !item.href.startsWith("javascript")).slice(0, 24),
                excerpt: ((document.body && document.body.innerText) || "").replace(/\\s+/g, " ").slice(0, 700)
              };
            }"""
        )
        data["ok"] = True
        data["requestedUrl"] = target
        data["finalUrl"] = page.url
        return data
    except Exception as exc:
        return {"ok": False, "requestedUrl": target, "detail": str(exc)[:200]}
    finally:
        if context is not None:
            await context.close()


def followup_text(data: dict | None) -> str:
    if not isinstance(data, dict):
        return ""
    return str(data.get("reply") or data.get("summary") or "")[:4000]


def edit_finding(record: dict, finding_id: str, body: dict) -> None:
    findings = ((record.get("report") or {}).get("findings")) or []
    for item in findings:
        if item.get("id") != finding_id:
            continue
        status = body.get("status")
        if status in _FINDING_STATUSES:
            item["status"] = status
        changed = False
        for key in ("title", "change", "why", "acceptance"):
            if key in body:
                item[key] = str(body[key])[:800]
                changed = True
        if changed and item.get("status") == "proposed":
            item["status"] = "edited"
        return
    raise KeyError(finding_id)


def brief_markdown(record: dict) -> str:
    plan = record.get("plan") or {}
    report = record.get("report") or {}
    lines = [
        "# Implementation brief",
        "",
        plan.get("task") or "",
        "",
        "This brief is advice from recorded investigations. It does not change the repository.",
        "",
    ]
    findings = [item for item in report.get("findings") or [] if item.get("status") != "rejected"]
    if not findings:
        lines.append("No proposed or accepted findings are stored.")
        return "\n".join(lines)
    for item in findings:
        lines.extend(
            [
                f"## {item.get('title') or 'Finding'}",
                f"Status: {item.get('status')}",
                f"Kind: {item.get('kind')}",
                f"Where: {item.get('where')}",
                f"Observed: {item.get('observed')}",
                f"Personas: {item.get('personas')}",
                f"Goal: {item.get('goal')}",
                f"Impact: {item.get('impact')}",
                f"Change: {item.get('change')}",
                f"Why: {item.get('why')}",
                f"Acceptance: {item.get('acceptance')}",
                f"Retest: {item.get('retest')}",
                f"Severity, as stated by the analysis: {item.get('severity')}",
                f"Confidence, as stated by the analysis: {item.get('confidence')}",
                f"Priority, as stated by the analysis: {item.get('priority')}",
                "",
            ]
        )
    return "\n".join(lines)
