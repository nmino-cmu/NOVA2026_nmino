"""Local page facts. Script source is not part of the observation."""

from __future__ import annotations

from urllib.parse import urlsplit

from playwright.async_api import Page

_SCRIPT = """
() => {
  function shown(el) {
    if (!el || el.hidden) return false;
    const style = getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return false;
    const box = el.getBoundingClientRect();
    return box.width > 0 && box.height > 0;
  }
  const controls = [];
  for (const el of document.querySelectorAll("a, button")) {
    if (!shown(el)) continue;
    const name = (el.getAttribute("aria-label") || el.innerText || "").trim().replace(/\\s+/g, " ");
    if (!name) continue;
    controls.push({
      role: el.tagName === "A" ? "link" : "button",
      name,
      enabled: !el.disabled && el.getAttribute("aria-disabled") !== "true"
    });
    if (controls.length >= 64) break;
  }
  const text = ((document.body && document.body.innerText) || "").slice(0, 4000);
  const form = document.querySelector("#checkout-form");
  const submit = form && form.querySelector("button");
  const headings = [...document.querySelectorAll("h1, h2, h3")].filter(shown).map((el) => ({
    role: "heading",
    name: (el.innerText || "").trim(),
    visible: true
  }));
  return {
    url: location.href,
    title: document.title,
    text,
    controls,
    homeVisible: location.pathname === "/" && text.includes("Orbit Supply") && text.includes("Signed out"),
    signedOutVisible: text.includes("Signed out"),
    checkoutFormEnabled: !!(form && shown(form) && submit && shown(submit) && !submit.disabled),
    errorVisible: [...document.querySelectorAll("[role=alert]")].some(shown),
    headings,
    ready: document.documentElement.dataset.ready === "true"
  };
}
"""


def page_key(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path or '/'}"


async def observe(page: Page) -> dict:
    facts = await page.evaluate(_SCRIPT)
    facts["text"] = (facts.get("text") or "")[:4000]
    return facts
