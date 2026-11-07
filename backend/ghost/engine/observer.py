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
  function label(el) {
    const named = el.getAttribute("aria-label") || el.getAttribute("placeholder") || "";
    const wrapped = el.closest("label");
    const text = named || (wrapped && wrapped.innerText) || el.innerText || "";
    return text.trim().replace(/\\s+/g, " ").slice(0, 80);
  }
  const controls = [];
  const fields = [];
  function push(bucket, entry) {
    if (bucket.length >= 64) return;
    bucket.push(entry);
  }
  for (const el of document.querySelectorAll("input, textarea")) {
    if (!shown(el) || el.disabled) continue;
    const kind = (el.getAttribute("type") || "text").toLowerCase();
    if (kind === "hidden" || kind === "password" || kind === "checkbox" || kind === "radio") continue;
    if (kind === "submit" || kind === "image") {
      const name = (el.getAttribute("aria-label") || el.getAttribute("value") || el.getAttribute("alt") || "Submit").trim();
      if (name) push(controls, { role: "button", name: name.slice(0, 80), enabled: !el.disabled });
      continue;
    }
    const name = label(el);
    if (!name) continue;
    if (kind === "range") push(fields, { role: "slider", name, enabled: true });
    else if (kind === "search" || kind === "text" || el.tagName === "TEXTAREA") push(fields, { role: kind === "search" ? "searchbox" : "textbox", name, enabled: true });
  }
  for (const el of document.querySelectorAll("[draggable=true]")) {
    if (!shown(el)) continue;
    const name = label(el);
    if (name) push(fields, { role: "draggable", name, enabled: true });
  }
  for (const el of document.querySelectorAll("[data-drop]")) {
    if (!shown(el)) continue;
    const name = label(el);
    if (name) push(fields, { role: "drop", name, enabled: true });
  }
  for (const el of document.querySelectorAll("a, button")) {
    if (!shown(el)) continue;
    const name = label(el);
    if (!name) continue;
    push(controls, {
      role: el.tagName === "A" ? "link" : "button",
      name,
      enabled: !el.disabled && el.getAttribute("aria-disabled") !== "true"
    });
  }
  const merged = [...fields.slice(0, 16), ...controls].slice(0, 64);
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
    controls: merged,
    homeVisible: location.pathname === "/" && text.includes("Orbit Supply") && text.includes("Signed out"),
    signedOutVisible: text.includes("Signed out"),
    checkoutFormEnabled: !!(form && shown(form) && submit && shown(submit) && !submit.disabled),
    errorVisible: [...document.querySelectorAll("[role=alert]")].some(shown),
    alerts: [...document.querySelectorAll("[role=alert], [role=status]")].filter(shown).map((el) => (el.innerText || "").trim().replace(/\\s+/g, " ").slice(0, 160)).filter(Boolean).slice(0, 3),
    headings,
    ready: document.documentElement.dataset.ready === "true",
    cartText: ((document.querySelector("#bag") && document.querySelector("#bag").innerText) || "").trim(),
    priceCeiling: document.querySelector("#price") ? document.querySelector("#price").value : null
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
