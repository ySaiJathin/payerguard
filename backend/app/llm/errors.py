"""Error types for LLM investigation (contracts/api.md's error responses)."""


class MistralAPIError(RuntimeError):
    """Raised when the Mistral API call fails (timeout, rate limit, service
    error) after the single permitted retry (spec FR-007) -- maps to
    `502 Bad Gateway`."""


class MalformedResponseError(RuntimeError):
    """Raised when Mistral's response doesn't satisfy the six-section
    content rules (non-empty sections) even though it parsed as valid
    JSON (spec FR-004) -- maps to `422 Unprocessable Entity`."""


class IncidentNotFoundError(RuntimeError):
    """Raised when `POST /llm/investigate` is called with only an
    `incident_id` and no inline `structured_payload` -- Phase 12's
    Incident store doesn't exist yet to resolve it against -- maps to
    `404 Not Found`."""
