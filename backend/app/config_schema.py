"""Validation of model-configuration JSON against the required application schema.

Preserves unknown valid fields so SDK-specific extensions are not lost; we only
check that the required structure is present and well-typed.
"""
from __future__ import annotations

from typing import Any


class ConfigValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def validate_model_config(config: Any) -> list[str]:
    """Return a list of human-readable errors; empty list means valid."""
    errors: list[str] = []

    if not isinstance(config, dict):
        return ["Configuration root must be a JSON object."]

    model = config.get("model")
    if not isinstance(model, str) or not model.strip():
        errors.append("Field 'model' must be a non-empty string.")

    if "state" in config and not isinstance(config.get("state"), str):
        errors.append("Field 'state' must be a string when present.")

    questions = config.get("questions")
    if not isinstance(questions, dict) or not questions:
        errors.append("Field 'questions' must be a non-empty object.")
        return errors

    if "booking_intent" not in questions:
        errors.append("Field 'questions' must include a 'booking_intent' question.")

    for name, q in questions.items():
        prefix = f"questions.{name}"
        if not isinstance(q, dict):
            errors.append(f"{prefix} must be an object.")
            continue
        qtype = q.get("type")
        if qtype not in ("choice", "noul", "score"):
            errors.append(f"{prefix}.type must be one of 'choice', 'noul', 'score'.")
        if not isinstance(q.get("instructions"), str) or not q["instructions"].strip():
            errors.append(f"{prefix}.instructions must be a non-empty string.")
        if qtype == "choice":
            criteria = q.get("criteria")
            if not isinstance(criteria, dict) or not criteria:
                errors.append(f"{prefix}.criteria must be a non-empty object for a 'choice' question.")
            elif name == "booking_intent":
                missing = [lbl for lbl in ("High", "Medium", "Low") if lbl not in criteria]
                if missing:
                    errors.append(
                        f"{prefix}.criteria must include labels High, Medium, Low (missing: {', '.join(missing)})."
                    )
        if qtype == "score":
            criteria = q.get("criteria")
            if not isinstance(criteria, list) or not criteria:
                errors.append(f"{prefix}.criteria must be a non-empty list for a 'score' question.")

    return errors
