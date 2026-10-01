import type { FlightSearch, Session } from "../types";
import { AIRPORTS, IATA_CODES, daysBetween, parseDate } from "../util";

interface Props {
  session: Session;
  onChange: (updater: (s: Session) => Session) => void;
}

function newSearch(): FlightSearch {
  return {
    id: crypto.randomUUID(),
    origin: "",
    destination: "",
    departure_date: null,
    return_date: null,
    adults: 1,
    children: 0,
  };
}

// Validation for a single search; returns a map of field -> message.
function validateSearch(s: FlightSearch, browsingDate?: string | null): Record<string, string> {
  const errs: Record<string, string> = {};
  if (s.origin && s.destination && s.origin === s.destination) {
    errs.destination = "Origin and destination must differ.";
  }
  if (s.origin && !IATA_CODES.includes(s.origin)) {
    errs.origin = "Use a known 3-letter IATA code.";
  }
  if (s.destination && !IATA_CODES.includes(s.destination)) {
    errs.destination = errs.destination || "Use a known 3-letter IATA code.";
  }
  const dep = parseDate(s.departure_date);
  const ret = parseDate(s.return_date);
  const browse = parseDate(browsingDate);
  if (dep && browse && dep < browse) {
    errs.departure_date = "Departure must not be before the browsing date.";
  }
  if (dep && ret && ret < dep) {
    errs.return_date = "Return must not be before departure.";
  }
  if (s.adults < 1 && s.children > 0) {
    errs.adults = "At least one adult is required when children are present.";
  }
  return errs;
}

function SearchFields({
  search,
  browsingDate,
  onUpdate,
}: {
  search: FlightSearch;
  browsingDate?: string | null;
  onUpdate: (patch: Partial<FlightSearch>) => void;
}) {
  const errs = validateSearch(search, browsingDate);
  return (
    <div className="grid">
      <div className="field">
        <label>Origin (IATA)</label>
        <input
          list="iata-list"
          value={search.origin}
          maxLength={3}
          aria-invalid={!!errs.origin}
          onChange={(e) => onUpdate({ origin: e.target.value.toUpperCase().slice(0, 3) })}
        />
        {errs.origin && <div className="field-error">{errs.origin}</div>}
      </div>
      <div className="field">
        <label>Destination (IATA)</label>
        <input
          list="iata-list"
          value={search.destination}
          maxLength={3}
          aria-invalid={!!errs.destination}
          onChange={(e) => onUpdate({ destination: e.target.value.toUpperCase().slice(0, 3) })}
        />
        {errs.destination && <div className="field-error">{errs.destination}</div>}
      </div>
      <div className="field">
        <label>Departure date</label>
        <input
          type="date"
          value={search.departure_date ?? ""}
          aria-invalid={!!errs.departure_date}
          onChange={(e) => onUpdate({ departure_date: e.target.value || null })}
        />
        {errs.departure_date && <div className="field-error">{errs.departure_date}</div>}
      </div>
      <div className="field">
        <label>Return date (optional)</label>
        <input
          type="date"
          value={search.return_date ?? ""}
          aria-invalid={!!errs.return_date}
          onChange={(e) => onUpdate({ return_date: e.target.value || null })}
        />
        {errs.return_date && <div className="field-error">{errs.return_date}</div>}
      </div>
      <div className="field">
        <label>Adults</label>
        <input
          type="number"
          min={0}
          max={9}
          value={search.adults}
          aria-invalid={!!errs.adults}
          onChange={(e) => onUpdate({ adults: Math.max(0, Math.min(9, Number(e.target.value) || 0)) })}
        />
        {errs.adults && <div className="field-error">{errs.adults}</div>}
      </div>
      <div className="field">
        <label>Children</label>
        <input
          type="number"
          min={0}
          max={9}
          value={search.children}
          onChange={(e) => onUpdate({ children: Math.max(0, Math.min(9, Number(e.target.value) || 0)) })}
        />
      </div>
    </div>
  );
}

