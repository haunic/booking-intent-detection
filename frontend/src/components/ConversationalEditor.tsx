import type { ChatMessage, Session } from "../types";

interface Props {
  session: Session;
  onChange: (updater: (s: Session) => Session) => void;
}

export function ConversationalEditor({ session, onChange }: Props) {
  const data = session.conversational;

  const addMessage = () =>
    onChange((s) =>
      s.conversational.previous_messages.length >= 10
        ? s
        : {
            ...s,
            conversational: {
              ...s.conversational,
              previous_messages: [
                ...s.conversational.previous_messages,
                { id: crypto.randomUUID(), text: "" },
              ],
            },
          },
    );

  const updateMessage = (idx: number, text: string) =>
    onChange((s) => {
      const msgs = [...s.conversational.previous_messages];
      msgs[idx] = { ...msgs[idx], text };
      return { ...s, conversational: { ...s.conversational, previous_messages: msgs } };
    });

  const removeMessage = (idx: number) =>
    onChange((s) => ({
      ...s,
      conversational: {
        ...s.conversational,
        previous_messages: s.conversational.previous_messages.filter((_, i) => i !== idx),
      },
    }));

  const moveMessage = (idx: number, dir: -1 | 1) =>
    onChange((s) => {
      const arr = [...s.conversational.previous_messages];
      const j = idx + dir;
      if (j < 0 || j >= arr.length) return s;
      [arr[idx], arr[j]] = [arr[j], arr[idx]];
      return { ...s, conversational: { ...s.conversational, previous_messages: arr } };
    });

  const setCurrent = (text: string) =>
    onChange((s) => ({
      ...s,
      conversational: { ...s.conversational, current_request: text },
    }));

  return (
    <>
      <div className="card">
        <h3>Previous conversation ({data.previous_messages.length}/10)</h3>
        {data.previous_messages.length === 0 && (
          <p className="muted">No prior messages. Add some, or just use the current request below.</p>
        )}
        <div className="chat-log">
          {data.previous_messages.map((m: ChatMessage, idx) => (
            <div key={m.id} className="chat-bubble">
              <div className="btn-row" style={{ marginBottom: 6 }}>
                <span className="idx">Traveler message #{idx + 1}</span>
                <span className="spacer" />
                <button className="small" onClick={() => moveMessage(idx, -1)} disabled={idx === 0}>
                  ↑
                </button>
                <button
                  className="small"
                  onClick={() => moveMessage(idx, 1)}
                  disabled={idx === data.previous_messages.length - 1}
                >
                  ↓
                </button>
                <button className="small danger" onClick={() => removeMessage(idx)}>
                  Remove
                </button>
              </div>
              <textarea
                value={m.text}
                placeholder="e.g. Looking at flights from Nice to Rome next month..."
                onChange={(e) => updateMessage(idx, e.target.value)}
              />
            </div>
          ))}
        </div>
        <button
          className="small"
          onClick={addMessage}
          disabled={data.previous_messages.length >= 10}
          style={{ marginTop: 10 }}
        >
          + Add previous message
        </button>
      </div>

      <div className="card">
        <h3>Current request</h3>
        <label htmlFor="composer">Type the traveler's current message</label>
        <textarea
          id="composer"
          style={{ minHeight: 110 }}
          value={data.current_request}
          placeholder="Find me a return flight from Nice to Bangkok for two adults, leaving around 15 December and coming back one week later."
          onChange={(e) => setCurrent(e.target.value)}
        />
      </div>
    </>
  );
}
