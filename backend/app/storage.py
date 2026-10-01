"""Local JSON file storage with atomic writes and validation.

Layout (all under the project `./data/` directory):

    data/
      config/
        settings.json                       # connection settings
        traditional-flight-search.json      # model config (mode A)
        conversational-flight-search.json   # model config (mode B)
      sessions/
        <session-id>.json                   # one file per session

No database is used. Writes are atomic (write temp file, then os.replace).
All reads/writes validate JSON before persisting.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from .models import (
    ConnectionSettings,
    Session,
    SessionSummary,
    default_connection_settings,
)

# Resolve ./data relative to the project root (two levels up from this file:
# backend/app/storage.py -> project root). Overridable via DATA_DIR env var.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("DATA_DIR", _PROJECT_ROOT / "data"))
CONFIG_DIR = DATA_DIR / "config"
SESSIONS_DIR = DATA_DIR / "sessions"

SETTINGS_FILE = CONFIG_DIR / "settings.json"
TRADITIONAL_CONFIG_FILE = CONFIG_DIR / "traditional-flight-search.json"
CONVERSATIONAL_CONFIG_FILE = CONFIG_DIR / "conversational-flight-search.json"

_write_lock = threading.Lock()


# --- Default model configs (seeded on first run) ----------------------------

_INTENT_QUESTIONS = {
    "booking_intent": {
        "type": "choice",
        "instructions": (
            "Evaluate the likelihood that the traveler will complete a flight booking "
            "during the current search session based on session behavior and search parameters."
        ),
        "criteria": {
            "High": (
                "Traveler has converged on exact travel parameters, repeated an identical flight "
                "query, viewed specific seat or fare rules, entered passenger or payment details, "
                "or is booking urgent or near-term travel."
            ),
            "Medium": (
                "Traveler is testing slight date variations of approximately two to five days with "
                "the same origin and destination, comparing narrow pricing options, or maintaining "
                "similar stay durations across repeated searches."
            ),
            "Low": (
                "Traveler is in an early exploration stage, with a long advance booking window, "
                "broad destination switching, major date shifts, or browsing behavior that does not "
                "show a narrowed itinerary."
            ),
        },
    }
}

DEFAULT_TRADITIONAL_CONFIG: dict[str, Any] = {
    "model": "nimble",
    "state": "",
    "questions": _INTENT_QUESTIONS,
}

DEFAULT_CONVERSATIONAL_CONFIG: dict[str, Any] = {
    "model": "nimble",
    "state": "",
    "questions": _INTENT_QUESTIONS,
}


# --- Low-level atomic IO ----------------------------------------------------


def _atomic_write_json(path: Path, data: Any) -> None:
    """Serialize `data` to JSON and write it atomically.

    The data is fully serialized (and thereby validated as JSON-encodable)
    before any file is touched. The temp file is created in the same directory
    so os.replace is atomic on the same filesystem.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    # Validate round-trip before writing.
    json.loads(payload)

    with _write_lock:
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# --- Initialization / seeding ----------------------------------------------


def ensure_initialized() -> None:
    """Create directories and seed config files on first run (idempotent)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    if not SETTINGS_FILE.exists():
        _atomic_write_json(SETTINGS_FILE, default_connection_settings().model_dump())
    if not TRADITIONAL_CONFIG_FILE.exists():
        _atomic_write_json(TRADITIONAL_CONFIG_FILE, DEFAULT_TRADITIONAL_CONFIG)
    if not CONVERSATIONAL_CONFIG_FILE.exists():
        _atomic_write_json(CONVERSATIONAL_CONFIG_FILE, DEFAULT_CONVERSATIONAL_CONFIG)


# --- Connection settings ----------------------------------------------------


def load_settings() -> ConnectionSettings:
    ensure_initialized()
    try:
        raw = _read_json(SETTINGS_FILE)
        return ConnectionSettings.model_validate(raw)
    except Exception:
        # Corrupt settings -> fall back to defaults (do not crash the app).
        return default_connection_settings()


def save_settings(settings: ConnectionSettings) -> ConnectionSettings:
    _atomic_write_json(SETTINGS_FILE, settings.model_dump())
    return settings


def reset_settings() -> ConnectionSettings:
    settings = default_connection_settings()
    _atomic_write_json(SETTINGS_FILE, settings.model_dump())
    return settings


# --- Model configs ----------------------------------------------------------


def _config_path(mode: str) -> Path:
    if mode == "traditional":
        return TRADITIONAL_CONFIG_FILE
    if mode == "conversational":
        return CONVERSATIONAL_CONFIG_FILE
    raise ValueError(f"Unknown config mode: {mode}")


def _default_config(mode: str) -> dict[str, Any]:
    return DEFAULT_TRADITIONAL_CONFIG if mode == "traditional" else DEFAULT_CONVERSATIONAL_CONFIG


def load_config(mode: str) -> dict[str, Any]:
    ensure_initialized()
    path = _config_path(mode)
    try:
        return _read_json(path)
    except Exception:
        return _default_config(mode)


def config_modified_at(mode: str) -> str | None:
    path = _config_path(mode)
    if not path.exists():
        return None
    from datetime import datetime, timezone

    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def save_config(mode: str, config: dict[str, Any]) -> dict[str, Any]:
    path = _config_path(mode)
    _atomic_write_json(path, config)
    return config


def reset_config(mode: str) -> dict[str, Any]:
    path = _config_path(mode)
    default = _default_config(mode)
    _atomic_write_json(path, default)
    return default


# --- Sessions ---------------------------------------------------------------


def _session_path(session_id: str) -> Path:
    # Guard against path traversal: session ids are hex, but be defensive.
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
    if not safe or safe != session_id:
        raise ValueError("Invalid session id")
    return SESSIONS_DIR / f"{safe}.json"


def save_session(session: Session) -> Session:
    _atomic_write_json(_session_path(session.id), session.model_dump(mode="json"))
    return session


def load_session(session_id: str) -> Session | None:
    try:
        path = _session_path(session_id)
    except ValueError:
        return None
    if not path.exists():
        return None
    try:
        return Session.model_validate(_read_json(path))
    except Exception:
        return None


def delete_session(session_id: str) -> bool:
    try:
        path = _session_path(session_id)
    except ValueError:
        return False
    if path.exists():
        path.unlink()
        return True
    return False


def list_sessions() -> list[SessionSummary]:
    ensure_initialized()
    summaries: list[SessionSummary] = []
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            session = Session.model_validate(_read_json(path))
        except Exception:
            continue
        summaries.append(
            SessionSummary(
                id=session.id,
                name=session.name,
                mode=session.mode,
                createdAt=session.createdAt,
                updatedAt=session.updatedAt,
                channel=session.channel,
                lastPredictionStatus=session.lastPredictionStatus,
                predictionCount=len(session.predictionHistory),
            )
        )
    summaries.sort(key=lambda s: s.updatedAt, reverse=True)
    return summaries
