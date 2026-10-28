"""Authenticated execution envelope shared by core, jobs, and tools.

Kimi's isolated subagent context is a task boundary, not a new model provider:
https://www.kimi.com/code/docs/en/kimi-code-cli/customization/agents.html
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
import re

_ACTIVE = ContextVar('basak_execution', default=None)
_ID = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$')


@dataclass(frozen=True)
class ExecutionContext:
    user_id: str
    workspace_id: str
    run_id: str
    parent_run_id: str = ''
    workspace_root: str = ''
    tool_call_id: str = ''
    allowed_tools: frozenset | None = None
    control: object = field(default=None, compare=False, repr=False)
    brain: object = field(default=None, compare=False, repr=False)
    # inline: aynı istek içinde koşan ordu zarfı (chat.inline_ordu).
    # Kalıcı hesap doğrulaması yalnız kalıcı işçi yolu için geçerlidir;
    # istek içi alt ajan hesap/kayıt gerektirmez.
    inline: bool = False

    def __post_init__(self):
        for value in (self.user_id, self.workspace_id, self.run_id):
            if not isinstance(value, str) or not _ID.fullmatch(value):
                raise ValueError('Kimlik, calisma alani ve kosu kimligi zorunlu')
        if not self.inline and (
                self.user_id.startswith(('anon-', 'anonim-'))
                or re.fullmatch(r'p[0-9a-f]{16}', self.user_id)):
            raise ValueError('Bu islem kalici hesap oturumu gerektirir')
        if self.workspace_root:
            object.__setattr__(self, 'workspace_root', str(Path(self.workspace_root).resolve()))


def current():
    return _ACTIVE.get()


def require():
    ctx = current()
    if ctx is None:
        raise PermissionError('Bu islem hesaba bagli gorev calisma alani gerektirir')
    return ctx


@contextmanager
def bound(context):
    """Explicitly bind the envelope at *each* queue/thread boundary."""
    from chat.kimlik import _ctx_kullanici
    token = _ACTIVE.set(context)
    principal = _ctx_kullanici.set(context.user_id)
    try:
        yield context
    finally:
        _ctx_kullanici.reset(principal)
        _ACTIVE.reset(token)


def workspace_path(path):
    ctx = require()
    if not ctx.workspace_root:
        raise PermissionError('Bu gorevde dosya calisma alani acilmamis')
    root = Path(ctx.workspace_root).resolve()
    candidate = Path(path)
    candidate = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not candidate.is_relative_to(root):
        raise PermissionError('Dosya bu kullanicinin calisma alaninin disinda')
    return candidate
