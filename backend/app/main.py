"""FastAPI application: sessions, prediction, admin (settings + model configs).

The TypeSafe SDK is only ever called from this backend via `typesafe_adapter`.
The browser never touches files directly.
"""
from __future__ import annotations

import html
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import storage
from .config_schema import validate_model_config
from .models import (
    Channel,
    ConnectionSettings,
    PredictionRun,
    PredictionStatus,
    NormalizedResult,
    SearchMode,
    Session,
    SessionSummary,
    new_id,
    utc_now_iso,
)
from .ollama_probe import check_connection, check_sdk_list_models
from .random_generator import generate_session
from .state_builder import build_state
from . import typesafe_adapter

app = FastAPI(title="Booking Intent Detection", version="1.0.0")

# Local dev: the Vite dev server runs on a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    storage.ensure_initialized()


# A generous default prediction timeout: the 9B model can be slow to load.
PREDICTION_TIMEOUT_SECONDS = 180.0


def _sanitize_text(value: Optional[str]) -> Optional[str]:
    """Light server-side sanitization of free text we persist.

    We strip control characters and cap length. Rendering escaping is also done
    on the frontend; this is defense in depth.
    """
    if value is None:
        return None
    cleaned = "".join(ch for ch in value if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return cleaned[:5000]


def _sanitize_session(session: Session) -> Session:
    session.name = _sanitize_text(session.name)
    for m in session.conversational.previous_messages:
        m.text = _sanitize_text(m.text) or ""
    session.conversational.current_request = _sanitize_text(session.conversational.current_request) or ""
    return session


# --- Health -----------------------------------------------------------------


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "sdkAvailable": typesafe_adapter.sdk_available(),
        "sdkImportError": typesafe_adapter.sdk_import_error(),
    }


# --- Sessions ---------------------------------------------------------------


@app.get("/api/sessions", response_model=list[SessionSummary])
def api_list_sessions() -> list[SessionSummary]:
    return storage.list_sessions()


@app.post("/api/sessions", response_model=Session)
def api_create_session(session: Session) -> Session:
    session.id = new_id()
    session.createdAt = utc_now_iso()
    session.updatedAt = session.createdAt
    _sanitize_session(session)
    return storage.save_session(session)


@app.get("/api/sessions/{session_id}", response_model=Session)
def api_get_session(session_id: str) -> Session:
    session = storage.load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.put("/api/sessions/{session_id}", response_model=Session)
def api_update_session(session_id: str, session: Session) -> Session:
    existing = storage.load_session(session_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Session not found")
    # Preserve immutable fields and prediction history.
    session.id = session_id
    session.createdAt = existing.createdAt
    session.predictionHistory = existing.predictionHistory
    session.lastPredictionStatus = existing.lastPredictionStatus
    session.updatedAt = utc_now_iso()
    _sanitize_session(session)
    return storage.save_session(session)


@app.delete("/api/sessions/{session_id}")
def api_delete_session(session_id: str) -> dict[str, Any]:
    ok = storage.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}


