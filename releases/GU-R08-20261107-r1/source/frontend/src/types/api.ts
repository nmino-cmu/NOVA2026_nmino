export type RunStatus = "queued" | "running" | "completed" | "failed" | string;

export type NodeStatus = "witnessed" | "current" | "verified" | "failed";

export interface BestVerified {
  routeId: string;
  verificationId: string;
  status: string;
  interactions: number;
  actionSequenceHash: string;
  resetInstanceId: string;
  initialStateHash: string;
}

export interface GraphNode {
  id: string;
  label: string;
  x: number;
  y: number;
  status: NodeStatus;
  seq: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface WitnessEntry {
  index: number;
  kind: string;
  name: string;
  role: string;
  interactions: number;
  outcome: string;
  screenshotId: string | null;
}

export interface CheckEntry {
  id: string;
  name: string;
  status: string;
  detail: string;
}

export interface ActivityEntry {
  seq: number;
  type: string;
  summary: string;
}

export interface EvidenceEntry {
  id: string;
  kind: string;
  mediaType: string;
  label: string;
  capturedAt: string;
}

export interface CurrentAction {
  name: string;
  reason?: string;
}

export interface LatestVerification {
  verificationId: string;
  status: string;
  interactions: number | null;
  detail: string;
}

export interface Projection {
  phase: string;
  currentAction: CurrentAction | null;
  bestVerified: BestVerified | null;
  latestVerification?: LatestVerification | null;
  nodes: GraphNode[];
  edges: GraphEdge[];
  witness: WitnessEntry[];
  checks: CheckEntry[];
  activity: ActivityEntry[];
  evidence: EvidenceEntry[];
  limitations: string[];
  restoration: string;
}

export interface TaskInfo {
  id: string;
  version: number;
  objective: string;
  task: string;
  url: string;
  acceptableInteractions: number;
}

export interface Budget {
  wallMs: number;
  requests: number;
  totalTokens: number;
  browserActions: number;
  resets: number;
  routeActions: number;
  spendingUSD: number | null;
}

export interface Usage {
  requests: number;
  inputTokens: number | null;
  outputTokens: number | null;
  totalTokens: number | null;
  tokenAccounting: string;
  cachedInputTokens: number | null;
  reasoningTokens: number | null;
  browserActions: number;
  resets: number;
  elapsedMs: number;
  spendingUSD: number | null;
  spendingAccounting: string;
}

export interface RunSnapshot {
  id: string;
  status: RunStatus;
  stopReason: string | null;
  throughSeq: number;
  readOnly: boolean;
  discovery: boolean;
  label: string;
  policyId: string;
  buildId: string;
  error: string | null;
  task: TaskInfo;
  budget: Budget;
  usage: Usage;
  projection: Projection;
  versions: Record<string, string | number>;
}

export interface RunListItem {
  id: string;
  status?: RunStatus;
  label?: string;
  createdAt?: string;
}

export interface TaskDraftOrbit {
  mode: "orbit";
}

export interface TaskDraftSupplied {
  mode: "supplied";
  url: string;
  objective: string;
  targetName: string;
  restoration: "fresh_context" | "unknown";
}

export type TaskDraftBody = TaskDraftOrbit | TaskDraftSupplied;

export interface TaskDraftResponse {
  checks?: CheckEntry[];
  objective?: string;
  task?: string;
  url?: string;
  acceptableInteractions?: number;
  budget?: Partial<Budget>;
  [key: string]: unknown;
}

export interface CreateTaskResponse {
  id: string;
  version: number;
}

export interface CreateRunBody {
  taskId: string;
  taskVersion: number;
  policyId: string;
  idempotencyKey: string;
}

export interface CreateRunResponse {
  id: string;
}

export interface FixtureCheckBody {
  kind: "ordinary" | "shortcut" | "express";
  idempotencyKey: string;
}

export interface RunEvent {
  seq: number;
  type?: string;
  [key: string]: unknown;
}

export interface PlaybackPayload extends RunSnapshot {
  events: RunEvent[];
  readOnly: true;
}
