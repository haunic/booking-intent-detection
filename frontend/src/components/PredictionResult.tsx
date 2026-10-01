import type { PredictionRun } from "../types";
import { formatDateTime } from "../util";
import { JsonViewer } from "./JsonViewer";

// Renders a single prediction run: human-readable result + raw/debug sections.
// All text is rendered as React children (escaped), never dangerouslySetInnerHTML.
export function PredictionResult({ run }: { run: PredictionRun }) {
  if (run.status === "error") {
    const err = run.error || {};
    return (
      <div className="result-banner Low" role="alert">
        <h3 style={{ marginTop: 0 }}>Prediction failed</h3>
        <p>{String((err as any).detail || "The prediction could not be completed.")}</p>
        {(err as any).kind && <p className="muted">Error type: {String((err as any).kind)}</p>}
        <RawSections run={run} />
      </div>
    );
  }

  const n = run.normalized;
  if (!n || !n.intent) {
    return (
      <div className="result-banner">
        <p>No normalized result available.</p>
        <RawSections run={run} />
      </div>
    );
  }

  const pct =
    n.probabilityAvailable && n.probability != null ? Math.round(n.probability * 100) : null;

  return (
    <div>
      <div className={`result-banner ${n.intent}`}>
        <p className="muted" style={{ margin: 0 }}>
          Intent to book
        </p>
        <p className={`intent-label ${n.intent}`}>{n.intent}</p>

        {pct != null ? (
          <>
            <div className="probability-bar" aria-hidden="true">
              <span style={{ width: `${pct}%` }} />
            </div>
            <p style={{ margin: "4px 0" }}>Confidence: {pct}%</p>
          </>
        ) : (
          <p style={{ margin: "8px 0" }}>Probability not provided by the model.</p>
        )}

        <p>{n.explanation}</p>

        <div className="meta-grid">
          <div>
            <strong>Model</strong>
            <br />
            {n.model}
          </div>
          <div>
            <strong>Predicted at</strong>
            <br />
            {formatDateTime(n.predictedAt)}
          </div>
          <div>
            <strong>Response time</strong>
            <br />
            {n.durationMs} ms
          </div>
        </div>
      </div>

      <RawSections run={run} />
    </div>
  );
}

function RawSections({ run }: { run: PredictionRun }) {
  return (
    <div>
      <JsonViewer title="Raw TypeSafe SDK response" value={run.rawResponse} defaultOpen />
      <details>
        <summary>Generated state (sent to the model)</summary>
        <pre className="json">{run.state}</pre>
      </details>
      <JsonViewer title="Final TypeSafe request" value={run.sdkRequest} />
      <JsonViewer
        title="Normalized application result"
        value={run.normalized ?? { note: "no normalized result" }}
      />
    </div>
  );
}
