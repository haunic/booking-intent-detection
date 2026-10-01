import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useActiveSession } from "../SessionContext";
import type { SessionSummary } from "../types";
import { formatDateTime } from "../util";

export function SessionHistoryPage() {
  const navigate = useNavigate();
  const { setActive } = useActiveSession();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      setSessions(await api.listSessions());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function open(id: string) {
    try {
      const s = await api.getSession(id);
      setActive(s);
      navigate(`/session/${id}`);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function duplicate(id: string) {
    try {
      const copy = await api.duplicateSession(id);
      setActive(copy);
      navigate(`/session/${copy.id}`);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function remove(id: string) {
    if (!confirm("Delete this session? This cannot be undone.")) return;
    try {
      await api.deleteSession(id);
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <div className="page">
      <h1>Session History</h1>
      {error && <div className="alert error">{error}</div>}

      <div className="card">
        {loading ? (
          <p>Loading…</p>
        ) : sessions.length === 0 ? (
          <p className="muted">No saved sessions yet. Create one from “New Test Session”.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Mode</th>
                  <th>Channel</th>
                  <th>Last status</th>
                  <th>Runs</th>
                  <th>Updated</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <a
                        href={`/session/${s.id}`}
                        onClick={(e) => {
                          e.preventDefault();
                          open(s.id);
                        }}
                      >
                        {s.name || s.id.slice(0, 8)}
                      </a>
                    </td>
                    <td>{s.mode}</td>
                    <td>{s.channel}</td>
                    <td>
                      <span className={`badge ${s.lastPredictionStatus}`}>{s.lastPredictionStatus}</span>
                    </td>
                    <td>{s.predictionCount}</td>
                    <td>{formatDateTime(s.updatedAt)}</td>
                    <td>
                      <div className="btn-row">
                        <button className="small" onClick={() => open(s.id)}>
                          Open
                        </button>
                        <button className="small" onClick={() => duplicate(s.id)}>
                          Duplicate
                        </button>
                        <button className="small danger" onClick={() => remove(s.id)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
