# Booking Intent Detection

A locally hosted, responsive web application that demonstrates the **TypeSafe SDK**
in an *intent to book* prediction use case for flight shopping. It predicts whether a
traveler browsing a travel site has a **High**, **Medium**, or **Low** likelihood of
completing a flight booking during the current session.

This is a demonstration application, not a production booking engine. It runs entirely
on your laptop, talks to a local Ollama server, uses the locally installed `nimble`
decision model, and stores everything as JSON files on disk — no database.

---

## What it does

- **New Test Session** — start a Traditional (structured form) or Conversational (chat)
  session, enter data manually or generate coherent random test data, then run a prediction.
- **Session History** — reopen, modify, re-predict, duplicate, or delete saved sessions.
- **Administration** — edit and test the TypeSafe/Ollama connection settings, and edit the
  per-mode model configuration JSON with syntax + schema validation.

Each prediction shows a human-readable result (intent, confidence, explanation, model,
duration) plus collapsible raw views: the raw SDK response, the generated `state`, the
final SDK request, and the normalized application result.

---

## Architecture decision (why Python backend)

The prompt's *preferred* stack was Node + TypeScript, offered as optional ("if no stack
was specified, select one and document the decision"). The one hard constraint is **"Use
the TypeSafe SDK."** After inspecting the SDK, the official, locally installable SDK that
exposes the `system_one` decision call is the **Python** package `typesafe-sdk`
(verified: version 0.7.2, imports as `typesafe_sdk`). There is no equivalent published
Node package that implements the same call surface, and the requirement that the SDK be
called only from the backend makes a Python backend the correct choice.

Decision:

| Layer | Choice | Reason |
|-------|--------|--------|
| Backend | **Python + FastAPI** | The TypeSafe SDK is a Python package; the SDK must only be called from the backend. |
| Frontend | **React + TypeScript + Vite** | Matches the requested frontend; responsive. |
| Runtime validation | **Zod** (frontend) + **Pydantic** (backend) | Validates data at both boundaries. |
| Storage | **Local JSON files** under `./data/` | No database, atomic writes, survives restart. |
| SDK isolation | **`backend/app/typesafe_adapter.py`** | The only module that imports `typesafe_sdk`, so it can be corrected in one place if the installed SDK differs from the docs. |

### Confirmed SDK facts (from docs + the installed package, verified live)

1. **Package / import** — `pip install typesafe-sdk`; `from typesafe_sdk import TypeSafeClient, Choice, ...` (installed 0.7.2).
2. **Sync & async** — both `TypeSafeClient` (sync) and `AsyncTypeSafeClient` exist. This app uses the **synchronous** client.
3. **Configuration** — constructor kwargs `api_key`, `base_url`, `model`, `timeout`, with env fallbacks `TYPESAFE_API_KEY` / `TYPESAFE_BASE_URL` / `TYPESAFE_DEFAULT_MODEL`. `base_url` is the root before `/v1/systemone` and `/v1/models`.
4. **Request / response** — `client.system_one(state=<str|json>, questions={name: {"type": "choice", "instructions": ..., "criteria": {...}}})` returns a `SystemOneResponse` with `.model`, `.usage`, and `.answers`. A choice answer has `.choice`, `.probabilities` (per-label map), and `.confidence`.
5. **Probability / confidence** — **yes**, choice answers provide a `confidence` score (0–1) and per-label `probabilities`. The app uses `confidence` as the probability, falling back to the winning label's probability, and never fabricates a value.
6. **Errors / malformed output** — the SDK raises `TypeSafeError`, `TypeSafeAPIError`, `TypeSafeAPIConnectionError`, `TypeSafeAPITimeoutError`, `TypeSafeAPIResponseValidationError`, etc. The adapter catches all of these and maps them to a normalized `AdapterError` that is stored on the prediction run and shown safely in the UI.

> Note: a plain Ollama server implements `/v1/systemone` (used for predictions) but may
> not implement the SDK's `/v1/models` listing. The Administration "Test connection"
> feature therefore checks model availability through Ollama's native `/api/tags`
> endpoint and reports the SDK `/v1/models` check separately as optional.

---

## Prerequisites

1. **Ollama** installed and running locally. Default endpoint: `http://localhost:11434`.
   - Download: https://ollama.com
2. The **`nimble`** decision model pulled locally:
   ```
   ollama pull nimble
   ```
3. **Python 3.11+** (tested on 3.14).
4. **Node.js 18+** and npm (tested on Node 22).

