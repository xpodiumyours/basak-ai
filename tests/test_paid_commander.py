"""Capped OpenRouter commander must never expand free-agent access or spend."""
from types import SimpleNamespace

import pytest


MODEL = 'xiaomi/mimo-v2.5-pro'


def enable(monkeypatch):
    monkeypatch.setenv('BASAK_PAID_COMMANDER_ENABLED', 'true')
    monkeypatch.setenv('BASAK_KOMUTAN_MODEL', 'openrouter:' + MODEL)
    monkeypatch.setenv('BASAK_PAID_COMMANDER_OWNER_ID', 'owner-123')


def test_paid_commander_is_explicitly_owner_scoped(monkeypatch):
    from brain.paid_commander import authorized_commander, configured_model
    enable(monkeypatch)
    assert configured_model() == MODEL
    valid = {'user_id': 'owner-123', 'kind': 'agent', 'parent_id': None}
    assert authorized_commander(valid)
    assert not authorized_commander({**valid, 'kind': 'chat'})
    assert not authorized_commander({**valid, 'parent_id': 'parent'})
    assert not authorized_commander({**valid, 'user_id': 'other'})
    monkeypatch.delenv('BASAK_PAID_COMMANDER_OWNER_ID')
    assert not authorized_commander(valid)
    monkeypatch.setenv('BASAK_PAID_COMMANDER_ENABLED', 'false')
    assert configured_model() == ''
    assert not authorized_commander(valid)


@pytest.mark.parametrize('limit,reset,remaining,expected', [
    (3.0, 'monthly', 3.0, True),
    (2.0, 'monthly', 1.0, True),
    (3.01, 'monthly', 3.01, False),
    (3.0, 'daily', 3.0, False),
    (None, 'monthly', 3.0, False),
    (3.0, 'monthly', 0, False),
])
def test_provider_enforced_budget_is_required(
        monkeypatch, limit, reset, remaining, expected):
    from brain.paid_commander import capped_key
    monkeypatch.setenv('BASAK_PAID_OPENROUTER_API_KEY', 'test-secret')
    seen = []

    def fake_get(url, **kwargs):
        seen.append((url, kwargs))
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {'data': {
                'limit': limit, 'limit_reset': reset,
                'limit_remaining': remaining, 'is_management_key': False}})
    monkeypatch.setattr('brain.paid_commander.httpx.get', fake_get)
    assert bool(capped_key()) is expected
    assert seen[0][0].endswith('/key')
    assert seen[0][1]['follow_redirects'] is False


def test_paid_model_selection_keeps_free_workers(monkeypatch):
    from tools.platform import selection
    enable(monkeypatch)
    brain = SimpleNamespace(_bulut_zinciri=lambda tools=False: [])
    assert selection(brain, 'komutan') == ('openrouter_paid', MODEL)
    assert selection(brain, 'isci') == ('', '')
    assert selection(brain, 'primary') == ('', '')


def test_paid_prepend_only_inside_explicit_role_and_preserves_fallback(monkeypatch):
    from brain.model_havuzu import model_selection
    from brain.paid_commander import prepend_commander
    enable(monkeypatch)
    monkeypatch.setenv('BASAK_PAID_OPENROUTER_API_KEY', 'test-secret')
    monkeypatch.setattr('brain.paid_commander.capped_key', lambda: 'test-secret')
    monkeypatch.setattr('brain.openrouter.OpenRouterClient',
                        lambda key, model: SimpleNamespace(
                            model=model, musait=lambda: True))
    free = [('groq', object()), ('openrouter', object())]
    assert prepend_commander(free) is free
    with model_selection('groq', ''):
        assert prepend_commander(free) is free
    with model_selection('openrouter_paid', MODEL):
        chain = prepend_commander(free)
        assert [name for name, _ in chain] == [
            'openrouter_paid', 'groq', 'openrouter']
        assert chain[0][1].model == MODEL
    monkeypatch.setattr('brain.paid_commander.capped_key', lambda: '')
    with model_selection('openrouter_paid', MODEL):
        assert prepend_commander(free) is free


def test_paid_requires_valid_provider_model_identifier(monkeypatch):
    from brain.paid_commander import configured_model
    enable(monkeypatch)
    monkeypatch.setenv('BASAK_KOMUTAN_MODEL', 'openrouter:openrouter/free')
    assert configured_model() == ''
    monkeypatch.setenv('BASAK_KOMUTAN_MODEL', 'openrouter:foo:free')
    assert configured_model() == ''
