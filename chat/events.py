"""chat/events.py — Canonical Agent Event Stream (P2 Ortak Mimari).

Model çıktılarının ve sağlayıcı yanıtlarının (Groq, Gemini, NVIDIA, GLM, Cohere)
tip-denetimli ortak olay akışıdır.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AgentEvent:
    event_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventThinking(AgentEvent):
    thinking: str = ""
    event_type: str = "thinking"


@dataclass
class EventToolCall(AgentEvent):
    call_id: str = ""
    name: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    raw_args: str = ""
    event_type: str = "tool_call"


@dataclass
class EventToolResult(AgentEvent):
    call_id: str = ""
    name: str = ""
    result: Any = None
    ok: bool = True
    turn: int = 0
    event_type: str = "tool_result"


@dataclass
class EventFinalChunk(AgentEvent):
    chunk: str = ""
    event_type: str = "final_chunk"


@dataclass
class EventComplete(AgentEvent):
    final_text: str = ""
    provider: str = ""
    finish_reason: str = ""
    event_type: str = "complete"


def parse_tool_call(raw_call: dict[str, Any]) -> EventToolCall:
    """Ham tool_call dict yapısını EventToolCall nesnesine dönüştürür."""
    call_id = str(raw_call.get("id") or "")
    fn = raw_call.get("function") or {}
    name = str(fn.get("name") or raw_call.get("name") or "")
    raw_args = fn.get("arguments") or raw_call.get("arguments") or "{}"
    
    args = {}
    if isinstance(raw_args, dict):
        args = raw_args
        raw_args_str = json.dumps(raw_args, ensure_ascii=False)
    else:
        raw_args_str = str(raw_args)
        try:
            parsed = json.loads(raw_args_str)
            if isinstance(parsed, dict):
                args = parsed
        except (ValueError, TypeError):
            args = {}

    return EventToolCall(
        call_id=call_id,
        name=name,
        args=args,
        raw_args=raw_args_str,
    )


def response_to_events(response: dict[str, Any], provider: str = "") -> list[AgentEvent]:
    """Modelden dönen ham yanıt dict'ini canonical olay listesine ayrıştırır."""
    events: list[AgentEvent] = []
    if not isinstance(response, dict):
        return events

    # Düşünce (thinking / reasoning)
    for t_key in ("thinking", "reasoning", "reasoning_content"):
        val = response.get(t_key)
        if val:
            events.append(EventThinking(thinking=str(val)))
            break

    # Tool calls
    tool_calls = response.get("tool_calls") or []
    if isinstance(tool_calls, list):
        for tc in tool_calls:
            if isinstance(tc, dict):
                events.append(parse_tool_call(tc))

    # İçerik
    content = str(response.get("content") or "")
    if content:
        events.append(EventFinalChunk(chunk=content))

    events.append(EventComplete(
        final_text=content,
        provider=str(provider or response.get("provider") or ""),
        finish_reason=str(response.get("_finish_reason") or ""),
    ))

    return events
