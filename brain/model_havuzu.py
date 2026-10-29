"""Mevcut SDK'larda ucretsiz model yedeklemesi; ek sunucu veya paket yok.

Katalog yalniz adaydir. Basariyi gercek API yaniti belirler. Kullanici
metni incelenmez; native yanit, arac imzalari ve akisin parcasi korunur.
"""

import json
import hashlib
import threading
import time
from contextvars import ContextVar
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

_SELECTION = ContextVar('basak_model_selection', default=None)
_AVAILABILITY = {}
_AVAILABILITY_LOCK = threading.RLock()


@contextmanager
def model_selection(provider, model):
    token = _SELECTION.set((provider, model))
    try:
        yield
    finally:
        _SELECTION.reset(token)


def katalog():
    return json.loads(Path(__file__).with_name("ucretsiz_modeller.json").read_text(encoding="utf-8"))["saglayicilar"]


def _yeniden_denenebilir(hata):
    status = getattr(hata, "status_code", None)
    if status is None:
        status = getattr(getattr(hata, "response", None), "status_code", None)
    if status in (401, 402, 403):
        return False  # Ortak anahtar/bakiye hatasini ayni hesapta tekrarlama.
    return status in (404, 408, 409, 410, 429) or (
        isinstance(status, int) and status >= 500
    ) or isinstance(hata, (TimeoutError, ConnectionError)) or type(hata).__name__ in (
        "APITimeoutError", "APIConnectionError", "ReadTimeout", "ConnectError",
    )


class _Chat:
    def __init__(self, havuz):
        self._havuz = havuz
        original = havuz._sdk.chat
        if hasattr(original, "completions"):
            self.completions = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        return self._havuz.cagir(self._havuz._sdk.chat.completions.create, kwargs)

    def __call__(self, **kwargs):
        return self._havuz.cagir(self._havuz._sdk.chat, kwargs)

    def __getattr__(self, name):
        return getattr(self._havuz._sdk.chat, name)


class ModelHavuzuSDK:
    def __init__(self, sdk, modeller, ortak_kota=False, provider='', availability=None):
        self._sdk = sdk
        self.modeller = tuple(modeller)
        self.ortak_kota = ortak_kota
        self.provider = provider
        if availability is None:
            # Share model cooldowns across this process's provider clients,
            # keeping independent accounts and endpoints separate.
            key = getattr(sdk, 'api_key', None)
            if provider and isinstance(key, str) and key:
                scope = (provider, str(getattr(sdk, 'base_url', '')),
                         hashlib.sha256(key.encode()).hexdigest())
                with _AVAILABILITY_LOCK:
                    availability = _AVAILABILITY.setdefault(scope, {})
            else:
                availability = {}
        self._availability = availability
        self._son_model = ContextVar("basak_son_model", default=None)
        self.chat = _Chat(self)

    @property
    def son_model(self):
        return self._son_model.get()

    def __getattr__(self, name):
        return getattr(self._sdk, name)

    def with_options(self, **kwargs):
        return ModelHavuzuSDK(self._sdk.with_options(**kwargs), self.modeller,
                             ortak_kota=self.ortak_kota, provider=self.provider,
                             availability=self._availability)

    def _note_failure(self, model, error):
        if not _yeniden_denenebilir(error):
            return
        from brain.brain import _bekleme_suresi, _COOLDOWN_SURE
        until = time.monotonic() + (_bekleme_suresi(error) or _COOLDOWN_SURE)
        with _AVAILABILITY_LOCK:
            self._availability[model] = (until, error)

    def adaylar(self, kwargs):
        aracli = bool(kwargs.get("tools"))
        uygun = [m["id"] for m in self.modeller if not aracli or m["tools"]]
        selection = _SELECTION.get()
        exact = selection and selection[0] == self.provider and selection[1]
        istenen = selection[1] if exact else kwargs.get("model")
        if exact and istenen not in uygun:
            raise ValueError('Secilen model arac protokolu icin katalogda yok')
        if istenen in uygun:
            uygun.remove(istenen)
            uygun.insert(0, istenen)
        if not uygun:
            raise RuntimeError("Ucretsiz katalogda bu protokole uygun model yok")
        with _AVAILABILITY_LOCK:
            available = [m for m in uygun if
                         self._availability.get(m, (0, None))[0] <= time.monotonic()]
            if not available:
                # Return the real provider error to the existing cross-provider
                # fallback, instead of sleeping or probing every exhausted model.
                raise self._availability[uygun[0]][1]
        return available

    def cagir(self, fonksiyon, kwargs):
        if kwargs.get("stream"):
            return self._akis(fonksiyon, kwargs)
        for model in self.adaylar(kwargs):
            try:
                yanit = fonksiyon(**dict(kwargs, model=model))
            except Exception as hata:
                self._note_failure(model, hata)
                if self.ortak_kota and getattr(hata, "status_code", None) == 429:
                    raise
                if not _yeniden_denenebilir(hata):
                    raise
                son_hata = hata
                continue
            self._son_model.set(model)
            return yanit
        raise son_hata

    def _akis(self, fonksiyon, kwargs):
        for model in self.adaylar(kwargs):
            akis = None
            basladi = False
            try:
                akis = fonksiyon(**dict(kwargs, model=model))
                for parca in akis:
                    # Tek parca ile bile iki modelin yaniti birlestirilmez.
                    basladi = True
                    self._son_model.set(model)
                    yield parca
                if not basladi:
                    raise RuntimeError("Model bos akis dondurdu")
                return
            except Exception as hata:
                self._note_failure(model, hata)
                if self.ortak_kota and getattr(hata, "status_code", None) == 429:
                    raise
                if basladi or (str(hata) != "Model bos akis dondurdu"
                               and not _yeniden_denenebilir(hata)):
                    raise
                son_hata = hata
            finally:
                kapat = getattr(akis, "close", None)
                if callable(kapat):
                    kapat()
        raise son_hata


def bagla(ad, istemci, ayar):
    """Native SDK korunur; yalniz katalogdaki mevcut saglayicilar genisler."""
    modeller = katalog().get(ad)
    sdk = getattr(istemci, "client", None)
    if not modeller or sdk is None or not hasattr(sdk, "chat"):
        return istemci
    import os
    env = {"groq": "GROQ_MODEL", "nvidia": "NVIDIA_MODEL", "gemini": "GEMINI_MODEL",
           "cloudflare": "CLOUDFLARE_MODEL", "cohere": "COHERE_MODEL",
           "mistral": "MISTRAL_MODEL", "glm": "ZAI_MODEL"}[ad]
    alan = "glm_model" if ad == "glm" else ad + "_model"
    acik_model = os.environ.get(env) or (ayar or {}).get(alan)
    # Acik model secimi korunur. Otomatik varsayilan, katalogun ilk adayidir.
    if acik_model:
        if acik_model not in {m["id"] for m in modeller}:
            return istemci
        istemci.model = acik_model
    else:
        istemci.model = modeller[0]["id"]
    istemci.model_havuzu = modeller
    # This router already performs model/provider failover. Avoid the SDK's
    # nested retries delaying each attempt before the next model is reached.
    if hasattr(sdk.chat, 'completions') and callable(getattr(sdk, 'with_options', None)):
        sdk = sdk.with_options(max_retries=0)
    istemci.client = ModelHavuzuSDK(
        sdk, modeller, ortak_kota=ad in ("mistral", "cohere", "cloudflare"), provider=ad)
    return istemci
