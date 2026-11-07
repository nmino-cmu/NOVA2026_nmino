from pathlib import Path

from ghost.engine.browser import context_headers
from ghost.hashing import action_sequence_hash
from ghost.providers.guard import find_violation
from ghost.registry import Ctx, _self_check, build_task, evaluate
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
