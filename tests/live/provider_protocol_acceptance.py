"""Phase 1: 8 provider official tool-protocol live acceptance.

Scope is intentionally ONLY phase 1 of the agreed sequence:
8 providers -> one safe tool-call round trip each -> final response.
No 52-tool/416-cell claims are made here.
"""

import json
import os
from pathlib import Path

PROVIDERS = (
    "groq", "gemini", "openrouter", "glm",
    "cloudflare", "cohere", "kilo", "nvidia",
)

CREDENTIALS = {
    "groq": ("GROQ_API_KEY",),
    "gemini": ("GEMINI_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY",),
    "glm": ("ZAI_API_KEY",),
    "cloudflare": ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"),
    "cohere": ("COHERE_API_KEY",),
    "kilo": (),
    "nvidia": ("NVIDIA_API_KEY",),
}

PROBE_TOOL = {
    "type": "function",
    "function": {
        "name": "protokol_probe",
        "description": (
            "Protocol acceptance probe. Call this function exactly once and "
            "return the supplied text in the echo argument."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "echo": {
                    "type": "string",
                    "description": "Return exactly BASAK_PROTOCOL_OK",
                }
            },
            "required": ["echo"],
            "additionalProperties": False,
        },
    },
}

PROMPT = (
    "This is a provider tool-protocol acceptance test. "
    "Call the available protokol_probe function exactly once. "
    "Set echo to BASAK_PROTOCOL_OK. Do not answer in plain text before "
    "the tool call."
)


def _short(value, limit=220):
    s = str(value or "").replace("\n", " ").replace("|", "/")
    return s if len(s) <= limit else s[:limit - 3] + "..."


def _credential_state(provider):
    required = CREDENTIALS[provider]
    missing = [name for name in required if not os.environ.get(name)]
    return not missing, missing


def _tool_calls(reply):
    if not isinstance(reply, dict):
        return []
    return reply.get("tool_calls") or []


def _preserve_state(reply, assistant):
    for key in (
        "reasoning_content", "reasoning", "reasoning_details",
        "thinking", "reasoning_text", "tool_plan",
    ):
        if isinstance(reply, dict) and key in reply:
            assistant[key] = reply[key]
    return assistant


def _validate_call(call):
    fn = (call or {}).get("function") or {}
    if fn.get("name") != "protokol_probe":
        return False, "wrong tool name: %s" % fn.get("name")
    try:
        args = json.loads(fn.get("arguments") or "{}")
    except Exception as exc:
        return False, "arguments are not valid JSON: %s" % exc
    if not isinstance(args, dict):
        return False, "arguments are not an object"
    if args.get("echo") != "BASAK_PROTOCOL_OK":
        return False, "echo mismatch: %r" % args.get("echo")
    return True, ""


def _actual_model(provider, client):
    if provider == "nvidia":
        try:
            from brain.nvidia import GPTOSS_MODEL
            return GPTOSS_MODEL
        except Exception:
            pass
    return getattr(client, "model", None) or "unknown"


