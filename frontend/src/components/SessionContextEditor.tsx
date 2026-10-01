import type { Channel, Session } from "../types";
import { TIME_ZONES } from "../util";

const CHANNELS: Channel[] = ["Mobile", "Desktop", "Voice AI Assistant"];

export function SessionContextEditor({
  session,
  onChange,
}: {
  session: Session;
  onChange: (updater: (s: Session) => Session) => void;
}) {
  return (
    <div className="card">
      <h3>Session context</h3>
      <div className="grid">
        <div className="field">
          <label>Session name (optional)</label>
          <input
            value={session.name ?? ""}
            placeholder="e.g. Convergent Paris trip"
            onChange={(e) => onChange((s) => ({ ...s, name: e.target.value }))}
          />
        </div>
        <div className="field">
          <label>Device / channel</label>
          <select
            value={session.channel}
            onChange={(e) => onChange((s) => ({ ...s, channel: e.target.value as Channel }))}
          >
            {CHANNELS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Browsing date</label>
          <input
            type="date"
            value={session.browsingDate ?? ""}
            onChange={(e) => onChange((s) => ({ ...s, browsingDate: e.target.value || null }))}
          />
        </div>
        <div className="field">
          <label>Browsing local time</label>
          <input
            type="time"
            value={session.browsingLocalTime ?? ""}
            onChange={(e) => onChange((s) => ({ ...s, browsingLocalTime: e.target.value || null }))}
          />
        </div>
        <div className="field">
          <label>Time zone / UTC offset</label>
          <input
            list="tz-list"
            value={session.timeZone ?? ""}
            onChange={(e) => onChange((s) => ({ ...s, timeZone: e.target.value || null }))}
          />
          <datalist id="tz-list">
            {TIME_ZONES.map((t) => (
              <option key={t} value={t} />
            ))}
          </datalist>
        </div>
      </div>
    </div>
  );
}
