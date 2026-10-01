"""Isolated TypeSafe SDK adapter.

This is the ONLY module that imports or references `typesafe_sdk`. Everything
SDK-version-specific lives here so it can be corrected in one place if the
installed SDK differs from the documentation.

Confirmed against typesafe-sdk 0.7.2 (verified live against local Ollama + nimble):

* Package name / import:   `pip install typesafe-sdk` -> `import typesafe_sdk`
* Sync & async clients:    `TypeSafeClient` (sync) and `AsyncTypeSafeClient`.
                           We use the synchronous client.
* Configuration:           constructor kwargs `api_key`, `base_url`, `model`,
                           `timeout`; env fallbacks TYPESAFE_API_KEY /
                           TYPESAFE_BASE_URL / TYPESAFE_DEFAULT_MODEL. base_url
                           is the root before `/v1/systemone` and `/v1/models`.
* Request:                 `client.system_one(state=<str|json>, questions={name: {
                               "type": "choice", "instructions": str,
                               "criteria": {label: description|None}}})`
                           Questions may be plain dicts (used here so the model
                           config JSON passes through faithfully).
* Response:                `SystemOneResponse` with `.model`, `.usage`,
                           `.answers` (dict name -> answer). A choice answer has
                           `.choice` (str), `.probabilities` (dict label->float)
                           and `.confidence` (float in 0..1).
* Probability/confidence:  YES. choice answers expose `confidence` and a
                           per-label `probabilities` map. We treat `confidence`
                           as the probability score, falling back to the winning
                           label's probability.
* Errors:                  `TypeSafeError` (base), `TypeSafeAPIError`,
                           `TypeSafeAPIConnectionError`, `TypeSafeAPITimeoutError`,
                           `TypeSafeAPIResponseValidationError`, plus HTTP-status
                           subclasses. All are caught and mapped to AdapterError.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

try:  # Import isolation: a single failure point if the SDK is absent/renamed.
    from typesafe_sdk import TypeSafeClient
    from typesafe_sdk import (
        TypeSafeError,
        TypeSafeAPIError,
        TypeSafeAPIConnectionError,
        TypeSafeAPITimeoutError,
        TypeSafeAPIResponseValidationError,
    )

    _SDK_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - defensive
    TypeSafeClient = None  # type: ignore[assignment]
    TypeSafeError = TypeSafeAPIError = TypeSafeAPIConnectionError = Exception  # type: ignore[assignment,misc]
    TypeSafeAPITimeoutError = TypeSafeAPIResponseValidationError = Exception  # type: ignore[assignment,misc]
    _SDK_IMPORT_ERROR = exc


# The question key the application uses for the booking-intent choice.
INTENT_QUESTION_KEY = "booking_intent"
# Canonical intent labels, in order.
INTENT_LABELS = ("High", "Medium", "Low")


class AdapterError(Exception):
    """A normalized, UI-safe error from the SDK layer.

    `kind` is a stable machine-readable category; `detail` is a human-readable
    message safe to surface. The raw SDK exception type name is kept for display
    but never the API key.
    """

    def __init__(self, kind: str, detail: str, sdk_error_type: str | None = None) -> None:
        super().__init__(detail)
        self.kind = kind
        self.detail = detail
        self.sdk_error_type = sdk_error_type

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "detail": self.detail, "sdkErrorType": self.sdk_error_type}


@dataclass
class NormalizedPrediction:
    """Application-shaped prediction result independent of the SDK."""

    intent: str | None
    probability: float | None
    probability_available: bool
    explanation: str
    model: str
    predicted_at: str
    duration_ms: int
    raw_response: dict[str, Any] = field(default_factory=dict)
    sdk_request: dict[str, Any] = field(default_factory=dict)


def sdk_available() -> bool:
    return TypeSafeClient is not None


def sdk_import_error() -> str | None:
    return str(_SDK_IMPORT_ERROR) if _SDK_IMPORT_ERROR else None


def _coerce_question_config(questions: dict[str, Any]) -> dict[str, Any]:
    """Pass model-config questions through as plain dicts.

    The SDK accepts raw dicts for questions, so we forward the configured
    questions verbatim (minus any empty criteria values coerced to None), which
    preserves unknown/SDK-specific fields.
    """
    coerced: dict[str, Any] = {}
    for name, q in questions.items():
        if not isinstance(q, dict):
            continue
        item = dict(q)
        crit = item.get("criteria")
        if isinstance(crit, dict):
            # Normalize empty-string descriptions to None (SDK treats None as "no description").
            item["criteria"] = {k: (v if v not in ("", None) else None) for k, v in crit.items()}
        coerced[name] = item
    return coerced


def _extract_choice_answer(raw: dict[str, Any]) -> dict[str, Any] | None:
    answers = raw.get("answers")
    if not isinstance(answers, dict):
        return None
    # Prefer the configured intent key, else the first choice-typed answer.
    candidate = answers.get(INTENT_QUESTION_KEY)
    if isinstance(candidate, dict) and candidate.get("type") == "choice":
        return candidate
    for value in answers.values():
        if isinstance(value, dict) and value.get("type") == "choice":
            return value
    return None


def _normalize_intent_label(choice: Any) -> str | None:
    if not isinstance(choice, str):
        return None
    for label in INTENT_LABELS:
        if choice.strip().lower() == label.lower():
            return label
    return None


def run_prediction(
    *,
    state: str,
    questions: dict[str, Any],
    base_url: str,
    api_key: str,
    model: str,
    timeout_seconds: float,
) -> NormalizedPrediction:
    """Call the TypeSafe SDK once and return a normalized, validated result.

    Raises AdapterError for any SDK/connection/validation failure.
    """
    if TypeSafeClient is None:
        raise AdapterError(
            "sdk_unavailable",
            "The TypeSafe SDK is not installed or failed to import. "
            + (sdk_import_error() or ""),
        )

    coerced_questions = _coerce_question_config(questions)
    if not coerced_questions:
        raise AdapterError("invalid_request", "No valid questions were provided in the model configuration.")

    # The exact body the SDK will build (for display/debugging). This mirrors
    # the system_one request fields; it is not the literal wire bytes.
    sdk_request = {
        "model": model,
        "state": state,
        "questions": coerced_questions,
    }

    started = time.perf_counter()
    predicted_at = _utc_now_iso()
    try:
        with TypeSafeClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout_seconds,
        ) as client:
            response = client.system_one(state=state, questions=coerced_questions)
    except TypeSafeAPITimeoutError as exc:  # type: ignore[misc]
        raise AdapterError("timeout", f"The model did not respond within {timeout_seconds:.0f}s.", type(exc).__name__)
    except TypeSafeAPIConnectionError as exc:  # type: ignore[misc]
        raise AdapterError(
            "connection",
            "Could not connect to the Ollama endpoint. Confirm Ollama is running and the base URL is correct.",
            type(exc).__name__,
        )
    except TypeSafeAPIResponseValidationError as exc:  # type: ignore[misc]
        raise AdapterError(
            "malformed_response",
            "The model returned a response the SDK could not validate.",
            type(exc).__name__,
        )
    except TypeSafeAPIError as exc:  # type: ignore[misc]
        raise AdapterError("api_error", f"The TypeSafe API returned an error: {exc}", type(exc).__name__)
    except TypeSafeError as exc:  # type: ignore[misc]
        raise AdapterError("sdk_error", f"The TypeSafe SDK rejected the request: {exc}", type(exc).__name__)
    except Exception as exc:  # pragma: no cover - unexpected
        raise AdapterError("unknown", f"Unexpected SDK error: {exc}", type(exc).__name__)

    duration_ms = int((time.perf_counter() - started) * 1000)

    # Convert the SDK response to a plain dict for storage/display.
    raw_response = _response_to_dict(response)

    choice_answer = _extract_choice_answer(raw_response)
    if choice_answer is None:
        raise AdapterError(
            "malformed_response",
            "The model response did not contain a usable choice answer for booking intent.",
        )

    intent = _normalize_intent_label(choice_answer.get("choice"))
    if intent is None:
        raise AdapterError(
            "malformed_response",
            f"The model returned an unexpected intent label: {choice_answer.get('choice')!r}.",
        )

    probability, probability_available = _extract_probability(choice_answer, intent)
    explanation = _build_explanation(intent, probability, probability_available, choice_answer)
    resolved_model = raw_response.get("model") or model

    return NormalizedPrediction(
        intent=intent,
        probability=probability,
        probability_available=probability_available,
        explanation=explanation,
        model=resolved_model,
        predicted_at=predicted_at,
        duration_ms=duration_ms,
        raw_response=raw_response,
        sdk_request=sdk_request,
    )


def _extract_probability(choice_answer: dict[str, Any], intent: str) -> tuple[float | None, bool]:
    """Return (probability, available).

    Prefer the answer's `confidence`; fall back to the winning label's entry in
    `probabilities`. Never fabricate a value.
    """
    confidence = choice_answer.get("confidence")
    if isinstance(confidence, (int, float)) and 0.0 <= float(confidence) <= 1.0:
        return float(confidence), True

    probs = choice_answer.get("probabilities")
    if isinstance(probs, dict):
        value = probs.get(intent)
        if isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0:
            return float(value), True

    return None, False


def _build_explanation(
    intent: str,
    probability: float | None,
    probability_available: bool,
    choice_answer: dict[str, Any],
) -> str:
    """Create a short natural-language explanation strictly from the response.

    We do not assert certainty beyond what the model reported.
    """
    parts = [f"The model classified booking intent as {intent}."]
    if probability_available and probability is not None:
        parts.append(f"Reported confidence is {probability * 100:.1f}%.")
    else:
        parts.append("The model did not report a confidence score.")

    probs = choice_answer.get("probabilities")
    if isinstance(probs, dict) and probs:
        ranked = sorted(
            ((label, val) for label, val in probs.items() if isinstance(val, (int, float))),
            key=lambda item: item[1],
            reverse=True,
        )
        if ranked:
            breakdown = ", ".join(f"{label} {float(val) * 100:.0f}%" for label, val in ranked)
            parts.append(f"Per-label probabilities: {breakdown}.")
    return " ".join(parts)


def _response_to_dict(response: Any) -> dict[str, Any]:
    """Best-effort conversion of the SDK response object to a JSON-safe dict."""
    # Pydantic v2 models expose model_dump(mode="json").
    for method in ("model_dump",):
        fn = getattr(response, method, None)
        if callable(fn):
            try:
                return fn(mode="json")  # type: ignore[misc]
            except TypeError:
                return fn()
    if isinstance(response, dict):
        return response
    return {"repr": repr(response)}


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
