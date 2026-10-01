"""Ollama endpoint probing for the Administration "Test connection" feature.

This is deliberately separate from the TypeSafe prediction path. The TypeSafe
SDK does not expose a plain health-check, so for endpoint and model
availability we query Ollama's native `/api/tags` endpoint directly. The actual
SDK connectivity is exercised separately via the SDK's models.list().

Uses the standard library (urllib) to avoid adding an HTTP dependency; the SDK
ships httpx2, not httpx.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def _normalize_model_name(name: str) -> str:
    # nimble and nimble:latest should be treated as equivalent.
    return name.split(":", 1)[0].strip().lower()


def check_connection(base_url: str, model: str, timeout_seconds: float = 8.0) -> dict[str, Any]:
    """Probe Ollama endpoint availability and whether `model` is present.

    Returns a structured result; never raises for ordinary network failures.
    """
    base = base_url.rstrip("/")
    result: dict[str, Any] = {
        "endpointReachable": False,
        "modelAvailable": False,
        "sdkListModelsOk": False,
        "availableModels": [],
        "messages": [],
    }

    tags_url = f"{base}/api/tags"
    try:
        req = urllib.request.Request(tags_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result["endpointReachable"] = True
        models = [m.get("name", "") for m in data.get("models", []) if isinstance(m, dict)]
        result["availableModels"] = models
        wanted = _normalize_model_name(model)
        result["modelAvailable"] = any(_normalize_model_name(m) == wanted for m in models)
        if not result["modelAvailable"]:
            result["messages"].append(
                f"Model '{model}' was not found in the Ollama model list. "
                f"Pull it with: ollama pull {model.split(':', 1)[0]}"
            )
    except urllib.error.URLError as exc:
        result["messages"].append(
            f"Could not connect to Ollama at {base}: {exc.reason}. Is the Ollama server running?"
        )
        return result
    except Exception as exc:  # pragma: no cover - defensive
        result["messages"].append(f"Ollama probe failed: {exc}")
        return result

    return result


def check_sdk_list_models(base_url: str, api_key: str, model: str, timeout_seconds: float = 8.0) -> dict[str, Any]:
    """Exercise TypeSafe SDK connectivity via its models.list() call.

    Kept isolated here (imports the SDK client lazily) and tolerant: some
    TypeSafe-compatible endpoints (including Ollama) may not implement
    `/v1/models`, so a failure here is reported but not treated as fatal.
    """
    out: dict[str, Any] = {"ok": False, "message": ""}
    try:
        from typesafe_sdk import TypeSafeClient
    except Exception as exc:  # pragma: no cover
        out["message"] = f"TypeSafe SDK import failed: {exc}"
        return out

    try:
        with TypeSafeClient(api_key=api_key, base_url=base_url, model=model, timeout=timeout_seconds) as client:
            client.models.list()
        out["ok"] = True
        out["message"] = "TypeSafe SDK reached the /v1/models endpoint."
    except Exception as exc:
        out["message"] = (
            "TypeSafe SDK models.list() was not available on this endpoint "
            f"({type(exc).__name__}). This is expected for a plain Ollama server; "
            "predictions use the /v1/systemone endpoint instead."
        )
    return out
