import json
from types import SimpleNamespace

import pytest

from chat.platform_agents import _Events


class Control:
    def __init__(self):
        self.lease = SimpleNamespace(run_id='stream-test')
        self.events = []
        self.checks = 0
        self.cancelled = False

    def check_cancelled(self):
        self.checks += 1
        if self.cancelled:
            from chat.platform_runtime import RunCancelled
            raise RunCancelled()

    def event(self, kind, payload):
        self.events.append((kind, payload))


def emit(callback, text):
    callback('BasakUI.parca(' + json.dumps(text) + ')')


def test_many_native_text_fragments_do_not_block_on_one_database_write_each():
    control = Control()
    callback = _Events(control)
    pieces = ['Ş', 'a', 'b', '\n', '"', '🙂'] * 20
    for part in pieces:
        emit(callback, part)
    callback.flush()
    persisted = [data['metin'] for kind, data in control.events
                 if kind == 'chat' and data['tur'] == 'parca']
    assert ''.join(persisted) == ''.join(pieces)
    assert len(persisted) <= 2
    assert control.checks <= 3


def test_tool_boundary_flushes_text_before_activity():
    control = Control()
    callback = _Events(control)
    emit(callback, 'Full output\n')
    callback('BasakUI.toolStatus("Working")')
    assert [p['tur'] for k, p in control.events if k == 'chat'] == ['parca', 'toolStatus']
    assert control.events[0][1]['metin'] == 'Full output\n'


def test_cancel_is_checked_again_during_a_long_stream(monkeypatch):
    import chat.platform_agents as agents
    clock = [100.0]
    monkeypatch.setattr(agents.time, 'monotonic', lambda: clock[0])
    control = Control()
    callback = _Events(control)
    emit(callback, 'first')
    control.cancelled = True
    clock[0] += 1
    from chat.platform_runtime import RunCancelled
    with pytest.raises(RunCancelled):
        emit(callback, 'second')


def test_final_answer_retains_exact_text_and_flush_order():
    control = Control()
    callback = _Events(control)
    emit(callback, 'a\n')
    emit(callback, 'b')
    callback('BasakUI.bitir("a\\nb", "native")')
    assert callback.answer == 'a\nb'
    assert control.events[0] == ('chat', {'tur': 'parca', 'metin': 'a\nb'})


def test_delegation_schema_uses_real_authorized_tool_names_without_mutating_registry():
    from chat.platform_agents import execution_catalog
    from tools import TOOLS
    original = json.dumps(TOOLS,sort_keys=True)
    allowed={'alt_ajan','hesapla'}
    catalog=execution_catalog(allowed)
    delegate=next(t for t in catalog if t['function']['name']=='alt_ajan')
    fields=delegate['function']['parameters']['properties']['isler']['items']['properties']
    assert fields['araclar']['items']['enum']==['alt_ajan','hesapla']
    assert fields['kabul']['items']['properties']['tool']['enum']==['alt_ajan','hesapla']
    assert json.dumps(TOOLS,sort_keys=True)==original
    assert 'hesap' not in fields['araclar']['items']['enum']
