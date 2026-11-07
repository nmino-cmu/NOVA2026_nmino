"""Second controlled storefront. It is a separate origin, not a copy of Orbit's routes."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

_CSS = "body{font-family:Inter,system-ui,sans-serif;background:#f6f3ec;color:#1c1915;margin:0}main{max-width:640px;margin:40px auto;padding:0 20px}a,button{font:inherit}button,a.primary{background:#1c1915;color:#fff;border:0;border-radius:8px;padding:10px 14px;text-decoration:none;display:inline-block}"

_carts: dict[str, list[dict]] = {}


def _ns(request: Request) -> str:
    return request.headers.get("x-harbor-namespace") or "public"


def create_app() -> FastAPI:
    app = FastAPI()

    def page(title: str, body: str) -> HTMLResponse:
        html = f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{_CSS}</style></head><body><main><p>Harbor Goods · Controlled demo application</p>{body}</main></body></html>"
        return HTMLResponse(html, headers={"X-Harbor-Build": "harbor-v1"})

    @app.get("/health")
    def health():
        return {"ok": True, "service": "harbor-goods", "build": "harbor-v1"}

    @app.get("/", response_class=HTMLResponse)
    def home():
        return page("Harbor Goods", "<h1>Harbor Goods</h1><p><a href='/catalog'>Catalog</a></p>")

    @app.get("/catalog", response_class=HTMLResponse)
    def catalog():
        return page("Catalog", "<h1>Catalog</h1><p><a href='/product/nova-mug'>Nova Mug</a></p>")

    @app.get("/product/nova-mug", response_class=HTMLResponse)
    def product():
        return page("Nova Mug", "<h1>Nova Mug</h1><form method='post' action='/cart/add'><button type='submit'>Add to cart</button></form>")

    @app.post("/cart/add")
    async def add(request: Request):
        ns = _ns(request)
        _carts[ns] = [{"sku": "nova-mug", "qty": 1}]
        return RedirectResponse("/cart", status_code=303)

    @app.get("/cart", response_class=HTMLResponse)
    def cart(request: Request):
        items = _carts.get(_ns(request)) or []
        if items:
            body = "<h1>Cart</h1><p>Nova Mug × 1</p><p><a class='primary' href='/checkout'>Continue to checkout</a></p>"
        else:
            body = "<h1>Cart</h1><p>Empty cart</p><button disabled>Continue to checkout</button>"
        return page("Cart", body)

    @app.get("/checkout", response_class=HTMLResponse)
    def checkout(request: Request):
        items = _carts.get(_ns(request)) or []
        ready = len(items) == 1 and items[0]["sku"] == "nova-mug"
        if ready:
            body = "<h1>Checkout</h1><p data-ready='true'>Checkout is ready for one Nova Mug.</p><button type='button' disabled>Place order</button>"
        else:
            body = "<h1>Checkout</h1><p role='alert'>The cart is not ready.</p>"
        return page("Checkout", body)

    @app.post("/control/reset")
    async def reset(request: Request):
        body = await request.json()
        ns = str(body.get("namespace") or "")
        _carts[ns] = []
        return {"ok": True, "namespace": ns}

    @app.get("/control/cart")
    def control_cart(request: Request):
        return {"items": _carts.get(_ns(request)) or []}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("HARBOR_PORT", "8789")))