export function TraditionalEditor({ session, onChange }: Props) {
  const data = session.traditional;

  const updatePrev = (idx: number, patch: Partial<FlightSearch>) =>
    onChange((s) => {
      const prev = [...s.traditional.previous_searches];
      prev[idx] = { ...prev[idx], ...patch };
      return { ...s, traditional: { ...s.traditional, previous_searches: prev } };
    });

  const addPrev = () =>
    onChange((s) =>
      s.traditional.previous_searches.length >= 10
        ? s
        : {
            ...s,
            traditional: {
              ...s.traditional,
              previous_searches: [...s.traditional.previous_searches, newSearch()],
            },
          },
    );

  const removePrev = (idx: number) =>
    onChange((s) => ({
      ...s,
      traditional: {
        ...s.traditional,
        previous_searches: s.traditional.previous_searches.filter((_, i) => i !== idx),
      },
    }));

  const movePrev = (idx: number, dir: -1 | 1) =>
    onChange((s) => {
      const arr = [...s.traditional.previous_searches];
      const j = idx + dir;
      if (j < 0 || j >= arr.length) return s;
      [arr[idx], arr[j]] = [arr[j], arr[idx]];
      return { ...s, traditional: { ...s.traditional, previous_searches: arr } };
    });

  const copyToCurrent = (idx: number) =>
    onChange((s) => {
      const src = s.traditional.previous_searches[idx];
      return {
        ...s,
        traditional: {
          ...s.traditional,
          current_search: { ...src, id: s.traditional.current_search.id },
        },
      };
    });

  const updateCurrent = (patch: Partial<FlightSearch>) =>
    onChange((s) => ({
      ...s,
      traditional: { ...s.traditional, current_search: { ...s.traditional.current_search, ...patch } },
    }));

  const cur = data.current_search;
  const derived = deriveCurrent(cur, data.previous_searches, session.browsingDate);

  return (
    <>
      <datalist id="iata-list">
        {AIRPORTS.map((a) => (
          <option key={a.code} value={a.code}>
            {a.city}
          </option>
        ))}
      </datalist>

      <div className="card">
        <h3>Previous searches ({data.previous_searches.length}/10)</h3>
        {data.previous_searches.length === 0 && <p className="muted">No previous searches.</p>}
        {data.previous_searches.map((s, idx) => (
          <div key={s.id} className="card" style={{ background: "var(--surface-2)" }}>
            <div className="btn-row" style={{ marginBottom: 8 }}>
              <strong>#{idx + 1}</strong>
              <span className="spacer" />
              <button className="small" onClick={() => movePrev(idx, -1)} disabled={idx === 0}>
                ↑
              </button>
              <button
                className="small"
                onClick={() => movePrev(idx, 1)}
                disabled={idx === data.previous_searches.length - 1}
              >
                ↓
              </button>
              <button className="small" onClick={() => copyToCurrent(idx)}>
                Copy to current
              </button>
              <button className="small danger" onClick={() => removePrev(idx)}>
                Remove
              </button>
            </div>
            <SearchFields search={s} browsingDate={session.browsingDate} onUpdate={(p) => updatePrev(idx, p)} />
          </div>
        ))}
        <button className="small" onClick={addPrev} disabled={data.previous_searches.length >= 10}>
          + Add previous search
        </button>
      </div>

      <div className="card">
        <h3>Current search</h3>
        <SearchFields search={cur} browsingDate={session.browsingDate} onUpdate={updateCurrent} />
        <div className="meta-grid" style={{ marginTop: 10 }}>
          <div>
            <strong>Trip type</strong>
            <br />
            {derived.tripType}
          </div>
          {derived.lengthOfStay != null && (
            <div>
              <strong>Length of stay</strong>
              <br />
              {derived.lengthOfStay} day(s)
            </div>
          )}
          {derived.daysToDeparture != null && (
            <div>
              <strong>Days to departure</strong>
              <br />
              {derived.daysToDeparture}
            </div>
          )}
          {derived.diff && (
            <div>
              <strong>Vs. previous</strong>
              <br />
              {derived.diff}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function deriveCurrent(cur: FlightSearch, prev: FlightSearch[], browsingDate?: string | null) {
  const dep = parseDate(cur.departure_date);
  const ret = parseDate(cur.return_date);
  const browse = parseDate(browsingDate);
  const tripType = ret ? "Round-trip" : dep ? "One-way" : "—";
  const lengthOfStay = dep && ret ? daysBetween(dep, ret) : null;
  const daysToDeparture = dep && browse ? daysBetween(browse, dep) : null;

  let diff: string | null = null;
  if (prev.length > 0) {
    const last = prev[prev.length - 1];
    const parts: string[] = [];
    if (last.origin !== cur.origin || last.destination !== cur.destination) parts.push("route changed");
    else parts.push("same route");
    const pdep = parseDate(last.departure_date);
    if (dep && pdep) {
      const shift = daysBetween(pdep, dep);
      parts.push(shift === 0 ? "same dates" : `${Math.abs(shift)}d date shift`);
    }
    diff = parts.join(", ");
  }
  return { tripType, lengthOfStay, daysToDeparture, diff };
}
