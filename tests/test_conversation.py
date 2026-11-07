import pytest

from ghost.conversation import (
    FACTS_NOTE,
    automated_check,
    brief_markdown,
    ceiling_note,
    count_backtracks,
    edit_finding,
    fallback_plan,
    ground_report,
    local_fixture_shop,
    public_target_error,
    load_conversation,
    new_conversation,
    normalize_plan,
    plain_state,
    save_conversation,
)
from ghost.engine.policies import prompt_payload
from ghost.providers.openrouter import _parse_document
from ghost.registry import build_task, note_goal


def test_public_demo_accepts_only_public_links():
    assert public_target_error("http://127.0.0.1:8788/shop")
    assert public_target_error("http://localhost/shop")
    assert public_target_error("http://10.1.2.3/")
    assert public_target_error("https://1.1.1.1/") is None
    assert local_fixture_shop("http://127.0.0.1:8788/shop")
    assert not local_fixture_shop("https://example.com/shop")
    plan = fallback_plan("https://example.com/shop", "Look around the site.")
    assert plan["queries"] == []


def test_a_json_fence_is_unwrapped_and_code_is_still_rejected():
    data, error = _parse_document('```json\n{"reply": "Here is a plan."}\n```')
    assert error is None
    assert data["reply"] == "Here is a plan."
    data, error = _parse_document("```\ndef foo():\n    pass\n```")
    assert data is None
    assert error == "code_like_text"


def test_plan_clamps_budget_and_keeps_a_custom_profile(tmp_path):
    plan = normalize_plan(
        {
            "url": "http://127.0.0.1:8788/shop",
            "task": "Find a mug",
            "personas": [
                {"id": "price", "profile": "Look at prices."},
                {"id": "night owl", "name": "Night owl", "profile": "Prefer obvious buttons."},
            ],
            "queries": ["a", "b", "c", "d"],
            "budget": {"requests": 100},
        },
        url="",
        user_text="Find a mug",
    )
    assert plan["budget"]["requests"] == 20
    assert plan["queries"] == ["a", "b", "c"]
    assert plan["personas"][0]["canTest"]
    assert plan["personas"][1]["id"] == "night-owl"
    assert "population" in plan["uncertain"][0]
    assert "cart text" in plan["automatedCheck"]
    record = new_conversation()
    record["plan"] = plan
    save_conversation(tmp_path, record)
    assert load_conversation(tmp_path, record["id"])["plan"]["task"] == "Find a mug"


def test_failed_run_stays_incomplete_and_unknown_evidence_is_dropped():
    report = ground_report(
        {
            "summary": "The price shopper stopped.",
            "personas": [{"name": "Price-conscious shopper", "completed": True, "conditions": ""}],
            "findings": [
                {
                    "title": "Search was blocked",
                    "observed": "Search was blocked",
                    "kind": "fact",
                    "evidenceIds": ["ev_real", "ev_invented"],
                }
            ],
        },
        {
            "personas": [
                {
                    "name": "Price-conscious shopper",
                    "status": "failed",
                    "stopReason": "search_envelope_exhausted",
                    "checks": [{"name": "Goal", "detail": "Cart was empty."}],
                    "evidence": [{"id": "ev_real", "label": "Search"}],
                    "actionCount": 3,
                    "blockedCount": 1,
                    "backtracks": 0,
                    "elapsedMs": 1000,
                    "requests": 2,
                    "browserActions": 3,
                }
            ]
        },
        screenshot_count=0,
    )
    assert report["personas"][0]["completed"] is False
    assert report["findings"][0]["evidenceIds"] == ["ev_real"]
    assert "model" in FACTS_NOTE


def test_prompt_carries_the_profile_as_a_preference():
    payload = prompt_payload(
        {
            "task": "Do not place an order.",
            "objective": "Cart",
            "personaName": "Price-conscious shopper",
            "personaProfile": "Compare prices.",
            "personaPriorities": "Affordability",
        },
        {"url": "http://127.0.0.1:8788/shop", "text": "notebook"},
        [],
        [],
    )
    assert payload["persona"]["profile"] == "Compare prices."
    assert any("does not override" in item for item in payload["constraints"])


