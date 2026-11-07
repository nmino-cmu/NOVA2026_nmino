"""Orbit Supply, a controlled demo storefront with a real cart."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

DATASET = "orbit-data-1"
SKU = "nova-mug"
_LOCK = threading.Lock()

_CSS = """
:root { color-scheme: light; --bg:#efeae2; --ink:#1c1915; --muted:#5e584e; --card:#fffdf9;
  --line:#e3d9cc; --accent:#0f6e62; --danger:#9d2c2c; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:16px/1.45 "Avenir Next", "Segoe UI", sans-serif; }
a { color: inherit; }
.wrap { max-width:1040px; margin:0 auto; padding:28px 24px 64px; }
header { display:flex; justify-content:space-between; gap:24px; align-items:center; }
.brand { font-weight:700; font-size:22px; text-decoration:none; }
.meta { color:var(--muted); margin:0; }
nav { display:flex; flex-wrap:wrap; gap:10px; margin:22px 0; }
nav a, nav button, .action, button {
  min-height:44px; padding:0 16px; border-radius:10px; border:1px solid var(--line);
  background:#fffdf9; color:var(--ink); font:inherit; text-decoration:none;
  display:inline-flex; align-items:center; cursor:pointer; }
button.express, a.primary { background:var(--accent); color:white; border-color:transparent; }
button:disabled { opacity:.45; cursor:not-allowed; }
main { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:28px; }
h1 { font-size:40px; line-height:1.1; margin:0 0 8px; }
.price { font-size:20px; margin:0 0 12px; }
.row { display:flex; gap:12px; flex-wrap:wrap; margin-top:18px; }
[role=alert] { background:#fde8e4; color:var(--danger); padding:12px 14px; border-radius:10px; }
[role=status] { color:var(--accent); font-weight:650; }
label { display:block; margin:12px 0; }
input { display:block; margin-top:6px; min-height:40px; width:min(360px, 100%);
  border:1px solid var(--line); border-radius:8px; padding:0 10px; font:inherit; }
:focus-visible { outline:3px solid var(--accent); outline-offset:2px; }
"""

_HOME_JS = """
function shown(open) { return open ? "true" : "false"; }
function wireHome(awaitsCommit) {
  const more = document.getElementById("more");
  const morePanel = document.getElementById("more-panel");
  const quick = document.getElementById("quick");
  const quickPanel = document.getElementById("quick-panel");
  const quickMug = document.getElementById("quick-mug");
  const express = document.getElementById("express");
  more.addEventListener("click", () => {
    const opening = morePanel.hasAttribute("hidden");
    if (opening) morePanel.removeAttribute("hidden");
    else morePanel.setAttribute("hidden", "");
    more.setAttribute("aria-expanded", shown(opening));
  });
  quick.addEventListener("click", () => {
    const opening = quickPanel.hasAttribute("hidden");
    if (opening) quickPanel.removeAttribute("hidden");
    else quickPanel.setAttribute("hidden", "");
    quick.setAttribute("aria-expanded", shown(opening));
  });
  quickMug.addEventListener("click", async () => {
    document.documentElement.dataset.busy = "1";
    quickMug.disabled = true;
    try {
      const res = await fetch("/api/cart/items", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({sku: "nova-mug", qty: 1})
      });
      if (!res.ok) throw new Error("add");
      location.assign("/checkout");
    } catch (err) {
      document.documentElement.dataset.busy = "0";
      quickMug.disabled = false;
      const box = document.getElementById("quick-error");
      box.hidden = false;
    }
  });
  express.addEventListener("click", async () => {
    if (awaitsCommit) {
      document.documentElement.dataset.busy = "1";
      express.disabled = true;
      const res = await fetch("/api/cart/items", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({sku: "nova-mug", qty: 1})
      });
      if (!res.ok) { document.documentElement.dataset.busy = "0"; return; }
      location.assign("/checkout");
      return;
    }
    const timer = setTimeout(() => {
      fetch("/api/cart/items", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({sku: "nova-mug", qty: 1})
      });
    }, 5000);
    window.addEventListener("pagehide", () => clearTimeout(timer), {once: true});
    location.assign("/checkout?optimistic=1");
  });
}
"""

_CHECKOUT_JS = """
setTimeout(async () => {
  const cart = await fetch("/api/cart").then((r) => r.json());
  const count = (cart.items || []).reduce((n, item) => n + item.qty, 0);
  const label = document.getElementById("cart-label");
  if (label) label.textContent = count ? count + " in cart" : "Empty cart";
  const ok = (cart.items || []).length === 1 && cart.items[0].sku === "nova-mug" && cart.items[0].qty === 1;
  if (!ok) {
    document.getElementById("ready-note").hidden = true;
    document.getElementById("express-error").hidden = false;
    const button = document.querySelector("#checkout-form button");
    if (button) button.disabled = true;
  }
}, 900);
"""


def _hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def create_app(*, db_path: Path, token: str, build: str) -> FastAPI:
    fixed = build == "orbit-fixed-v1"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
          namespace TEXT PRIMARY KEY,
          generation INTEGER NOT NULL,
          orders INTEGER NOT NULL,
          logged_in INTEGER NOT NULL,
          reset_instance_id TEXT
        );
        CREATE TABLE IF NOT EXISTS cart (
          namespace TEXT NOT NULL,
          sku TEXT NOT NULL,
          qty INTEGER NOT NULL,
          PRIMARY KEY (namespace, sku)
        );
        CREATE TABLE IF NOT EXISTS commits (
          id TEXT PRIMARY KEY,
          namespace TEXT NOT NULL,
          generation INTEGER NOT NULL,
          sku TEXT NOT NULL,
          qty INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pending (
          id TEXT PRIMARY KEY,
          namespace TEXT NOT NULL,
          generation INTEGER NOT NULL
        );
        """
    )

    def ns_of(request: Request) -> str:
        return request.headers.get("x-orbit-namespace") or "public"

    def authorized(request: Request) -> bool:
        if not token:
            return False
        got = request.headers.get("x-orbit-control") or ""
        return len(got) == len(token) and hmac.compare_digest(got, token)

    def read_state(ns: str) -> dict:
        meta = conn.execute("SELECT * FROM meta WHERE namespace=?", (ns,)).fetchone()
        rows = conn.execute(
            "SELECT sku, qty FROM cart WHERE namespace=? ORDER BY sku", (ns,)
        ).fetchall()
        commits = conn.execute(
            "SELECT COUNT(*) AS n FROM commits WHERE namespace=?", (ns,)
        ).fetchone()["n"]
        pending = [
            row["id"]
            for row in conn.execute("SELECT id FROM pending WHERE namespace=? ORDER BY id", (ns,))
        ]
        cart = [{"sku": row["sku"], "qty": row["qty"]} for row in rows]
        state = {
            "build": build,
            "dataset": DATASET,
            "namespace": ns,
            "generation": meta["generation"] if meta else 0,
            "loggedIn": bool(meta["logged_in"]) if meta else False,
            "orders": meta["orders"] if meta else 0,
            "pending": pending,
            "cart": cart,
            "commitCount": commits,
            "resetInstanceId": meta["reset_instance_id"] if meta else None,
        }
        state["initialStateHash"] = _hash(
            {
                "build": build,
                "dataset": DATASET,
                "loggedIn": state["loggedIn"],
                "orders": state["orders"],
                "pending": state["pending"],
                "cart": state["cart"],
                "commitCount": state["commitCount"],
            }
        )
        return state

    def ensure(ns: str) -> int:
        row = conn.execute("SELECT generation FROM meta WHERE namespace=?", (ns,)).fetchone()
        if row:
            return row["generation"]
        conn.execute(
            "INSERT INTO meta(namespace, generation, orders, logged_in, reset_instance_id) VALUES(?,1,0,0,NULL)",
            (ns,),
        )
        return 1

    def add_sku(ns: str, sku: str, qty: int, generation: int | None) -> bool:
        if sku != SKU or qty != 1:
            return False
        with _LOCK:
            conn.execute("BEGIN IMMEDIATE")
            try:
                current = ensure(ns)
                if generation is not None and generation != current:
                    conn.rollback()
                    return False
                row = conn.execute(
                    "SELECT qty FROM cart WHERE namespace=? AND sku=?", (ns, sku)
                ).fetchone()
                new_qty = (row["qty"] if row else 0) + qty
                conn.execute(
                    """INSERT INTO cart(namespace, sku, qty) VALUES(?,?,?)
                       ON CONFLICT(namespace, sku) DO UPDATE SET qty=excluded.qty""",
                    (ns, sku, new_qty),
                )
                conn.execute(
                    "INSERT INTO commits(id, namespace, generation, sku, qty) VALUES(?,?,?,?,?)",
                    ("cmt_" + uuid.uuid4().hex[:16], ns, current, sku, qty),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return True

    def reset(ns: str) -> dict:
        with _LOCK:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("SELECT generation FROM meta WHERE namespace=?", (ns,)).fetchone()
                gen = (row["generation"] + 1) if row else 1
                reset_id = "rst_" + uuid.uuid4().hex[:16]
                conn.execute("DELETE FROM cart WHERE namespace=?", (ns,))
                conn.execute("DELETE FROM commits WHERE namespace=?", (ns,))
                conn.execute("DELETE FROM pending WHERE namespace=?", (ns,))
                conn.execute(
                    """INSERT INTO meta(namespace, generation, orders, logged_in, reset_instance_id)
                       VALUES(?,?,0,0,?)
                       ON CONFLICT(namespace) DO UPDATE SET
                         generation=excluded.generation, orders=0, logged_in=0,
                         reset_instance_id=excluded.reset_instance_id""",
                    (ns, gen, reset_id),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        state = read_state(ns)
        state["ok"] = (
            state["cart"] == []
            and state["orders"] == 0
            and state["pending"] == []
            and state["commitCount"] == 0
            and state["loggedIn"] is False
            and state["resetInstanceId"] == reset_id
        )
        return state

    def cart_label(state: dict, fake: bool) -> str:
        if fake:
            return "1 in cart"
        qty = sum(item["qty"] for item in state["cart"])
        return f"{qty} in cart" if qty else "Empty cart"

    def layout(title: str, body: str, state: dict, *, script: str = "", fake_cart: bool = False) -> HTMLResponse:
        html = f"""<!doctype html>
<html lang="en" data-ready="true">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{_CSS}</style></head>
<body>
<div class="wrap">
<header>
  <a class="brand" href="/">Orbit Supply</a>
  <div>
    <p class="meta" id="session-label">Signed out</p>
    <p class="meta" id="cart-label">{cart_label(state, fake_cart)}</p>
  </div>
</header>
{body}
</div>
<script>{script}</script>
</body></html>"""
        return HTMLResponse(html, headers={"Cache-Control": "no-store", "X-Orbit-Build": build})

    app = FastAPI()

    @app.middleware("http")
    async def no_store(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Orbit-Build"] = build
        return response

    @app.get("/health")
    def health():
        return {"ok": True, "service": "orbit-supply", "build": build, "dataset": DATASET}

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        state = read_state(ns_of(request))
        awaits = "true" if fixed else "false"
        body = """
<nav aria-label="Shop">
  <a href="/catalog">Catalog</a>
  <button type="button" id="more" aria-expanded="false" aria-controls="more-panel">More</button>
  <button type="button" id="express" class="express">Express Nova Mug</button>
</nav>
<div id="more-panel" hidden>
  <button type="button" id="quick" aria-expanded="false" aria-controls="quick-panel">Quick order</button>
  <div id="quick-panel" hidden>
    <p id="quick-error" role="alert" hidden>Could not add Nova Mug.</p>
    <button type="button" id="quick-mug">Nova Mug checkout</button>
  </div>
</div>
<main>
  <h1>Orbit Supply</h1>
  <p>Desk goods for late launches. Start from the catalog, or use the menu.</p>
</main>"""
        return layout("Orbit Supply", body, state, script=_HOME_JS + f"\nwireHome({awaits});\n")

    @app.get("/catalog", response_class=HTMLResponse)
    def catalog(request: Request):
        state = read_state(ns_of(request))
        body = """
<main>
  <h1>Catalog</h1>
  <article>
    <h2><a href="/product/nova-mug">Nova Mug</a></h2>
    <p class="price">$28</p>
    <p>A heavy ceramic mug for the desk.</p>
  </article>
</main>"""
        return layout("Catalog", body, state)

    @app.get("/product/nova-mug", response_class=HTMLResponse)
    def product(request: Request):
        state = read_state(ns_of(request))
        in_cart = any(item["sku"] == SKU and item["qty"] >= 1 for item in state["cart"])
        note = "<p role='status'>Nova Mug is in the cart.</p>" if request.query_params.get("added") == "1" else ""
        if in_cart:
            add = '<button type="button" disabled>In cart</button>'
        else:
            add = """<form method="post" action="/cart/add"><button type="submit">Add to cart</button></form>"""
        body = f"""
<nav aria-label="Shop"><a href="/catalog">Catalog</a></nav>
<main>
  <h1>Nova Mug</h1>
  <p class="price">$28</p>
  {note}
  <p>Holds twelve ounces. One is enough.</p>
  <div class="row">{add}<a href="/cart">View cart</a></div>
</main>"""
        return layout("Nova Mug", body, state)

    @app.post("/cart/add")
    async def cart_add(request: Request):
        ok = add_sku(ns_of(request), SKU, 1, None)
        if not ok:
            return JSONResponse({"ok": False}, status_code=400)
        return RedirectResponse("/product/nova-mug?added=1", status_code=303)

    @app.post("/api/cart/items")
    async def api_add(request: Request):
        body = await request.json()
        generation = body.get("generation")
        if generation is not None:
            generation = int(generation)
        ok = add_sku(ns_of(request), str(body.get("sku") or ""), int(body.get("qty") or 0), generation)
        if not ok:
            return JSONResponse({"ok": False}, status_code=409)
        return {"ok": True, "cart": read_state(ns_of(request))["cart"]}

    @app.get("/api/cart")
    def api_cart(request: Request):
        state = read_state(ns_of(request))
        return {"items": [{"sku": i["sku"], "name": "Nova Mug", "qty": i["qty"]} for i in state["cart"]]}

    @app.get("/cart", response_class=HTMLResponse)
    def cart_page(request: Request):
        state = read_state(ns_of(request))
        one = state["cart"] == [{"sku": SKU, "qty": 1}]
        if one:
            action = '<a class="primary" href="/checkout">Continue to checkout</a>'
            lines = "<p>Nova Mug × 1</p><p>$28</p>"
        else:
            action = '<button type="button" disabled>Continue to checkout</button>'
            lines = "<p>Your cart is empty.</p>" if not state["cart"] else "<p>The cart does not match a single Nova Mug.</p>"
        body = f"""
<nav aria-label="Shop"><a href="/catalog">Catalog</a></nav>
<main><h1>Cart</h1>{lines}<div class="row">{action}</div></main>"""
        return layout("Cart", body, state)

    @app.get("/checkout", response_class=HTMLResponse)
    def checkout(request: Request):
        state = read_state(ns_of(request))
        optimistic = request.query_params.get("optimistic") == "1"
        real = state["cart"] == [{"sku": SKU, "qty": 1}]
        show_ready = optimistic or real
        if show_ready:
            form = """
<p id="ready-note" role="status">Checkout ready</p>
<p>Nova Mug × 1</p>
<form id="checkout-form" method="post" action="/checkout/place">
  <label>Name <input name="name" autocomplete="name"></label>
  <label>Email <input name="email" type="email" autocomplete="email"></label>
  <button type="submit">Place order</button>
</form>
<p id="express-error" role="alert" hidden>The Express cart update did not complete. Your cart is empty.</p>"""
        else:
            form = """
<p role="alert">Your cart is empty.</p>
<form id="checkout-form">
  <button type="submit" disabled>Place order</button>
</form>
<p><a href="/catalog">Catalog</a></p>"""
        script = _CHECKOUT_JS if optimistic else ""
        body = f'<nav aria-label="Shop"><a href="/catalog">Catalog</a></nav><main><h1>Checkout</h1>{form}</main>'
        return layout("Checkout", body, state, script=script, fake_cart=optimistic)

    @app.post("/checkout/place")
    async def place(request: Request):
        ns = ns_of(request)
        with _LOCK:
            conn.execute("BEGIN IMMEDIATE")
            try:
                state = read_state(ns)
                if state["cart"] != [{"sku": SKU, "qty": 1}]:
                    conn.rollback()
                    return JSONResponse({"ok": False}, status_code=400)
                conn.execute("UPDATE meta SET orders = orders + 1 WHERE namespace=?", (ns,))
                conn.execute("DELETE FROM cart WHERE namespace=?", (ns,))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return layout(
            "Order placed",
            "<main><h1>Order placed</h1><p role='status'>The order was recorded.</p></main>",
            read_state(ns),
        )

    @app.get("/milestone", response_class=HTMLResponse)
    def milestone():
        body = """
<main>
  <h1>Field note</h1>
  <p>A separate local page with no cart.</p>
  <button type="button" id="show">Show milestone</button>
  <h2 id="reached" hidden>Milestone reached</h2>
</main>
<script>
document.getElementById("show").addEventListener("click", () => {
  document.getElementById("reached").hidden = false;
});
</script>"""
        empty = {
            "cart": [],
            "loggedIn": False,
            "orders": 0,
            "pending": [],
            "commitCount": 0,
        }
        return layout("Field note", body, empty)

    @app.post("/control/reset")
    async def control_reset(request: Request):
        if not authorized(request):
            return JSONResponse({"error": "not found"}, status_code=404)
        body = await request.json()
        ns = str(body.get("namespace") or "")
        if not ns or "/" in ns or ".." in ns:
            return JSONResponse({"ok": False}, status_code=400)
        return reset(ns)

    @app.get("/control/state")
    def control_state(request: Request):
        if not authorized(request):
            return JSONResponse({"error": "not found"}, status_code=404)
        return read_state(ns_of(request))

    app.state.orbit_read = read_state
    app.state.orbit_add = add_sku
    app.state.orbit_reset = reset
    return app


def _default_app() -> FastAPI:
    root = Path(__file__).resolve().parents[2]
    data = Path(os.environ.get("GHOST_DATA_DIR") or (root / ".data"))
    return create_app(
        db_path=Path(os.environ.get("ORBIT_DB") or (data / "orbit.sqlite3")),
        token=os.environ.get("ORBIT_CONTROL_TOKEN", ""),
        build=os.environ.get("ORBIT_BUILD", "orbit-buggy-v1"),
    )


app = _default_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("ORBIT_PORT", "8788")))
