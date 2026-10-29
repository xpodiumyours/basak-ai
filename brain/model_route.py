"""Execution routing policy, not an artificial model brain.

In single mode one available existing provider handles a request.  No
task-text classification, response rewriting, new API keys or silent
multi-provider queue. All existing free providers remain eligible on
subsequent requests. The legacy chain is retained for rollback.
"""
import os


def single_route():
    return os.environ.get("BASAK_MODEL_ROUTING_MODE", "").strip().lower() == "single"


def one_eligible(ordered, stats, quota_check, cooldown_check):
    """Choose from measured, technically available providers without API calls."""
    for name in ordered:
        if quota_check(name, stats):
            continue
        if cooldown_check(name) > 0:
            continue
        return [name]
    return []
