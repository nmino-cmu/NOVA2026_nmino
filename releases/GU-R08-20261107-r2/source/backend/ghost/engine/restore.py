"""Controller-only fixture reset. The browser context never receives the token."""

from __future__ import annotations

import httpx


async def orbit_health(origin: str) -> dict:
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(f"{origin}/health")
    response.raise_for_status()
    return response.json()


async def orbit_reset(origin: str, token: str, namespace: str) -> dict:
    if not token:
        return {"ok": False, "detail": "Orbit control token is missing."}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{origin}/control/reset",
            headers={"X-Orbit-Control": token},
            json={"namespace": namespace},
        )
    if response.status_code != 200:
        return {"ok": False, "detail": "Fixture reset was rejected."}
    data = response.json()
    data["ok"] = bool(data.get("ok")) and bool(data.get("initialStateHash")) and bool(data.get("resetInstanceId"))
    return data


async def orbit_set_build(origin: str, token: str, build: str) -> dict:
    if not token:
        return {"ok": False, "detail": "Orbit control token is missing."}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{origin}/control/build",
            headers={"X-Orbit-Control": token},
            json={"build": build},
        )
    if response.status_code != 200:
        return {"ok": False, "detail": "The fixture rejected the build change."}
    return response.json()


async def orbit_state(origin: str, token: str, namespace: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{origin}/control/state",
            headers={"X-Orbit-Control": token, "X-Orbit-Namespace": namespace},
        )
    response.raise_for_status()
    return response.json()