Verify Ollama and the model:
```
curl http://localhost:11434/api/tags
```
`nimble` (or `nimble:latest`) should appear in the list.

---

## Setup

Clone/open the project, then set up the two parts.

### 1. Backend (Python / FastAPI)

From the project root:

```powershell
# Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate         # macOS / Linux

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Frontend (React / Vite)

```powershell
cd frontend
npm install
cd ..
```

---

## Running the app (two terminals)

**Terminal 1 — backend API** (from the project root):

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The backend seeds `./data/config/` on first run (connection settings + both model
configs) and creates `./data/sessions/`.

**Terminal 2 — frontend dev server** (from `frontend/`):

```powershell
npm run dev
```

Then open **http://localhost:5173**.

The Vite dev server proxies all `/api/*` requests to the backend on port 8000, so the
browser only talks to a single origin and never touches files directly.

> On the very first prediction the 9B model may take a while to load into memory. The
> backend uses a generous 180-second timeout for prediction calls.

### Production-style build (optional)

```powershell
cd frontend
npm run build        # outputs frontend/dist/
npm run preview      # serves the built app (configure a proxy or run the backend separately)
```

---

## Data layout

All mutable data lives under `./data/` (no database):

```
data/
  config/
    settings.json                      # TYPESAFE_BASE_URL / API_KEY / DEFAULT_MODEL
    traditional-flight-search.json     # model config for Mode A
    conversational-flight-search.json  # model config for Mode B
  sessions/
    <session-id>.json                  # one file per saved session
```

- Writes are **atomic** (temp file + `os.replace`) and JSON is validated before saving.
- Config and settings files are **seeded on first run** if missing.
- The app fully recovers all sessions and prediction history after a restart.

### Configuration via environment variables (optional)

The connection settings are normally managed on the Administration page and persisted to
`data/config/settings.json`. If you prefer, you can also set the SDK's standard
environment variables before starting the backend; values saved in the Administration
page take precedence for predictions:

```
TYPESAFE_BASE_URL   (default http://localhost:11434)
TYPESAFE_API_KEY    (default ollama)
TYPESAFE_DEFAULT_MODEL (default nimble)
```

The API key is never returned to the browser or logged.

---

## How a prediction works

1. The active session is validated.
2. The mode-specific model config is loaded from `./data/config/` and schema-checked.
3. Connection settings are loaded.
4. The session is converted into a concise natural-language `state` (browsing channel,
   dates, time zone, current/previous itinerary or conversation, days-to-departure, trip
   duration, route/date/passenger changes, convergence vs exploration signals).
5. The `state` is injected into the configured TypeSafe request.
6. The TypeSafe SDK is called via the isolated adapter against the configured endpoint and model.
7. The response is validated and normalized to:
   ```json
   {
     "intent": "High | Medium | Low",
     "probability": 0.0,
     "probabilityAvailable": true,
     "explanation": "string",
     "model": "string",
     "predictedAt": "ISO-8601 timestamp",
     "durationMs": 0
   }
   ```
   When the model provides no score, `probability` is `null` and `probabilityAvailable`
   is `false` (the UI shows "Probability not provided by the model." and nothing is fabricated).
8. The request, raw response, normalized result, timestamps, duration, and any error are
   saved to the session's prediction history.
9. The result is returned to the frontend.

---

## Security / safety notes

- The TypeSafe SDK is called **only from the backend**.
- The browser never reads or writes files directly; all persistence goes through the API.
- User input is sanitized server-side (control characters stripped, length capped) and all
  model output is rendered as escaped text (no `dangerouslySetInnerHTML`).
- The API key is masked in the UI, never sent back to the browser, and not logged.
- No secrets are hardcoded in source; defaults are the harmless local Ollama values.

---

## Project structure

```
backend/
  requirements.txt
  app/
    main.py              # FastAPI app: sessions, prediction, admin endpoints
    models.py            # Pydantic domain models
    storage.py           # Atomic JSON storage + config/settings seeding
    state_builder.py     # Session -> natural-language state
    random_generator.py  # Coherent random test data with intent profiles
    config_schema.py     # Model-config schema validation
    ollama_probe.py      # Ollama /api/tags + SDK /v1/models connection test
    typesafe_adapter.py  # *** The only module that imports the TypeSafe SDK ***
frontend/
  src/
    api.ts               # API client (Zod-validated responses)
    types.ts             # Shared Zod schemas / types
    pages/               # New Session, History, Administration, Session editor
    components/          # Mode editors, result + JSON viewers
data/                    # Local JSON storage (seeded on first run)
```
