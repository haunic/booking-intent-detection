import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useActiveSession } from "../SessionContext";
import type { IntentProfile, Session } from "../types";
import { SessionContextEditor } from "../components/SessionContextEditor";
import { TraditionalEditor } from "../components/TraditionalEditor";
import { ConversationalEditor } from "../components/ConversationalEditor";
import { PredictionResult } from "../components/PredictionResult";
import { formatDateTime } from "../util";

export function SessionEditorPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { active, setActive } = useActiveSession();

  const [session, setSession] = useState<Session | null>(active && active.id === id ? active : null);
  const [loading, setLoading] = useState(!session);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [profile, setProfile] = useState<IntentProfile>("random");
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (session && session.id === id) return;
    if (!id) return;
    setLoading(true);
    api
      .getSession(id)
      .then((s) => {
        setSession(s);
        setActive(s);
        setDirty(false);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  function update(updater: (s: Session) => Session) {
    setSession((prev) => (prev ? updater(prev) : prev));
    setDirty(true);
    setInfo(null);
  }

  async function save() {
    if (!session) return;
    setError(null);
    try {
      const saved = await api.updateSession(session.id, session);
      setSession(saved);
      setActive(saved);
      setDirty(false);
      setInfo("Session saved.");
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function regenerate() {
    if (!session) return;
    setError(null);
    try {
      const gen = await api.generate(session.mode, profile);
      // Keep the existing id/history; replace inputs + context from the generated draft.
      update((s) => ({
        ...s,
        name: gen.name,
        channel: gen.channel,
        browsingDate: gen.browsingDate,
        browsingLocalTime: gen.browsingLocalTime,
        timeZone: gen.timeZone,
        traditional: gen.traditional,
        conversational: gen.conversational,
      }));
      setInfo("Random data generated. Review and save or predict.");
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function predict() {
    if (!session) return;
    setError(null);
    setInfo(null);
    setPredicting(true);
    try {
      // Persist current edits first so the prediction uses the latest input.
      if (dirty) {
        const saved = await api.updateSession(session.id, session);
        setSession(saved);
      }
      const updated = await api.predict(session.id);
      setSession(updated);
      setActive(updated);
      setDirty(false);
      const latest = updated.predictionHistory[0];
      if (latest?.status === "error") {
        setError((latest.error as any)?.detail || "Prediction failed.");
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setPredicting(false);
    }
  }

  async function duplicate() {
    if (!session) return;
    try {
      const copy = await api.duplicateSession(session.id);
      setActive(copy);
      navigate(`/session/${copy.id}`);
      setInfo("Duplicated into a new session.");
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function remove() {
    if (!session) return;
    if (!confirm("Delete this session? This cannot be undone.")) return;
    try {
      await api.deleteSession(session.id);
      if (active?.id === session.id) setActive(null);
      navigate("/history");
    } catch (e: any) {
      setError(e.message);
    }
  }

  if (loading) return <div className="page">Loading…</div>;
  if (!session) return <div className="page">{error || "Session not found."}</div>;

  const latest = session.predictionHistory[0];

  return (
    <div className="page">
      <div className="btn-row" style={{ marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>
          {session.mode === "conversational" ? "Conversational Flight Search" : "Traditional Flight Search"}
        </h1>
        <span className="spacer" />
        <span className="muted">Updated {formatDateTime(session.updatedAt)}</span>
      </div>

      {error && <div className="alert error">{error}</div>}
      {info && <div className="alert success">{info}</div>}

      <div className="card">
        <div className="btn-row">
          <label style={{ margin: 0 }}>Intent profile for random data</label>
          <select
            value={profile}
            style={{ width: "auto" }}
            onChange={(e) => setProfile(e.target.value as IntentProfile)}
          >
            <option value="random">Random</option>
            <option value="high">Likely High</option>
            <option value="medium">Likely Medium</option>
            <option value="low">Likely Low</option>
          </select>
          <button className="small" onClick={regenerate}>
            🎲 Generate random session
          </button>
          <span className="spacer" />
          <button className="small" onClick={duplicate}>
            Duplicate
          </button>
          <button className="small danger" onClick={remove}>
            Delete
          </button>
        </div>
        <p className="muted" style={{ marginBottom: 0 }}>
          The intent profile only shapes generated test data. It never sets the prediction result.
        </p>
      </div>

      <SessionContextEditor session={session} onChange={update} />

      {session.mode === "conversational" ? (
        <ConversationalEditor session={session} onChange={update} />
      ) : (
        <TraditionalEditor session={session} onChange={update} />
      )}

      <div className="card">
        <div className="btn-row">
          <button onClick={save}>{dirty ? "Save session" : "Saved"}</button>
          <span className="spacer" />
          <button className="primary predict-btn" style={{ width: "auto" }} onClick={predict} disabled={predicting}>
            {predicting ? "Predicting…" : "Predict intent to book"}
          </button>
        </div>
        {predicting && (
          <p className="muted">
            Calling the TypeSafe SDK against your local model. The first call can take a while if the model
            is loading.
          </p>
        )}
      </div>

      {latest && (
        <div className="card">
          <h2>Latest prediction</h2>
          <PredictionResult run={latest} />
        </div>
      )}

      {session.predictionHistory.length > 1 && (
        <div className="card">
          <h2>Previous prediction runs ({session.predictionHistory.length - 1})</h2>
          {session.predictionHistory.slice(1).map((run) => (
            <details key={run.id}>
              <summary>
                {formatDateTime(run.createdAt)} —{" "}
                <span className={`badge ${run.normalized?.intent ?? run.status}`}>
                  {run.normalized?.intent ?? run.status}
                </span>
              </summary>
              <div style={{ padding: 12 }}>
                <PredictionResult run={run} />
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}
