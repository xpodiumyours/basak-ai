"""tests/test_profesyonel_mimari.py — Profesyonel mimari kabul testleri.

FAZ 1 (Events), FAZ 2 (Evidence) ve FAZ 3 (Checkpoints) doğrulama testleri.
"""

import pytest
from chat.events import (
    EventThinking, EventToolCall, EventToolResult, EventFinalChunk,
    EventComplete, parse_tool_call, response_to_events
)
from chat.evidence import EvidenceStore
from chat.agent_runtime import AgentRunState
from chat.checkpoints import save_checkpoint, load_checkpoint, delete_checkpoint


def test_events_stream_and_parsing():
    raw_call = {
        "id": "call_123",
        "type": "function",
        "function": {
            "name": "web_search",
            "arguments": "{\"query\": \"ankara hava durumu\"}",
        }
    }
    tc = parse_tool_call(raw_call)
    assert isinstance(tc, EventToolCall)
    assert tc.name == "web_search"
    assert tc.args.get("query") == "ankara hava durumu"

    response = {
        "content": "Ankara güneşli.",
        "thinking": "Hava durumunu kontrol ettim.",
        "tool_calls": [raw_call],
        "_finish_reason": "stop"
    }
    events = response_to_events(response, provider="groq")
    types = [e.event_type for e in events]
    assert "thinking" in types
    assert "tool_call" in types
    assert "final_chunk" in types
    assert "complete" in types


def test_evidence_store_truthfulness():
    store = EvidenceStore()
    store.add("url", "https://ornek.com", tool="sayfa_oku", call_id="c1", snippet="bilgi")
    # Ayni URL tekrar eklenmemeli
    store.add("url", "https://ornek.com", tool="sayfa_oku", call_id="c1")
    assert store.count() == 1

    store.add("task", "task_42", tool="add_task", call_id="c2", snippet="gorev acildi")
    assert store.count() == 2

    snap = store.snapshot()
    assert len(snap) == 2
    assert snap[0]["kind"] == "url"
    assert snap[1]["kind"] == "task"


def test_agent_runtime_with_evidence_and_checkpoint(tmp_path, monkeypatch):
    from chat import kimlik
    monkeypatch.setattr(kimlik, "kullanici_koku", lambda: str(tmp_path))

    state = AgentRunState(run_id="run_prof_01")
    state.record_evidence("file", "docs/PLAN.md", tool="read_file", call_id="c1")
    state.evidence_add("https://site.com", tool="sayfa_oku", call_id="c2")

    assert state.evidence_store.count() == 2
    assert len(state.evidence) == 1

    # Mola / Pause durumunda checkpoint tetiklenmeli
    state.pause(reason="sure")
    assert state.status == "paused"

    loaded = load_checkpoint("run_prof_01")
    assert loaded is not None
    assert loaded["run_id"] == "run_prof_01"
    assert loaded["status"] == "paused"

    delete_checkpoint("run_prof_01")
    assert load_checkpoint("run_prof_01") is None
