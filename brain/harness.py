"""Başak hafif harness v1.

İki karar katmanı vardır:
1) TaskProfile: bu turda gerçekten ne gerekiyor?
2) ModelFamily: çağrılacak gerçek model hangi ailede?

Varsayılan LEGACY'dir. Yalnız yüksek güvenli chat/read turları hafifletilir.
Bu modül provider sırası, izin/onay politikası veya tool executor davranışını
değiştirmez.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import logging
import re

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TaskProfile:
    name: str
    tool_names: tuple[str, ...] = ()
    stream_allowed: bool = True
    compact_context: bool = False
    active: bool = False


@dataclass(frozen=True)
class HarnessSpec:
    task: str
    family: str
    max_tools: int
    note: str = ""
    active: bool = False


LEGACY = TaskProfile("legacy", active=False)
CHAT_LITE = TaskProfile(
    "chat-lite", tool_names=(), stream_allowed=True,
    compact_context=True, active=True,
)

_CURRENT_PROFILE: ContextVar[TaskProfile | None] = ContextVar(
    "basak_task_profile", default=None
)

_FILE_RE = re.compile(
    r"(?:[a-z]:[\\/][^\s]+|(?:^|\s)/(?:[^\s/]+/)*[^\s]+|"
    r"\.(?:md|txt|json|py|yaml|yml|csv|log)\b)",
    re.IGNORECASE,
)
_SMALL_LLAMA_RE = re.compile(r"llama[^\n]*(?:3b|7b|8b)", re.IGNORECASE)


def _has(text: str, phrases) -> bool:
    return any(p in text for p in phrases)


def task_profile_for(text: str) -> TaskProfile:
    """Mesajı yalnız yüksek güvenli iki hafif profile ayırır.

    Belirsizlikte LEGACY döner. Böylece v1 bilinmeyen işlere yeni davranış
    dayatmaz.
    """
    t = (text or "").strip().casefold()
    if not t:
        return LEGACY

    tools: list[str] = []

    # Açık dosya okuma.
    file_phrases = (
        "dosyayi oku", "dosyayı oku", "dosya icerigi", "dosya içeriği",
        "dosyanin icinde ne var", "dosyanın içinde ne var",
        "bu dosyayi ac", "bu dosyayı aç", "icinde ne yaziyor",
        "içinde ne yazıyor", "goster su dosyayi", "göster şu dosyayı",
    )
    if _has(t, file_phrases) or (
        _FILE_RE.search(t) and _has(t, ("oku", "göster", "goster", "içerik", "icerik"))
    ):
        tools.append("read_file")

    # Açık klasör listeleme.
    if _has(t, (
        "klasoru listele", "klasörü listele", "dosyalari listele",
        "dosyaları listele", "klasordeki dosyalar", "klasördeki dosyalar",
        "hangi dosyalar var", "klasorde ne var", "klasörde ne var",
    )):
        tools.append("list_files")

    # Açık repo/doküman/metadata okuması.
    if _has(t, (
        "son commit", "repo durumu", "kod durumu", "hangi dal",
        "hangi branch", "git durumu", "diff ne durumda",
    )):
        tools.append("git_durum")
    if _has(t, (
        "planda ne", "belgede ne", "listede ne yaziyor", "listede ne yazıyor",
        "dokumanda", "dokümanda", "gorev listesinde", "görev listesinde",
        "notlarda", "defterde ne", "rehberde",
    )):
        tools.append("belge_ara")
    if _has(t, (
        "dosya boyutu", "dosya tarihi", "dosya bilgisi",
        "kac kb", "kaç kb", "kac mb", "kaç mb",
        "ne zaman degisti", "ne zaman değişti",
    )):
        tools.append("dosya_bilgi")

    if tools:
        # v1: Groq tavsiyesindeki dar yüzeye uygun olarak en fazla 3 okuma aracı.
        unique = tuple(dict.fromkeys(tools))[:3]
        return TaskProfile(
            "read-lite", tool_names=unique, stream_allowed=False,
            compact_context=True, active=True,
        )

    # v1'de chat-lite yalnız açık küçük sohbet kalıplarıdır. Başka her şey
    # LEGACY: kapsamı bilmediğimiz işi hafif harness'a zorlamayız.
    chat_phrases = (
        "merhaba", "selam", "günaydın", "gunaydin", "iyi akşamlar",
        "iyi aksamlar", "iyi geceler", "nasılsın", "nasilsin", "naber",
        "ne haber", "teşekkür", "tesekkur", "sağ ol", "sag ol",
    )
    if _has(t, chat_phrases):
        return CHAT_LITE

    return LEGACY


@contextmanager
def harness_scope(text: str):
    """Bir kullanıcı turu boyunca deterministik TaskProfile'ı sabitler."""
    token = _CURRENT_PROFILE.set(task_profile_for(text))
    try:
        yield _CURRENT_PROFILE.get()
    finally:
        _CURRENT_PROFILE.reset(token)


def current_profile() -> TaskProfile:
    return _CURRENT_PROFILE.get() or LEGACY


def resolve_model_family(provider: str, model_id: str | None) -> str:
    """Provider adından değil gerçek model id'sinden aile çözer."""
    p = (provider or "").casefold()
    m = (model_id or "").casefold()
    if "gpt-oss" in m:
        return "gpt-oss"
    if "glm-4.5-flash" in m or (p == "glm" and "flash" in m):
        return "glm-flash"
    if "llama-3.2-3b" in m or _SMALL_LLAMA_RE.search(m):
        return "llama-small"
    return "generic-lite"