def _provider_test(brain, provider, client):
    from brain import registry

    sent_mode = registry.ajan_tool_choice(provider)
    model = _actual_model(provider, client)

    gate = getattr(client, "ajan_musait", None)
    if callable(gate):
        try:
            if not gate():
                return {
                    "ok": False, "mode": sent_mode, "model": model,
                    "first": False, "second": False,
                    "error": "provider/model agent capability gate rejected",
                }
        except Exception as exc:
            return {
                "ok": False, "mode": sent_mode, "model": model,
                "first": False, "second": False,
                "error": "agent capability gate error: %s" % _short(exc),
            }

    try:
        first = brain._tek_cagri(
            client,
            provider,
            [{"role": "user", "content": PROMPT}],
            [PROBE_TOOL],
            None,
            None,
            tool_choice="required",
        )
    except Exception as exc:
        return {
            "ok": False, "mode": sent_mode, "model": model,
            "first": False, "second": False,
            "error": "first turn failed: %s" % _short(exc),
        }

    calls = _tool_calls(first)
    if not calls:
        return {
            "ok": False, "mode": sent_mode, "model": model,
            "first": False, "second": False,
            "error": "provider returned no tool call",
        }

    valid = []
    errors = []
    for call in calls:
        ok, error = _validate_call(call)
        if ok:
            valid.append(call)
        else:
            errors.append(error)

    if not valid:
        return {
            "ok": False, "mode": sent_mode, "model": model,
            "first": False, "second": False,
            "error": "; ".join(errors) or "no valid protocol probe call",
        }

    call = valid[0]
    assistant = _preserve_state(
        first,
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [call],
        },
    )

    history = [
        {"role": "user", "content": PROMPT},
        assistant,
        {
            "role": "tool",
            "tool_call_id": call.get("id") or "protocol_probe",
            "name": "protokol_probe",
            "content": json.dumps(
                {"result": "BASAK_PROTOCOL_OK"},
                ensure_ascii=False,
            ),
        },
    ]

    try:
        second = brain._tek_cagri(
            client,
            provider,
            history,
            [PROBE_TOOL],
            None,
            None,
            tool_choice=None,
        )
    except Exception as exc:
        return {
            "ok": False, "mode": sent_mode, "model": model,
            "first": True, "second": False,
            "error": "tool-result follow-up failed: %s" % _short(exc),
        }

    content = ""
    if isinstance(second, dict):
        content = str(second.get("content") or "").strip()

    if not content:
        extra_calls = _tool_calls(second)
        return {
            "ok": False, "mode": sent_mode, "model": model,
            "first": True, "second": False,
            "error": (
                "follow-up produced no final text"
                + ("; returned another tool call" if extra_calls else "")
            ),
        }

    return {
        "ok": True,
        "mode": sent_mode,
        "model": model,
        "first": True,
        "second": True,
        "error": "",
    }


def main():
    from brain import Brain
    from brain import registry

    brain = Brain()
    rows = []
    all_ok = True

    for provider in PROVIDERS:
        creds_ok, missing = _credential_state(provider)
        if not creds_ok:
            rows.append({
                "provider": provider,
                "ok": False,
                "mode": registry.ajan_tool_choice(provider),
                "model": "-",
                "first": False,
                "second": False,
                "error": "missing GitHub secret(s): " + ", ".join(missing),
            })
            all_ok = False
            continue

        client = (getattr(brain, "_providers", {}) or {}).get(provider)
        if client is None:
            rows.append({
                "provider": provider,
                "ok": False,
                "mode": registry.ajan_tool_choice(provider),
                "model": "-",
                "first": False,
                "second": False,
                "error": "adapter did not create a live client",
            })
            all_ok = False
            continue

        result = _provider_test(brain, provider, client)
        result["provider"] = provider
        rows.append(result)
        all_ok = all_ok and result["ok"]

    lines = [
        "# Basak Phase 1 - 8 provider protocol acceptance",
        "",
        "| Provider | Result | Official mode sent | Model | Tool call | Tool result -> final | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {provider} | {result} | {mode} | {model} | {first} | {second} | {note} |".format(
                provider=row["provider"],
                result="PASS" if row["ok"] else "FAIL",
                mode=row["mode"],
                model=_short(row["model"], 70),
                first="PASS" if row["first"] else "FAIL",
                second="PASS" if row["second"] else "FAIL",
                note=_short(row["error"], 180),
            )
        )

    passed = sum(1 for row in rows if row["ok"])
    lines.extend([
        "",
        "## Acceptance",
        "",
        "%d/8 providers passed." % passed,
        "",
        (
            "PHASE 1 ACCEPTED: all 8 providers completed a real tool-call "
            "and tool-result continuation."
            if all_ok else
            "PHASE 1 NOT ACCEPTED: 8/8 live provider protocol proof is required."
        ),
    ])

    report = "\n".join(lines) + "\n"
    print(report)
    Path("provider-protocol-report.md").write_text(
        report, encoding="utf-8"
    )

    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