@app.post("/api/sessions/{session_id}/duplicate", response_model=Session)
def api_duplicate_session(session_id: str) -> Session:
    existing = storage.load_session(session_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Session not found")
    clone = existing.model_copy(deep=True)
    clone.id = new_id()
    clone.name = (existing.name or f"{existing.mode.value} session") + " (copy)"
    clone.createdAt = utc_now_iso()
    clone.updatedAt = clone.createdAt
    clone.predictionHistory = []
    clone.lastPredictionStatus = PredictionStatus.NONE
    return storage.save_session(clone)


# --- Random generation ------------------------------------------------------


class GenerateRequest(BaseModel):
    mode: str = "traditional"
    profile: str = "random"


@app.post("/api/generate", response_model=Session)
def api_generate(req: GenerateRequest) -> Session:
    """Return an unsaved, coherent random session (frontend decides to save)."""
    return generate_session(req.mode, req.profile)


# --- Prediction -------------------------------------------------------------


@app.post("/api/sessions/{session_id}/predict", response_model=Session)
def api_predict(session_id: str) -> Session:
    session = storage.load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # 1. Validate the active session has usable input.
    _validate_predictable(session)

    # 2. Load the mode-specific model config.
    mode_key = "conversational" if session.mode == SearchMode.CONVERSATIONAL else "traditional"
    config = storage.load_config(mode_key)
    errors = validate_model_config(config)
    if errors:
        raise HTTPException(status_code=400, detail=f"Model configuration invalid: {'; '.join(errors)}")

    # 3. Load connection settings.
    settings = storage.load_settings()

    # 4. Build the natural-language state.
    state = build_state(session)

    # 5/6. Inject state + call the SDK via the isolated adapter.
    questions = config.get("questions", {})
    model = config.get("model") or settings.TYPESAFE_DEFAULT_MODEL

    run = PredictionRun(state=state)
    try:
        prediction = typesafe_adapter.run_prediction(
            state=state,
            questions=questions,
            base_url=settings.TYPESAFE_BASE_URL,
            api_key=settings.TYPESAFE_API_KEY,
            model=model,
            timeout_seconds=PREDICTION_TIMEOUT_SECONDS,
        )
        # 7. Validate/normalize already done in adapter.
        run.status = "success"
        run.sdkRequest = prediction.sdk_request
        run.rawResponse = prediction.raw_response
        run.durationMs = prediction.duration_ms
        run.normalized = NormalizedResult(
            intent=prediction.intent,
            probability=prediction.probability,
            probabilityAvailable=prediction.probability_available,
            explanation=prediction.explanation,
            model=prediction.model,
            predictedAt=prediction.predicted_at,
            durationMs=prediction.duration_ms,
        )
        session.lastPredictionStatus = PredictionStatus.SUCCESS
    except typesafe_adapter.AdapterError as exc:
        run.status = "error"
        run.error = exc.to_dict()
        session.lastPredictionStatus = PredictionStatus.ERROR

    # 8. Persist the run in the session's prediction history (newest first).
    session.predictionHistory.insert(0, run)
    session.updatedAt = utc_now_iso()
    storage.save_session(session)

    # 9. Return the updated session (contains the new run).
    return session


def _validate_predictable(session: Session) -> None:
    if session.mode == SearchMode.CONVERSATIONAL:
        data = session.conversational
        if not (data.current_request.strip() or any(m.text.strip() for m in data.previous_messages)):
            raise HTTPException(
                status_code=400,
                detail="A conversational session needs at least one message or a current request.",
            )
    else:
        cur = session.traditional.current_search
        if not (cur.origin and cur.destination):
            raise HTTPException(
                status_code=400,
                detail="The current search needs both an origin and a destination.",
            )
        if cur.origin == cur.destination:
            raise HTTPException(status_code=400, detail="Origin and destination must differ.")


# --- Admin: connection settings ---------------------------------------------


class SettingsResponse(BaseModel):
    TYPESAFE_BASE_URL: str
    TYPESAFE_DEFAULT_MODEL: str
    apiKeySet: bool = Field(..., description="Whether an API key is stored (value never returned).")


def _settings_to_response(s: ConnectionSettings) -> SettingsResponse:
    return SettingsResponse(
        TYPESAFE_BASE_URL=s.TYPESAFE_BASE_URL,
        TYPESAFE_DEFAULT_MODEL=s.TYPESAFE_DEFAULT_MODEL,
        apiKeySet=bool(s.TYPESAFE_API_KEY),
    )


@app.get("/api/settings", response_model=SettingsResponse)
def api_get_settings() -> SettingsResponse:
    # The API key value is never sent to the browser.
    return _settings_to_response(storage.load_settings())


class SettingsUpdate(BaseModel):
    TYPESAFE_BASE_URL: str
    TYPESAFE_DEFAULT_MODEL: str
    # Optional: only overwrite the key if provided (keeps masking workflow safe).
    TYPESAFE_API_KEY: Optional[str] = None


@app.put("/api/settings", response_model=SettingsResponse)
def api_update_settings(update: SettingsUpdate) -> SettingsResponse:
    current = storage.load_settings()
    new_key = update.TYPESAFE_API_KEY if update.TYPESAFE_API_KEY is not None and update.TYPESAFE_API_KEY != "" else current.TYPESAFE_API_KEY
    try:
        settings = ConnectionSettings(
            TYPESAFE_BASE_URL=update.TYPESAFE_BASE_URL,
            TYPESAFE_API_KEY=new_key,
            TYPESAFE_DEFAULT_MODEL=update.TYPESAFE_DEFAULT_MODEL,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    storage.save_settings(settings)
    return _settings_to_response(settings)


@app.post("/api/settings/reset", response_model=SettingsResponse)
def api_reset_settings() -> SettingsResponse:
    return _settings_to_response(storage.reset_settings())


@app.post("/api/settings/test")
def api_test_connection() -> dict[str, Any]:
    s = storage.load_settings()
    probe = check_connection(s.TYPESAFE_BASE_URL, s.TYPESAFE_DEFAULT_MODEL)
    sdk = check_sdk_list_models(s.TYPESAFE_BASE_URL, s.TYPESAFE_API_KEY, s.TYPESAFE_DEFAULT_MODEL)
    probe["sdkListModelsOk"] = sdk["ok"]
    probe["messages"].append(sdk["message"])
    probe["success"] = probe["endpointReachable"] and probe["modelAvailable"]
    return probe


# --- Admin: model configs ---------------------------------------------------


class ConfigResponse(BaseModel):
    mode: str
    config: dict[str, Any]
    modifiedAt: Optional[str]


@app.get("/api/configs/{mode}", response_model=ConfigResponse)
def api_get_config(mode: str) -> ConfigResponse:
    if mode not in ("traditional", "conversational"):
        raise HTTPException(status_code=404, detail="Unknown config mode")
    return ConfigResponse(mode=mode, config=storage.load_config(mode), modifiedAt=storage.config_modified_at(mode))


class ConfigUpdate(BaseModel):
    config: dict[str, Any]


@app.put("/api/configs/{mode}", response_model=ConfigResponse)
def api_update_config(mode: str, update: ConfigUpdate) -> ConfigResponse:
    if mode not in ("traditional", "conversational"):
        raise HTTPException(status_code=404, detail="Unknown config mode")
    errors = validate_model_config(update.config)
    if errors:
        raise HTTPException(status_code=422, detail={"message": "Configuration failed schema validation", "errors": errors})
    saved = storage.save_config(mode, update.config)
    return ConfigResponse(mode=mode, config=saved, modifiedAt=storage.config_modified_at(mode))


@app.post("/api/configs/{mode}/reset", response_model=ConfigResponse)
def api_reset_config(mode: str) -> ConfigResponse:
    if mode not in ("traditional", "conversational"):
        raise HTTPException(status_code=404, detail="Unknown config mode")
    saved = storage.reset_config(mode)
    return ConfigResponse(mode=mode, config=saved, modifiedAt=storage.config_modified_at(mode))


class ValidateConfigRequest(BaseModel):
    config: dict[str, Any]


@app.post("/api/configs/{mode}/validate")
def api_validate_config(mode: str, req: ValidateConfigRequest) -> dict[str, Any]:
    errors = validate_model_config(req.config)
    return {"valid": not errors, "errors": errors}
