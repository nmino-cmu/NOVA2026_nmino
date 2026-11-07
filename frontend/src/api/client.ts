import type {
  CreateRunBody,
  CreateRunResponse,
  CreateTaskResponse,
  FixtureCheckBody,
  PlaybackPayload,
  RunListItem,
  RunSnapshot,
  TaskDraftBody,
  TaskDraftResponse,
} from "../types/api";

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function createTaskDraft(body: TaskDraftBody): Promise<TaskDraftResponse> {
  return fetch("/api/task-drafts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => parseJson<TaskDraftResponse>(r));
}

export function createTask(draft: TaskDraftResponse): Promise<CreateTaskResponse> {
  return fetch("/api/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(draft),
  }).then((r) => parseJson<CreateTaskResponse>(r));
}

export function createRun(body: CreateRunBody): Promise<CreateRunResponse> {
  return fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => parseJson<CreateRunResponse>(r));
}

export function listRuns(): Promise<RunListItem[]> {
  return fetch("/api/runs").then(async (r) => {
    const data = await parseJson<RunListItem[] | { runs: RunListItem[] }>(r);
    return Array.isArray(data) ? data : data.runs ?? [];
  });
}

export function getRun(id: string): Promise<RunSnapshot> {
  return fetch(`/api/runs/${encodeURIComponent(id)}`).then((r) =>
    parseJson<RunSnapshot>(r),
  );
}

export function stopRun(id: string): Promise<void> {
  return fetch(`/api/runs/${encodeURIComponent(id)}/stop`, {
    method: "POST",
  }).then((r) => {
    if (!r.ok) return r.text().then((t) => Promise.reject(new Error(t || r.statusText)));
  });
}

export function postFixtureCheck(body: FixtureCheckBody): Promise<unknown> {
  return fetch("/api/fixture-checks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => parseJson(r));
}

export function getPlayback(id: string): Promise<PlaybackPayload> {
  return fetch(`/api/playback/${encodeURIComponent(id)}`).then((r) =>
    parseJson<PlaybackPayload>(r),
  );
}

function apiOrigin(): string {
  return (import.meta.env.VITE_API_ORIGIN || "").replace(/\/$/, "");
}

export function evidenceUrl(id: string): string {
  const name = encodeURIComponent(id);
  if (import.meta.env.VITE_STATIC_DEMO === "1") {
    const base = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");
    return `${base}/api/evidence/${name}.jpg`;
  }
  return `${apiOrigin()}/api/evidence/${name}`;
}

// The public site is static. API calls go to the live Ghost process.
export function installApiOrigin(): void {
  const origin = apiOrigin();
  if (!origin) return;
  const orig = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const raw = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    let url: URL;
    try {
      url = new URL(raw, window.location.origin);
    } catch {
      return orig(input, init);
    }
    const at = url.pathname.indexOf("/api/");
    if (url.origin !== window.location.origin || at < 0) return orig(input, init);
    return orig(`${origin}${url.pathname.slice(at)}${url.search}`, init);
  };
}

// Published pages have no Ghost API. GET /api/* reads snapshot JSON. Other methods explain that.
export function installStaticDemoFetch(): void {
  if (import.meta.env.VITE_STATIC_DEMO !== "1") return;
  const base = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");
  const orig = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const raw = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const method = (
      init?.method || (input instanceof Request ? input.method : "GET")
    ).toUpperCase();
    const url = new URL(raw, window.location.origin);
    const marker = "/api/";
    const at = url.pathname.indexOf(marker);
    if (url.origin !== window.location.origin || at < 0) return orig(input, init);
    if (method !== "GET" && method !== "HEAD") {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            detail: "This page is a recorded demo. Republish the snapshot to update the investigation.",
          }),
          { status: 409, headers: { "content-type": "application/json" } },
        ),
      );
    }
    const rest = url.pathname.slice(at + marker.length);
    return orig(`${base}/snapshot/${rest}.json`);
  };
}

export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}
