"""Privacy-safe observations for real model calls in durable runs.

This does not select a provider or alter a model response. No prompt,
response text, credentials, endpoint, or provider exception text is stored.
Absent an authenticated durable execution, observation is a no-op.
"""
import logging
import re

logger = logging.getLogger(__name__)
_MODEL_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_./:+-]{0,159}$")
_PROVIDER = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")


def record(kind, provider, *, duration_ms=None, outcome=None, model=None):
    """Append a small metadata-only event; telemetry must never fail a chat."""
    if kind not in ("providerAttempt", "providerResult", "modelReported"):
        return
    if not isinstance(provider, str) or not _PROVIDER.fullmatch(provider):
        return
    payload = {"provider": provider}
    if kind == "providerResult":
        if outcome not in ("success", "error", "empty", "tool_call"):
            return
        payload["outcome"] = outcome
        if isinstance(duration_ms, (int, float)) and 0 <= duration_ms < 86_400_000:
            payload["duration_ms"] = int(duration_ms)
    if kind == "modelReported":
        if not isinstance(model, str) or not _MODEL_ID.fullmatch(model):
            return
        payload["model"] = model
    try:
        from chat.platform_context import current
        ctx = current()
        if ctx is not None and ctx.control is not None:
            ctx.control.event(kind, payload)
    except Exception:
        logger.debug("Provider observation unavailable", exc_info=True)
