from pathlib import Path

from ghost.engine.browser import context_headers
from ghost.engine.candidates import build, offered_queries
from ghost.hashing import action_sequence_hash
from ghost.providers.guard import find_violation
from ghost.registry import Ctx, _self_check, build_task, evaluate
from ghost.review import brief_markdown, comparability, freshness, recommendation_for
from ghost.store.projections import snapshot
from ghost.store.sqlite import Store


def test_attractive_checkout_does_not_pass_without_a_cart():
    _self_check()
    empty = {"loggedIn": False, "cart": [], "pending": [], "commitCount": 0, "orders": 0, "namespace": "n", "build": "orbit-buggy-v1"}
    page = {
        "checkoutFormEnabled": True,
        "errorVisible": False,
        "url": "http://127.0.0.1:8788/checkout?optimistic=1",
        "homeVisible": False,
        "signedOutVisible": True,
    }
    result = evaluate("orbit.checkout.v1", {}, Ctx(empty, page, 0, "n", ["http://127.0.0.1:8788"], "orbit-buggy-v1"))
    assert result["ok"] is False


def test_action_hash_ignores_ids_and_changes_with_the_target():
    action = {"id": "a", "kind": "activate", "target": {"role": "link", "name": "Catalog", "region": ""}, "dataIdentity": "", "cost": {"interactions": 1, "clicks": 1, "keyEvents": 0, "fieldFills": 0, "scrolls": 0}}
    other = {**action, "id": "b"}
    renamed = {**action, "target": {"role": "link", "name": "More", "region": ""}}
    assert action_sequence_hash([action], "p@1") == action_sequence_hash([other], "p@1")
    assert action_sequence_hash([action], "p@1") != action_sequence_hash([renamed], "p@1")


def test_guard_rejects_fenced_code_and_accepts_a_sentence():
    assert find_violation("Open the catalog.") is None
    assert find_violation("```\nprint(1)\n```") == "code_like_text"


def test_policy_module_has_no_designed_route():
    text = Path("backend/ghost/engine/policies.py").read_text(encoding="utf-8")
    assert "Express Nova Mug" not in text
    assert "Quick order" not in text
    assert "fixtures.orbit" not in text


def test_browser_headers_never_carry_the_control_token():
    headers = context_headers("http://127.0.0.1:8788/", "ns", "http://127.0.0.1:8788")
    assert headers == {"X-Orbit-Namespace": "ns"}
    assert context_headers("http://127.0.0.1:8790/milestone", "ns", "http://127.0.0.1:8788") == {}
    assert "X-Orbit-Control" not in headers


def test_rollback_publishes_no_event(tmp_path):
    store = Store(tmp_path)
    task = store.create_task(build_task({"mode": "orbit"}, orbit_origin="http://127.0.0.1:8788", model="m"))
    run = store.create_run(task_id=task["id"], policy_id="ordinary-model-v1", idempotency_key="idem-rollback-1", discovery=True, label="Investigation")
    try:
        with store.transaction():
            store._event(run["id"], "state_discovered", "x", {"summary": "nope"})
            raise RuntimeError("rollback")
    except RuntimeError:
        pass
    assert store.events_after(run["id"], 0) == []


def test_orbit_task_does_not_hardcode_the_build_in_goal_args():
    task = build_task({"mode": "orbit"}, orbit_origin="http://127.0.0.1:8788", model="m")
    assert task["goal"][0]["args"] == {}
    assert "buggy" not in str(task["goal"])


def test_a_build_change_is_comparable_and_stale(tmp_path):
    task = build_task({"mode": "orbit"}, orbit_origin="http://127.0.0.1:8788", model="m")
    from ghost.review import fingerprint

    digest = fingerprint(task, "same-route")
    assert comparability("orbit-buggy-v1", "orbit-fixed-v1", digest, digest) == "comparable_build_change"
    assert comparability("orbit-buggy-v1", "orbit-fixed-v1", digest, "other") == "not_comparable"
    assert freshness("orbit-buggy-v1", "orbit-fixed-v1") == "stale"
    assert freshness("orbit-fixed-v1", "orbit-fixed-v1") == "current"
    recommendation = recommendation_for({"id": "ver_failed"}, ["ev_1"])
    brief = brief_markdown(recommendation, "orbit-buggy-v1")
    assert "not permission to edit" in brief
    assert recommendation["source"] == "witnessed-failure"
    store = Store(tmp_path)
    created = store.create_task(task)
    run = store.create_run(task_id=created["id"], policy_id="regression.ordinary.v1", idempotency_key="idem-stale-1", discovery=False, label="Fixture regression check")
    store.apply(
        run["id"],
        records=[("verification", "ver_stale", {"id": "ver_stale", "status": "failed", "buildId": "orbit-buggy-v1", "stale": False})],
        event_type="route_verified",
        entity_id="ver_stale",
        summary="Recorded a failed checkout check",
    )
    row = store.records(run["id"], "verification")[0]
    row["stale"] = freshness(row["buildId"], "orbit-fixed-v1") == "stale"
    store.replace_record("verification", row["id"], row)
    assert store.find("verification", "ver_stale")["stale"] is True


