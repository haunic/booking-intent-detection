import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useActiveSession } from "../SessionContext";
import type { IntentProfile, SearchMode } from "../types";

// Minimal starter payload for a brand-new session (backend fills defaults).
function blankSession(mode: SearchMode) {
  return {
    mode,
    channel: "Desktop",
    traditional: {
      previous_searches: [],
      current_search: {
        id: crypto.randomUUID(),
        origin: "",
        destination: "",
        departure_date: null,
        return_date: null,
        adults: 1,
        children: 0,
      },
    },
    conversational: { previous_messages: [], current_request: "" },
    predictionHistory: [],
    lastPredictionStatus: "none",
  };
}

export function NewSessionPage() {
  const navigate = useNavigate();
  const { setActive } = useActiveSession();
  const [mode, setMode] = useState<SearchMode>("traditional");
  const [profile, setProfile] = useState<IntentProfile>("random");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startBlank() {
    setBusy(true);
    setError(null);
    try {
      const created = await api.createSession(blankSession(mode));
      setActive(created);
      navigate(`/session/${created.id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function startRandom() {
    setBusy(true);
    setError(null);
    try {
      const draft = await api.generate(mode, profile);
      const created = await api.createSession(draft);
      setActive(created);
      navigate(`/session/${created.id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <h1>New Test Session</h1>
      <p className="muted">
        Predict whether a traveler browsing a flight site has a High, Medium, or Low likelihood of booking
        this session. Pick a search mode to begin.
      </p>

      {error && <div className="alert error">{error}</div>}

      <div className="card">
        <h3>Search mode</h3>
        <div className="row">
          <button
            className={mode === "traditional" ? "primary" : ""}
            onClick={() => setMode("traditional")}
          >
            Traditional Flight Search
          </button>
          <button
            className={mode === "conversational" ? "primary" : ""}
            onClick={() => setMode("conversational")}
          >
            Conversational Flight Search
          </button>
        </div>
        <p className="muted">
          {mode === "traditional"
            ? "Structured search form with previous searches and a current itinerary."
            : "Chat-style composer with a conversation history."}
        </p>
      </div>

      <div className="card">
        <h3>Start</h3>
        <div className="btn-row">
          <button className="primary" onClick={startBlank} disabled={busy}>
            Start empty session
          </button>
          <span className="spacer" />
          <label style={{ margin: 0 }}>Random intent profile</label>
          <select value={profile} style={{ width: "auto" }} onChange={(e) => setProfile(e.target.value as IntentProfile)}>
            <option value="random">Random</option>
            <option value="high">Likely High</option>
            <option value="medium">Likely Medium</option>
            <option value="low">Likely Low</option>
          </select>
          <button onClick={startRandom} disabled={busy}>
            🎲 Generate random session
          </button>
        </div>
        <p className="muted" style={{ marginBottom: 0 }}>
          Random generation produces coherent, realistic test data. The intent profile only shapes the
          generated data; it does not set the prediction result.
        </p>
      </div>
    </div>
  );
}
