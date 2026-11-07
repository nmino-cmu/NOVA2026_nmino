import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getPlayback } from "../api/client";
import { SummaryCards } from "../components/SummaryCards";
import type { PlaybackPayload, RunEvent } from "../types/api";

export function PlaybackPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<PlaybackPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hoverSeq, setHoverSeq] = useState<number | null>(null);

  useEffect(() => {
    if (!id) return;
    void getPlayback(id)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load playback"));
  }, [id]);

  if (!id) {
    return <div className="error-banner">Missing playback id.</div>;
  }

  if (error) {
    return (
      <div>
        <h1 style={{ marginTop: 0 }}>Playback</h1>
        <div className="error-banner">{error}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <h1 style={{ marginTop: 0 }}>Playback</h1>
        <p style={{ color: "var(--secondary)" }}>Loading recorded investigation…</p>
      </div>
    );
  }

  const events = data.events ?? [];

  function emphasize(ev: RunEvent): boolean {
    if (hoverSeq === null) return true;
    const seq = ev.seq ?? 0;
    return seq <= hoverSeq;
  }

  return (
    <div>
      <div className="playback-ribbon" role="note">
        Recorded investigation · run <span className="tabular">{data.id}</span> · build{" "}
        <span className="tabular">{data.buildId}</span>
      </div>
      <h1 style={{ marginTop: 0 }}>Playback</h1>
      {data.error && <div className="error-banner">{data.error}</div>}
      <SummaryCards snapshot={data} />

      <section className="card playback-timeline" aria-label="Event timeline">
        <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Events</h2>
        <p style={{ color: "var(--secondary)", fontSize: "0.875rem" }}>
          Move the cursor over an event to emphasize earlier steps. This view is read-only.
        </p>
        {events.length === 0 ? (
          <p style={{ color: "var(--secondary)" }}>No events recorded.</p>
        ) : (
          events.map((ev, i) => (
            <div
              key={ev.seq ?? i}
              className={`playback-item ${emphasize(ev) ? "emphasized" : ""}`}
              onMouseEnter={() => setHoverSeq(typeof ev.seq === "number" ? ev.seq : null)}
              onMouseLeave={() => setHoverSeq(null)}
            >
              <span className="tabular" style={{ color: "var(--secondary)", marginRight: 8 }}>
                #{ev.seq ?? "?"}
              </span>
              {String(ev.type ?? "event")}
            </div>
          ))
        )}
      </section>

      <ul className="activity-list card" style={{ listStyle: "none" }}>
        {data.projection.activity.map((a) => (
          <li
            key={a.seq}
            className={hoverSeq !== null && a.seq <= hoverSeq ? "emphasized" : ""}
            style={{ opacity: hoverSeq !== null && a.seq > hoverSeq ? 0.5 : 1 }}
            onMouseEnter={() => setHoverSeq(a.seq)}
            onMouseLeave={() => setHoverSeq(null)}
          >
            <span className="tabular">#{a.seq}</span> {a.summary}
          </li>
        ))}
      </ul>
    </div>
  );
}
