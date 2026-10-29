"""Optional paid OpenRouter commander; never replaces the free agent pool.

A dedicated monthly-capped API key is mandatory. Failure to verify the cap
fails closed to the existing free providers. No credentials are logged.
"""
import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)
KEY_INFO_URL = "https://openrouter.ai/api/v1/key"
MAX_MONTHLY_USD = 3.0


def configured_model():
    if os.environ.get("BASAK_PAID_COMMANDER_ENABLED", "").lower() != "true":
        return ""
    value = os.environ.get("BASAK_KOMUTAN_MODEL", "").strip()
    if not value.startswith("openrouter:"):
        return ""
    model = value[len("openrouter:"):]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", model):
        return ""
    return model if not model.endswith(":free") else ""


def authorized_commander(job):
    """Only an explicitly designated owner can run a paid root agent task."""
    owner = os.environ.get("BASAK_PAID_COMMANDER_OWNER_ID", "").strip()
    return bool(owner and job.get("user_id") == owner
                and job.get("kind") == "agent"
                and not job.get("parent_id") and configured_model())


def scoped_model():
    """Only the explicit commander context may spend; subagents remain free."""
    from brain.model_havuzu import _SELECTION
    chosen = _SELECTION.get()
    model = configured_model()
    if model and chosen == ("openrouter_paid", model):
        return model
    return ""


def capped_key():
    """Require the provider-enforced monthly ceiling, not local best guesses."""
    key = os.environ.get("BASAK_PAID_OPENROUTER_API_KEY", "").strip()
    if not key:
        return ""
    try:
        response = httpx.get(
            KEY_INFO_URL, headers={"Authorization": "Bearer " + key},
            timeout=5, follow_redirects=False, trust_env=False)
        response.raise_for_status()
        info = response.json()["data"]
        limit = info.get("limit")
        remaining = info.get("limit_remaining")
        if (info.get("limit_reset") != "monthly"
                or not isinstance(limit, (float, int))
                or isinstance(limit, bool)
                or not 0 < limit <= MAX_MONTHLY_USD
                or not isinstance(remaining, (float, int))
                or remaining <= 0
                or info.get("is_management_key", False)):
            logger.warning("Ucretli beyin anahtari aylik en fazla 3 USD limitini dogrulamadi")
            return ""
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        logger.warning("OpenRouter harcama limiti okunamadi; ucretli beyin kapali")
        return ""
    return key


def prepend_commander(free_chain):
    """Add one paid first choice; preserve every existing free fallback."""
    model = scoped_model()
    if not model:
        return free_chain
    key = capped_key()
    if not key:
        return free_chain
    from brain.openrouter import OpenRouterClient
    paid = OpenRouterClient(key, model=model)
    if not paid.musait():
        return free_chain
    return [("openrouter_paid", paid), *free_chain]
