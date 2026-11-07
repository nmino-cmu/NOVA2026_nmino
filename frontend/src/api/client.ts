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

export function evidenceUrl(id: string): string {
  return `/api/evidence/${encodeURIComponent(id)}`;
}

export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}