def harness_spec(profile: TaskProfile, provider: str, model_id: str | None) -> HarnessSpec:
    if not profile.active:
        return HarnessSpec(profile.name, "legacy", 99, active=False)

    family = resolve_model_family(provider, model_id)
    if family == "llama-small":
        note = (
            "Bu tur yalnız verilen işi yap. "
            "Dosya/repo bilgisi gerekiyorsa yalnız verilen okuma araçlarını kullan; "
            "araç çıktısı olmadan somut içerik uydurma."
            if profile.name == "read-lite"
            else "Bu tur doğal ve kısa sohbet et; araç çağırma."
        )
        return HarnessSpec(profile.name, family, 2, note, True)
    if family in ("gpt-oss", "glm-flash"):
        return HarnessSpec(profile.name, family, 4, "", True)
    return HarnessSpec(profile.name, family, 3, "", True)


def _tool_name(schema: dict) -> str:
    try:
        return str(schema["function"]["name"])
    except (KeyError, TypeError):
        return ""


def _compact_system_messages(messages: list[dict], profile: TaskProfile,
                             note: str = "") -> list[dict]:
    if not profile.active or not profile.compact_context:
        return list(messages)

    out: list[dict] = []
    for message in messages:
        role = message.get("role")
        content = str(message.get("content") or "")

        if role == "system":
            # Hafif v1'de tüm kalıcı profil ve episodik hafıza dökümü taşınmaz.
            if content.startswith("Hafızadan:\n"):
                continue
            if content.startswith("Casper hakkinda KALICI bilinenler"):
                continue

            # flow.py bugün KISILIK + TOOL + DÜRÜSTLÜK + BİÇİM bloklarını
            # tek system mesajında birleştiriyor. Chat-lite'da araç bloğundan
            # sonrasını kes; read-lite'da yalnız biçim bloğunu kes.
            if profile.name == "chat-lite":
                marker = "\nELİNDEKİ ARAÇLAR:"
                if marker in content:
                    content = content.split(marker, 1)[0].rstrip()
            elif profile.name == "read-lite":
                marker = "\nCEVAP BiCiMi:"
                if marker in content:
                    content = content.split(marker, 1)[0].rstrip()

        if content:
            out.append({**message, "content": content})

    if note:
        # Model-aile notunu kullanıcı mesajından önce tek kısa system mesajı yap.
        insert_at = 0
        while insert_at < len(out) and out[insert_at].get("role") == "system":
            insert_at += 1
        out.insert(insert_at, {"role": "system", "content": note})

    return out


def prepare_call(messages: list[dict], tools: list[dict] | None,
                 provider: str, model_id: str | None):
    """Gerçek provider çağrısından hemen önce mesaj/tool yüzeyini hazırlar."""
    profile = current_profile()
    spec = harness_spec(profile, provider, model_id)
    if not spec.active:
        return messages, tools, spec

    prepared_messages = _compact_system_messages(messages, profile, spec.note)

    if profile.name == "chat-lite":
        prepared_tools = None
    else:
        allowed = set(profile.tool_names)
        prepared_tools = [
            schema for schema in (tools or [])
            if _tool_name(schema) in allowed
        ][:spec.max_tools]
        if not prepared_tools:
            prepared_tools = None

    return prepared_messages, prepared_tools, spec


def prepare_stream(messages: list[dict], model_id: str | None,
                   provider: str = ""):
    """Streaming için tool gerekmeyen hafif mesaj yüzeyi üretir."""
    profile = current_profile()
    spec = harness_spec(profile, provider, model_id)
    if not spec.active:
        return messages, profile.stream_allowed, spec
    prepared = _compact_system_messages(messages, profile, spec.note)
    return prepared, profile.stream_allowed, spec


class HarnessProviderProxy:
    """Bulut provider client'ını model-family harness ile saran şeffaf proxy."""

    def __init__(self, provider: str, inner):
        self._harness_provider = provider
        self._harness_inner = inner

    def __getattr__(self, name):
        return getattr(self._harness_inner, name)

    def cevapla(self, messages, tools=None, model=None, yapi=None, **kwargs):
        # `model` imzada açık tutulur: Brain._tek_cagri Groq override desteğini
        # inspect.signature ile keşfediyor. Proxy bu sözleşmeyi gizlememeli.
        model_id = model or getattr(self._harness_inner, "model", None)
        prepared_messages, prepared_tools, spec = prepare_call(
            messages, tools, self._harness_provider, model_id
        )
        if spec.active:
            logger.info(
                "Harness task=%s family=%s provider=%s tools=%d",
                spec.task, spec.family, self._harness_provider,
                len(prepared_tools or []),
            )

        call_kwargs = dict(kwargs)
        if model is not None:
            call_kwargs["model"] = model
        if yapi is not None:
            call_kwargs["yapi"] = yapi
        return self._harness_inner.cevapla(
            prepared_messages, tools=prepared_tools, **call_kwargs
        )


def wrap_provider(provider: str, client):
    # Ollama'nın imzası cevapla(messages, model, tools...) olduğu için cloud
    # proxy sözleşmesine sokulmaz. Yerel streaming ayrı prepare_stream kullanır.
    if provider == "yerel":
        return client
    if client is None or isinstance(client, HarnessProviderProxy):
        return client
    return HarnessProviderProxy(provider, client)