def test_custom_persona_is_allowed_when_it_has_a_profile():
    spec = build_task(
        {
            "mode": "supplied",
            "url": "http://127.0.0.1:8788/shop",
            "targetName": "Cart ready",
            "task": "Add the cheap items.",
            "persona": "night",
            "personaProfile": "Prefer obvious buttons.",
            "personaName": "Night owl",
        },
        orbit_origin="http://127.0.0.1:8788",
        model="m",
    )
    assert "Prefer obvious buttons." in spec["task"]
    assert spec["goal"][0]["id"] == "shop.cart.v1"
    with pytest.raises(ValueError):
        build_task(
            {
                "mode": "supplied",
                "url": "http://127.0.0.1:8788/shop",
                "targetName": "Cart ready",
                "persona": "night",
            },
            orbit_origin="http://127.0.0.1:8788",
            model="m",
        )


def test_backtracks_count_a_return_and_queued_state_is_a_wait():
    assert count_backtracks(["/a", "/b", "/a", "/a"]) == 1
    state, explanation = plain_state({"status": "queued", "projection": {}})
    assert state == "queued"
    assert "Waiting" in explanation
    plan = fallback_plan("http://127.0.0.1:8788/shop", "Add the cheap mug.")
    assert plan["queries"] == ["notebook"]
    assert "Cart ready" not in automated_check({"url": "https://example.com", "visibleOutcome": ""}) or "Done" in automated_check({"url": "https://example.com", "visibleOutcome": ""})
    record = {"plan": {"task": "Add the mug."}, "report": {"findings": [
        {"title": "Keep", "status": "accepted", "kind": "recommendation", "where": "Cart", "observed": "Saw the cart", "personas": "Hurried", "goal": "Open the cart", "impact": "Uncertain", "change": "Label the cart", "why": "The control was unlabeled", "acceptance": "The cart name is visible", "retest": "Run the hurried shopper again", "severity": "high", "confidence": "low", "priority": "first"},
        {"title": "Drop", "status": "rejected"},
    ]}}
    brief = brief_markdown(record)
    assert "Keep" in brief
    assert "Drop" not in brief
    assert "does not change the repository" in brief
    record["report"]["findings"][0]["id"] = "f1"
    edit_finding(record, "f1", {"change": "Name the cart control.", "status": "edited"})
    assert record["report"]["findings"][0]["change"] == "Name the cart control."
    assert record["report"]["findings"][0]["status"] == "edited"
    with pytest.raises(KeyError):
        edit_finding(record, "missing", {})


def test_a_failed_goal_is_kept_and_a_high_ceiling_is_the_recorded_reason():
    shop = {
        "url": "http://127.0.0.1:8788/shop",
        "cartText": "Field notebook $4 Basic ballpoint pen $2 Ceramic mug $6",
        "priceCeiling": "80",
    }
    attempts, ok, changed = note_goal([], shop, [{"ok": False, "detail": "Price ceiling is 80.0, above 40."}])
    assert ok is False and changed is True
    attempts, _, again = note_goal(attempts, shop, [{"ok": False, "detail": "Price ceiling is 80.0, above 40."}])
    assert again is False and len(attempts) == 1
    attempts, _, changed = note_goal(
        attempts,
        {"url": "http://127.0.0.1:8788/catalog", "cartText": "", "priceCeiling": None},
        [{"ok": False, "detail": "Cart is missing Field notebook $4."}],
    )
    assert changed is True and len(attempts) == 2
    note = ceiling_note(attempts)
    assert "80" in note and "40" in note and "does not move the ceiling" in note


def test_ui_scan_skips_broad_clarifying_questions():
    from ghost.conversation import interpret_plan

    reply, plan = interpret_plan(
        {
            "reply": "Here is a UI review plan.",
            "plan": {
                "url": "https://example.com",
                "kind": "review",
                "task": "Scan and give UI feedback",
                "personas": [{"id": "executive"}, {"id": "mobile"}],
            },
        },
        url="https://example.com",
        user_text="Scan this site and give general UI feedback.",
        prior_user_turns=1,
    )
    assert plan is not None
    assert plan["kind"] == "review"
    assert "Who is this for" not in reply


def test_a_broad_review_asks_before_it_fills_a_plan():
    from ghost.conversation import interpret_plan

    reply, plan = interpret_plan(
        {"reply": "Orbit Supply is a small storefront.", "plan": {"url": "http://127.0.0.1:8788/", "task": "Review"}},
        url="http://127.0.0.1:8788/",
        user_text="Review this website generally.",
        prior_user_turns=1,
    )
    assert plan is None
    assert "Who is this for" in reply
    _, later = interpret_plan(
        {"reply": "Here is the plan.", "plan": {"url": "http://127.0.0.1:8788/", "kind": "review", "task": "Review the home page"}},
        url="http://127.0.0.1:8788/",
        user_text="First-time visitors. I care about clarity. Look at the home page and catalog.",
        prior_user_turns=2,
    )
    assert later is not None
    assert later["kind"] == "review"


