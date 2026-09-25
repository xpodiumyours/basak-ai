"""Basak gercek capability registry metadata'si.

53 gercek arac icin tek runtime kaynak tools.definitions.TOOLS'tur.
Namespace'ler kullanici metnini SINIFLANDIRMAZ; modelin yetenek_ac ile
sectigi alan adini gercek arac semalarina ceviren katalogdur.
"""

from tools.definitions import TOOLS
from chat.agent_protocol import YETENEK_ALANLARI

# Tek kaynak: chat.agent_protocol.YETENEK_ALANLARI (AGENTS.md §0, madde 3).
CAPABILITY_NAMESPACES = YETENEK_ALANLARI


def tool_names(tools=None):
    return tuple(
        (t.get("function") or {}).get("name")
        for t in (TOOLS if tools is None else tools)
        if isinstance(t, dict) and (t.get("function") or {}).get("name")
    )


def validate_registry(tools=None):
    names = tool_names(tools)
    flat = [name for group in CAPABILITY_NAMESPACES.values() for name in group]
    missing = sorted(set(names) - set(flat))
    unknown = sorted(set(flat) - set(names))
    duplicates = sorted({x for x in flat if flat.count(x) > 1})
    return {
        "ok": not missing and not unknown and not duplicates
              and len(flat) == len(names),
        "tool_count": len(names),
        "namespace_count": len(CAPABILITY_NAMESPACES),
        "missing": missing,
        "unknown": unknown,
        "duplicates": duplicates,
    }


def namespace_schemas(namespace, tools=None):
    """Kabul/native discovery gorunumu; runtime gating DEGIL."""
    allowed = set(CAPABILITY_NAMESPACES.get(str(namespace or ""), ()))
    katalog = TOOLS if tools is None else tools
    return [
        t for t in katalog
        if (t.get("function") or {}).get("name") in allowed
    ]