def test_three_queries_are_offered_to_browse():
    queries = offered_queries(["notebook", "pen", "mug"], "browse")
    assert queries == ["notebook", "pen", "mug"]
    controls = [
        {"role": "searchbox", "name": "Search the shop", "enabled": True},
        {"role": "button", "name": "Add Field notebook $4", "enabled": True},
        {"role": "button", "name": "Add Leather notebook $18", "enabled": True},
    ]
    found = build(controls, set(), [], "http://shop", queries=queries, persona="browse")
    fills = [item["target"]["value"] for item in found if item["kind"] == "fill"]
    assert fills == ["notebook", "pen", "mug"]
    names = [item["target"]["name"] for item in found if item["kind"] == "activate"]
    assert names == ["Add Field notebook $4"]


def test_failed_and_stale_verifications_are_not_the_current_best(tmp_path):
    store = Store(tmp_path)
    task = store.create_task(build_task({"mode": "orbit"}, orbit_origin="http://127.0.0.1:8788", model="m"))
    run = store.create_run(task_id=task["id"], policy_id="regression.ordinary.v1", idempotency_key="idem-proj-1", discovery=False, label="Fixture check")
    store.apply(
        run["id"],
        records=[("prefix", "pfx_1", {"id": "pfx_1", "label": "Add to cart", "depth": 1, "lane": 0})],
        event_type="state_discovered",
        entity_id="pfx_1",
        summary="Witnessed cart step",
    )
    failed = {
        "id": "ver_fail",
        "routeId": "route_fail",
        "status": "failed",
        "interactions": 1,
        "repaired": False,
        "stale": False,
        "prefixIds": ["pfx_1"],
        "actions": [{"kind": "activate", "target": {"role": "button", "name": "Add to cart"}, "cost": {"interactions": 1}}],
        "detail": "Authoritative cart is not exactly one Nova Mug.",
        "buildId": "orbit-buggy-v1",
    }
    store.apply(run["id"], records=[("verification", "ver_fail", failed)], event_type="route_verified", entity_id="ver_fail", summary="Replay failed")
    body = snapshot(store, run["id"])
    assert body["projection"]["bestVerified"] is None
    assert body["projection"]["nodes"][0]["status"] == "failed"
    passed = {**failed, "id": "ver_old", "status": "passed", "stale": True, "buildId": "orbit-buggy-v1"}
    store.apply(run["id"], records=[("verification", "ver_old", passed)], event_type="route_verified", entity_id="ver_old", summary="Older pass")
    body = snapshot(store, run["id"])
    assert body["projection"]["bestVerified"] is None
    assert body["projection"]["nodes"][0]["status"] != "verified"
    assert body["projection"]["nodes"][0]["freshness"] == "stale"
    assert body["projection"]["routes"]["historical"]


def test_heading_alone_does_not_pass_the_shop_cart():
    page = {
        "url": "http://127.0.0.1:8788/shop",
        "headings": [{"name": "Cart ready"}],
        "cartText": "In the cart:",
        "priceCeiling": "80",
        "errorVisible": False,
        "controls": [],
    }
    result = evaluate(
        "shop.cart.v1",
        {"required": ["Field notebook $4"], "banned": ["Leather notebook $18"], "maxPrice": 40},
        Ctx(None, page, 0, "n", ["http://127.0.0.1:8788"], None),
    )
    assert result["ok"] is False
    bare = dict(page, errorVisible=None, checkoutFormEnabled=True)
    checkout = evaluate("orbit.checkout.v1", {}, Ctx({"cart": [{"sku": "nova-mug", "qty": 1}], "commitCount": 1, "pending": [], "orders": 0, "loggedIn": False}, bare, 0, "n", ["http://127.0.0.1:8788"], None))
    assert checkout["ok"] is False
    assert evaluate("visible_milestone.v1", {"urlIncludes": "/", "targets": []}, Ctx(None, page, 0, "n", ["http://127.0.0.1:8788"], None))["ok"] is False


def test_failure_recommendation_uses_task_checks():
    recommendation = recommendation_for(
        {"id": "ver_other", "detail": "Cart is missing Field notebook $4.", "actions": [{"target": {"name": "Search"}}]},
        ["ev_2"],
        {"objective": "Add a notebook, a pen, and a mug.", "checks": [{"id": "shop.cart.v1"}]},
    )
    assert recommendation["claim"] == "Cart is missing Field notebook $4."
    assert recommendation["acceptance"] == ["shop.cart.v1"]


def test_workspace_does_not_call_a_failed_step_count_verified():
    text = Path("frontend/src/components/WorkspaceScreen.tsx").read_text(encoding="utf-8")
    assert "latestVerification?.interactions" not in text
    assert "explored" not in text