def test_a_review_does_not_hunt_for_done_and_unknown_widgets_are_dropped():
    spec = build_task(
        {
            "mode": "supplied",
            "url": "http://127.0.0.1:8788/",
            "check": "explore",
            "paths": ["/", "/catalog"],
            "task": "Review the site generally.",
        },
        orbit_origin="http://127.0.0.1:8788",
        model="m",
    )
    assert spec["goal"][0]["id"] == "review.open.v1"
    assert spec["goal"][0]["args"]["paths"] == ["/", "/catalog"]
    assert "Done" not in spec["checks"][1]["label"]
    plan = normalize_plan(
        {
            "url": "https://example.com",
            "kind": "review",
            "task": "Review this website generally.",
            "dashboard": {"widgets": ["journey", "exec", "coverage"]},
        },
        url="",
        user_text="Review this website generally.",
    )
    assert plan["dashboard"]["widgets"] == ["journey", "coverage"]
    assert plan["tasks"][0]["check"] == "explore"
    assert "Done" not in plan["automatedCheck"]
    assert "cart text" not in plan["automatedCheck"]
    from ghost.engine.personas import REVIEW_PROFILES

    review = fallback_plan("https://example.com", "Scan the site and give general UI feedback.")
    assert [item["id"] for item in review["personas"]] == [item["id"] for item in REVIEW_PROFILES]


def test_a_price_label_must_appear_in_the_record():
    report = ground_report(
        {
            "summary": "The catalog mixed prices.",
            "findings": [
                {
                    "title": "Expensive pen stayed visible",
                    "observed": "The page showed Add Gel pen $9 next to the cheap pen.",
                    "kind": "fact",
                    "evidenceIds": ["ev_pen"],
                }
            ],
        },
        {
            "personas": [
                {
                    "name": "Shopper",
                    "status": "stopped",
                    "steps": [{"summary": "Activated Pens", "visible": ["Add Basic ballpoint pen $2"]}],
                    "evidence": [{"id": "ev_pen", "label": "Pens"}],
                    "checks": [],
                    "goalAttempts": [],
                }
            ]
        },
        screenshot_count=1,
    )
    finding = report["findings"][0]
    assert finding["supported"] is False
    assert "Add Gel pen $9" in finding["observed"]


def test_a_same_url_does_not_prove_the_page_was_unchanged():
    report = ground_report(
        {
            "summary": "More did nothing.",
            "findings": [
                {"title": "More is a dead control", "observed": "Activated More and there was no observable change.", "kind": "fact", "evidenceIds": ["ev_more"]},
            ],
        },
        {
            "personas": [
                {
                    "name": "Visitor",
                    "status": "stopped",
                    "steps": [{"summary": "Activated More", "url": "http://127.0.0.1:8788/", "visible": ["Quick order"]}],
                    "evidence": [{"id": "ev_more", "label": "More"}],
                    "checks": [],
                    "goalAttempts": [],
                }
            ]
        },
        screenshot_count=1,
    )
    finding = report["findings"][0]
    assert finding["supported"] is False
    assert "does not say the page content stayed the same" in finding["observed"]


def test_an_unrelated_screenshot_does_not_support_a_claim():
    report = ground_report(
        {
            "summary": "A claim.",
            "findings": [
                {"title": "Purple button", "observed": "The checkout button is purple", "kind": "fact", "evidenceIds": ["ev_real"]},
                {"title": "Search blocked", "observed": "Search was blocked", "kind": "fact", "evidenceIds": ["ev_real"]},
            ],
        },
        {
            "personas": [
                {
                    "name": "Visitor",
                    "status": "stopped",
                    "checks": [{"name": "Goal", "status": "failed", "detail": "Search was blocked."}],
                    "steps": [{"summary": "Search was blocked"}],
                    "evidence": [{"id": "ev_real", "label": "Search"}],
                }
            ],
            "checkAlignment": "",
        },
        screenshot_count=1,
    )
    purple, search = report["findings"]
    assert purple["supported"] is False
    assert purple["evidenceIds"] == []
    assert search["supported"] is True
    assert search["evidence"][0]["label"] == "Search"
