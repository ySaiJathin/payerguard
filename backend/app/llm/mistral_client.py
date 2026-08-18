"""Thin wrapper around the official `mistralai` client (research.md).

Uses Mistral's own structured-output mode (`chat.parse(response_format=...)`)
so the six-field JSON shape is enforced by Mistral's API itself, not by
best-effort free-text parsing on our side. `MISTRAL_API_KEY` is read only
from the environment (spec FR-008) -- never hardcoded, never logged.

Retries exactly once on a genuinely transient network error (timeout /
connection failure) before surfacing `MistralAPIError` -- never an
unbounded/indefinite retry (spec FR-007), and never a retry on a
content/rate-limit error, where retrying wouldn't help and would just
delay surfacing the failure.
"""

import os

import httpx

from app.llm.errors import MistralAPIError
from app.llm.schemas import InvestigationDraft

DEFAULT_MODEL = "mistral-small-latest"
DEFAULT_TIMEOUT_S = 45
_TRANSIENT_ERRORS = (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)


def _build_default_client(timeout_s: float):
    from mistralai.client import Mistral

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise MistralAPIError(
            "MISTRAL_API_KEY is not set in the environment -- see .env.example."
        )
    return Mistral(api_key=api_key, timeout_ms=int(timeout_s * 1000))


def call_mistral(
    prompt: str,
    client=None,
    model: str = DEFAULT_MODEL,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> InvestigationDraft:
    resolved_client = client or _build_default_client(timeout_s)

    attempts = 0
    last_error: Exception | None = None
    while attempts < 2:
        attempts += 1
        try:
            response = resolved_client.chat.parse(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format=InvestigationDraft,
            )
            return response.choices[0].message.parsed
        except _TRANSIENT_ERRORS as exc:
            last_error = exc
            continue  # one retry for genuinely transient network failures only
        except Exception as exc:  # noqa: BLE001 -- any other Mistral/SDK error fails fast
            raise MistralAPIError(f"Mistral API call failed: {exc}") from exc

    raise MistralAPIError(f"Mistral API call failed after retry: {last_error}") from last_error
