"""Pydantic domain models shared by the API, storage, and validation layers."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid4().hex


class SearchMode(str, Enum):
    TRADITIONAL = "traditional"
    CONVERSATIONAL = "conversational"


class Channel(str, Enum):
    MOBILE = "Mobile"
    DESKTOP = "Desktop"
    VOICE = "Voice AI Assistant"


class PredictionStatus(str, Enum):
    NONE = "none"
    SUCCESS = "success"
    ERROR = "error"


# --- Traditional mode -------------------------------------------------------


class FlightSearch(BaseModel):
    id: str = Field(default_factory=new_id)
    origin: str = ""
    destination: str = ""
    departure_date: Optional[str] = None  # ISO date (YYYY-MM-DD)
    return_date: Optional[str] = None
    adults: int = 1
    children: int = 0

    @field_validator("origin", "destination")
    @classmethod
    def _upper_iata(cls, v: str) -> str:
        return (v or "").strip().upper()[:3]

    @field_validator("adults")
    @classmethod
    def _adults_range(cls, v: int) -> int:
        return max(0, min(9, int(v)))

    @field_validator("children")
    @classmethod
    def _children_range(cls, v: int) -> int:
        return max(0, min(9, int(v)))


class TraditionalInput(BaseModel):
    previous_searches: list[FlightSearch] = Field(default_factory=list)
    current_search: FlightSearch = Field(default_factory=FlightSearch)

    @field_validator("previous_searches")
    @classmethod
    def _cap_previous(cls, v: list[FlightSearch]) -> list[FlightSearch]:
        return v[:10]


# --- Conversational mode ----------------------------------------------------


class ChatMessage(BaseModel):
    id: str = Field(default_factory=new_id)
    text: str = ""


class ConversationalInput(BaseModel):
    previous_messages: list[ChatMessage] = Field(default_factory=list)
    current_request: str = ""

    @field_validator("previous_messages")
    @classmethod
    def _cap_messages(cls, v: list[ChatMessage]) -> list[ChatMessage]:
        return v[:10]


# --- Prediction history -----------------------------------------------------


class NormalizedResult(BaseModel):
    intent: Optional[Literal["High", "Medium", "Low"]] = None
    probability: Optional[float] = None
    probabilityAvailable: bool = False
    explanation: str = ""
    model: str = ""
    predictedAt: str = ""
    durationMs: int = 0


class PredictionRun(BaseModel):
    id: str = Field(default_factory=new_id)
    createdAt: str = Field(default_factory=utc_now_iso)
    status: Literal["success", "error"] = "success"
    state: str = ""
    sdkRequest: dict[str, Any] = Field(default_factory=dict)
    rawResponse: dict[str, Any] = Field(default_factory=dict)
    normalized: Optional[NormalizedResult] = None
    error: Optional[dict[str, Any]] = None
    durationMs: int = 0


# --- Session ----------------------------------------------------------------


class Session(BaseModel):
    id: str = Field(default_factory=new_id)
    name: Optional[str] = None
    mode: SearchMode = SearchMode.TRADITIONAL
    createdAt: str = Field(default_factory=utc_now_iso)
    updatedAt: str = Field(default_factory=utc_now_iso)

    # Browsing context
    browsingDate: Optional[str] = None  # ISO date
    browsingLocalTime: Optional[str] = None  # HH:MM
    timeZone: Optional[str] = None  # e.g. "Europe/Paris" or "UTC+02:00"
    channel: Channel = Channel.DESKTOP

    # Mode-specific input (only one is meaningful per mode, both kept for duplication safety)
    traditional: TraditionalInput = Field(default_factory=TraditionalInput)
    conversational: ConversationalInput = Field(default_factory=ConversationalInput)

    predictionHistory: list[PredictionRun] = Field(default_factory=list)
    lastPredictionStatus: PredictionStatus = PredictionStatus.NONE

    @model_validator(mode="after")
    def _touch_defaults(self) -> "Session":
        if not self.browsingDate:
            self.browsingDate = datetime.now(timezone.utc).date().isoformat()
        if not self.browsingLocalTime:
            self.browsingLocalTime = datetime.now().strftime("%H:%M")
        if not self.timeZone:
            self.timeZone = "UTC+00:00"
        return self


class SessionSummary(BaseModel):
    id: str
    name: Optional[str]
    mode: SearchMode
    createdAt: str
    updatedAt: str
    channel: Channel
    lastPredictionStatus: PredictionStatus
    predictionCount: int


# --- Connection settings ----------------------------------------------------

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_API_KEY = "ollama"
DEFAULT_MODEL = "nimble"


class ConnectionSettings(BaseModel):
    TYPESAFE_BASE_URL: str = DEFAULT_BASE_URL
    TYPESAFE_API_KEY: str = DEFAULT_API_KEY
    TYPESAFE_DEFAULT_MODEL: str = DEFAULT_MODEL

    @field_validator("TYPESAFE_BASE_URL")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        v = (v or "").strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("TYPESAFE_BASE_URL must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("TYPESAFE_DEFAULT_MODEL")
    @classmethod
    def _validate_model(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("TYPESAFE_DEFAULT_MODEL must not be empty")
        return v


def default_connection_settings() -> ConnectionSettings:
    return ConnectionSettings()
