import { useEffect, useState } from "react";
import { api } from "../api";
import type { SearchMode, SettingsResponse, TestConnectionResult } from "../types";
import { formatDateTime } from "../util";

export function AdministrationPage() {
  return (
    <div className="page">
      <h1>Administration</h1>
      <ConnectionSettingsSection />
      <ModelConfigSection />
    </div>
  );
}

function ConnectionSettingsSection() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [keyDirty, setKeyDirty] = useState(false);
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const [test, setTest] = useState<TestConnectionResult | null>(null);
  const [testing, setTesting] = useState(false);

  async function load() {
    const s = await api.getSettings();
    setSettings(s);
    setBaseUrl(s.TYPESAFE_BASE_URL);
    setModel(s.TYPESAFE_DEFAULT_MODEL);
    setApiKey("");
    setKeyDirty(false);
  }

  useEffect(() => {
    load().catch((e) => setMsg({ kind: "error", text: e.message }));
  }, []);

  async function save() {
    setMsg(null);
    try {
      const payload: any = { TYPESAFE_BASE_URL: baseUrl, TYPESAFE_DEFAULT_MODEL: model };
      if (keyDirty && apiKey) payload.TYPESAFE_API_KEY = apiKey;
      const s = await api.updateSettings(payload);
      setSettings(s);
      setApiKey("");
      setKeyDirty(false);
      setMsg({ kind: "success", text: "Settings saved." });
    } catch (e: any) {
      setMsg({ kind: "error", text: e.message });
    }
  }

  async function reset() {
    if (!confirm("Reset connection settings to local defaults (localhost:11434, ollama, nimble)?")) return;
    try {
      const s = await api.resetSettings();
      setSettings(s);
      setBaseUrl(s.TYPESAFE_BASE_URL);
      setModel(s.TYPESAFE_DEFAULT_MODEL);
      setApiKey("");
      setKeyDirty(false);
      setMsg({ kind: "success", text: "Reset to local defaults." });
    } catch (e: any) {
      setMsg({ kind: "error", text: e.message });
    }
  }

  async function runTest() {
    setTesting(true);
    setTest(null);
    setMsg(null);
    try {
      setTest(await api.testConnection());
    } catch (e: any) {
      setMsg({ kind: "error", text: e.message });
    } finally {
      setTesting(false);
    }
  }

  return (
    <div className="card">
      <h2>Connection settings</h2>
      {msg && <div className={`alert ${msg.kind}`}>{msg.text}</div>}

      <div className="grid">
        <div className="field">
          <label>TYPESAFE_BASE_URL</label>
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="http://localhost:11434" />
        </div>
        <div className="field">
          <label>TYPESAFE_DEFAULT_MODEL</label>
          <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="nimble" />
        </div>
        <div className="field">
          <label>TYPESAFE_API_KEY {settings?.apiKeySet && !keyDirty ? "(stored — leave blank to keep)" : ""}</label>
          <div className="btn-row" style={{ gap: 6 }}>
            <input
              type={showKey ? "text" : "password"}
              value={apiKey}
              placeholder={settings?.apiKeySet ? "••••••••" : "ollama"}
              onChange={(e) => {
                setApiKey(e.target.value);
                setKeyDirty(true);
              }}
            />
            <button className="small" type="button" onClick={() => setShowKey((v) => !v)}>
              {showKey ? "Hide" : "Show"}
            </button>
          </div>
        </div>
      </div>

      <div className="btn-row">
        <button className="primary" onClick={save}>
          Save settings
        </button>
        <button onClick={runTest} disabled={testing}>
          {testing ? "Testing…" : "Test connection"}
        </button>
        <span className="spacer" />
        <button className="danger" onClick={reset}>
          Reset to local defaults
        </button>
      </div>

      {test && (
        <div className={`alert ${test.success ? "success" : "error"}`} style={{ marginTop: 14 }}>
          <strong>{test.success ? "Connection OK" : "Connection issues"}</strong>
          <ul style={{ margin: "8px 0 0" }}>
            <li>Ollama endpoint reachable: {test.endpointReachable ? "yes" : "no"}</li>
            <li>Model available: {test.modelAvailable ? "yes" : "no"}</li>
            <li>SDK /v1/models reachable: {test.sdkListModelsOk ? "yes" : "no (optional)"}</li>
            {test.availableModels.length > 0 && <li>Models: {test.availableModels.join(", ")}</li>}
            {test.messages.map((m, i) => (
              <li key={i} className="muted">
                {m}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ModelConfigSection() {
  const [mode, setMode] = useState<SearchMode>("traditional");
  const [text, setText] = useState("");
  const [modifiedAt, setModifiedAt] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [copied, setCopied] = useState(false);

  async function load(m: SearchMode) {
    setMsg(null);
    setErrors([]);
    const res = await api.getConfig(m);
    setText(JSON.stringify(res.config, null, 2));
    setModifiedAt(res.modifiedAt ?? null);
  }

  useEffect(() => {
    load(mode).catch((e) => setMsg({ kind: "error", text: e.message }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  function parse(): unknown | null {
    try {
      return JSON.parse(text);
    } catch (e: any) {
      setMsg({ kind: "error", text: `Invalid JSON: ${e.message}` });
      return null;
    }
  }

  async function validate() {
    setMsg(null);
    setErrors([]);
    const parsed = parse();
    if (parsed === null) return;
    const res = await api.validateConfig(mode, parsed);
    if (res.valid) setMsg({ kind: "success", text: "JSON and schema are valid." });
    else setErrors(res.errors);
  }

  async function save() {
    setMsg(null);
    setErrors([]);
    const parsed = parse();
    if (parsed === null) return;
    try {
      const res = await api.updateConfig(mode, parsed);
      setText(JSON.stringify(res.config, null, 2));
      setModifiedAt(res.modifiedAt ?? null);
      setMsg({ kind: "success", text: "Configuration saved." });
    } catch (e: any) {
      setMsg({ kind: "error", text: e.message });
    }
  }

  async function reset() {
    if (!confirm(`Reset the ${mode} configuration to its default?`)) return;
    try {
      const res = await api.resetConfig(mode);
      setText(JSON.stringify(res.config, null, 2));
      setModifiedAt(res.modifiedAt ?? null);
      setMsg({ kind: "success", text: "Reset to default." });
      setErrors([]);
    } catch (e: any) {
      setMsg({ kind: "error", text: e.message });
    }
  }

  async function copy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  function download() {
    const blob = new Blob([text], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${mode}-flight-search.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="card">
      <h2>Model configurations</h2>
      <div className="btn-row">
        <label style={{ margin: 0 }}>Configuration</label>
        <select value={mode} style={{ width: "auto" }} onChange={(e) => setMode(e.target.value as SearchMode)}>
          <option value="traditional">traditional-flight-search.json</option>
          <option value="conversational">conversational-flight-search.json</option>
        </select>
        <span className="spacer" />
        {modifiedAt && <span className="muted">Last modified {formatDateTime(modifiedAt)}</span>}
      </div>

      {msg && (
        <div className={`alert ${msg.kind}`} style={{ marginTop: 12 }}>
          {msg.text}
        </div>
      )}
      {errors.length > 0 && (
        <div className="alert error" style={{ marginTop: 12 }}>
          <strong>Schema validation failed:</strong>
          <ul style={{ margin: "6px 0 0" }}>
            {errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      <textarea
        style={{ minHeight: 320, fontFamily: "ui-monospace, Menlo, Consolas, monospace", marginTop: 12 }}
        value={text}
        spellCheck={false}
        onChange={(e) => setText(e.target.value)}
      />

      <div className="btn-row" style={{ marginTop: 12 }}>
        <button onClick={validate}>Validate</button>
        <button className="primary" onClick={save}>
          Save
        </button>
        <button onClick={copy}>{copied ? "Copied!" : "Copy"}</button>
        <button onClick={download}>Download</button>
        <span className="spacer" />
        <button className="danger" onClick={reset}>
          Reset to default
        </button>
      </div>
    </div>
  );
}
