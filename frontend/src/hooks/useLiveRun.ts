import { useCallback, useEffect, useRef, useState } from "react";
import { getRun } from "../api/client";
import type { RunSnapshot } from "../types/api";

function isLive(status: string): boolean {
  return status === "queued" || status === "running";
}

export function useLiveRun(runId: string | undefined) {
  const [snapshot, setSnapshot] = useState<RunSnapshot | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const lastSeqRef = useRef(0);
  const throughSeqRef = useRef(0);

  const reload = useCallback(async () => {
    if (!runId) return;
    try {
      const data = await getRun(runId);
      setSnapshot(data);
      setFetchError(null);
      throughSeqRef.current = data.throughSeq;
      lastSeqRef.current = data.throughSeq;
    } catch (e) {
      setFetchError(e instanceof Error ? e.message : "Failed to load run");
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    setLoading(true);
    void reload();
  }, [reload]);

  useEffect(() => {
    if (!runId || !snapshot || !isLive(snapshot.status)) return;

    const interval = window.setInterval(() => {
      void reload();
    }, 1000);

    return () => window.clearInterval(interval);
  }, [runId, snapshot?.status, reload]);

  useEffect(() => {
    if (!runId || !snapshot || !isLive(snapshot.status)) return;

    const after = throughSeqRef.current;
    const es = new EventSource(
      `/api/runs/${encodeURIComponent(runId)}/events?after=${after}`,
    );

    es.onmessage = (ev) => {
      try {
        const parsed = JSON.parse(ev.data) as { seq?: number };
        const seq = parsed.seq;
        if (typeof seq !== "number") return;
        if (lastSeqRef.current > 0 && seq > lastSeqRef.current + 1) {
          void reload();
        }
        lastSeqRef.current = seq;
        throughSeqRef.current = Math.max(throughSeqRef.current, seq);
      } catch {
        /* ignore malformed */
      }
    };

    es.onerror = () => {
      es.close();
    };

    return () => es.close();
  }, [runId, snapshot?.status, reload]);

  return { snapshot, loading, fetchError, reload };
}
