"""brain/brain.py — Basak'in ana beyin sinifi.

Varsayilan: Groq (ucretsiz, hizli).
Yerel Ollama sadece Groq calismazsa fallback olarak kullanilir.
"""

import json
import logging
import os
import time
from datetime import datetime

from brain.groq import GroqClient, MODELLER
from brain.model_family import coz as _aile_coz
from brain.ollama import OLLAMA_URL
from brain.stats import model_stats_al
from brain import secici, registry

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(BASE, "ayarlar.json")
AUDIT_DOSYASI = os.path.join(BASE, "data", "audit", "audit.log")


def _audit(mesaj: str):
    """P1 audit kaydi: her beyin cagrisi data/audit/audit.log'a islenir.

    Kayit icerigi: zaman, hangi kaynak, sure, hata varsa nedeni.
    Bu log modelden etkilenmez — Policy Core prensibi.
    """
    try:
        os.makedirs(os.path.dirname(AUDIT_DOSYASI), exist_ok=True)
        zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(AUDIT_DOSYASI, "a", encoding="utf-8") as f:
            f.write(f"{zaman} | {mesaj}\n")
    except OSError as e:
        logger.warning("Audit yazilamadi: %s", e)


def _ayar_yukle() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _ayar_kaydet(veri: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error("Ayarlar kaydedilemedi: %s", e)


# FAZ 1.1: yapi sozlesmesi destegi self-healing kesfi — saglayici bir kez
# yapi'yi 400/invalid_request_error ile reddederse burada False isaretlenir
# ve sonraki cagrilarda yapi hic gonderilmez (registry karti degismez).
_YAPI_DENEME = {}

# QWEN BEKLEMEDE (2026-09-09, tam tespit): hesap etkinlesmesi
# bitene kadar (403 hatasi) Qwen zincire KATILMAZ. Casper
# etkinlestirince False yapilir, kart registry'de hazir bekler.
_QWEN_BEKLEMEDE = True

# COOLDOWN: rate-limit (429) gelince provider gecici olarak atla
import time as _time_mod
_COOLDOWN = {}  # {ad: bitis_zamani}
_COOLDOWN_SURE = 120  # 2 dakika

# Zaman asimi cooldown'u (2026-09-11): 429 kadar agir degil; saglayici
# bir sonraki istekte geri gelebilir. 60 sn yeter.
_ZAMAN_ASIMI_COOLDOWN = 60

# Erisim engeli cooldown'u (2026-09-12): 403/401/yetkisiz/paid-plan
# dakikalarda iyilesmez — her turda ölü saglayiciyi yeniden denemek
# kota ve süre yakar. 1 saat pas geç; anahtar/model degisince temizlenir.
_ERISIM_COOLDOWN = 3600


def _erisim_engeli_mi(hata):
    """Hata kalici erisim engeli mi? (403/401/paid-plan/gecersiz anahtar)."""
    s = str(hata).lower()
    return any(k in s for k in (
        "403", "401", "forbidden", "denied", "unauthorized",
        "api key", "invalid_key", "authentication",
        "requires paid", "paid plan", "permission"))

def _cooldown_kaldi(ad):
    bitis = _COOLDOWN.get(ad, 0)
    kalan = bitis - _time_mod.time()
    return max(0, kalan)

def _cooldown_ekle(ad, sure=None):
    _COOLDOWN[ad] = _time_mod.time() + (sure or _COOLDOWN_SURE)

def _rate_limit_mi(hata):
    s = str(hata).lower()
    return any(k in s for k in ("429", "rate", "limit", "too many", "quota"))


def _zaman_asimi_mi(hata):
    """Hata zaman asimi mi? (2026-09-11)

    GLM 3 sn'lik zaman asimi duvarina surekli carpiyordu: her istekte
    yeniden denenip patliyor, zincir yavasiyor, yerel modele dusiliyordu.
    Zaman asimi GECICI bir durumdur (429 gibi) — kisa cooldown alir.
    """
    s = str(hata).lower()
    return any(k in s for k in (
        "timed out", "timeout", "time out", "read operation",
        "connection reset", "connection aborted"))



def _yapi_desteksiz_mi(hata) -> bool:
    """Hata, yapi/response_format desteklenmeyen istekten mi kaynaklaniyor?

    Mesajinda response_format/format/json gecen VE bad-request turunde
    (400 / invalid_request_error / bad request) istisnalar sayilir.
    """
    s = str(hata).lower()
    if not any(k in s for k in ("response_format", "format", "json")):
        return False
    return any(k in s for k in ("400", "invalid_request_error", "bad request"))


class Brain:
    def __init__(self):
        ayar = _ayar_yukle()

        # ── ADAPTER PATTERN: adapter'ları otomatik keşfet ve başlat ──
        from brain.adapters.registry import discover_all, create_providers
        self._adaptors = discover_all()
        self._providers = create_providers(ayar, self._adaptors)

        # Backward compatibility: eski attribute isimleri korunur
        self.groq_key = (
            os.environ.get("GROQ_API_KEY") or ayar.get("groq_key") or ""
        )
        self.groq_model = ayar.get("groq_model", MODELLER["varsayilan"])
        self._groq = self._providers.get("groq")
        self._ollama = self._providers.get("yerel")
        self._gemini = self._providers.get("gemini")
        self._glm = self._providers.get("glm")
        self._nvidia = self._providers.get("nvidia")
        self._kilo = self._providers.get("kilo")
        self._openrouter = self._providers.get("openrouter")
        self._cloudflare = self._providers.get("cloudflare")
        self._cohere = self._providers.get("cohere")
        self._qwen = self._providers.get("qwen")
        # 2026-09-10: kullanicinin ozel (ucretli) saglayicisi. Anahtar
        # yoksa None'dir — bedava kurulum etkilenmez.
        self._genel = self._providers.get("genel")

    def _bulut_zinciri(self) -> list:
        """Musait bulut istemcilerini toplar: [(ad, istemci)].

        DIKKAT: Bu listenin sirasi ONCELIK SIRASI DEGILDIR. Gercek
        sirayi secici.sec() belirler (registry.VARSAYILAN_SIRA temel;
        gorev tipi + karne yeniden dizer). Buradaki sira yalnizca
        secici'ye mevcut havuzi vermek ve 'tercih'siz eski cagilarda
        yedek siralamak icindir. Son care her zaman Ollama (yerel).
        """
        zincir = []
        if self._groq is not None and self._groq.musait():
            zincir.append(("groq", self._groq))
        if self._glm is not None and self._glm.musait():
            zincir.append(("glm", self._glm))
        if self._cloudflare is not None and self._cloudflare.musait():
            zincir.append(("cloudflare", self._cloudflare))
        if self._cohere is not None and self._cohere.musait():
            zincir.append(("cohere", self._cohere))
        if self._nvidia is not None and self._nvidia.musait():
            zincir.append(("nvidia", self._nvidia))
        if self._kilo is not None and self._kilo.musait():
            zincir.append(("kilo", self._kilo))
        if self._openrouter is not None and self._openrouter.musait():
            zincir.append(("openrouter", self._openrouter))
        if self._qwen is not None and self._qwen.musait():
            # QWEN BEKLEMEDE disinda normal katilim
            if not _QWEN_BEKLEMEDE:
                zincir.append(("qwen", self._qwen))
        if self._gemini is not None and self._gemini.musait():
            zincir.append(("gemini", self._gemini))
        # 2026-09-10: ozel saglayici EN SONDA — bedavalar once denenir,
        # parali anahtar takilinca davranis degismez, yedek cogalir.
        # getattr: elle kurulan Brain nesnelerinde de patlamaz.
        _genel = getattr(self, "_genel", None)
        if _genel is not None and _genel.musait():
            zincir.append(("genel", _genel))
        return zincir

    def bulut_musait(self) -> bool:
        # Herhangi bir bulut saglayici hazirsa True. Ollama son caredir.
        return bool(self._bulut_zinciri())

    def anahtar_ayarla(self, key: str):
        self.groq_key = key.strip()
        ayar = _ayar_yukle()
        ayar["groq_key"] = self.groq_key
        _ayar_kaydet(ayar)
        # 2026-09-12: anahtar degisimi erisim engelini iyilestirebilir —
        # ölü isaretli cooldown'lar temizlenir.
        _COOLDOWN.clear()
        if self.groq_key:
            try:
                self._groq = GroqClient(self.groq_key, self.groq_model)
            except ValueError:
                self._groq = None
        else:
            self._groq = None

    def groq_model_ayarla(self, model_adi: str):
        if model_adi in MODELLER:
            self.groq_model = MODELLER[model_adi]
        else:
            self.groq_model = model_adi
        ayar = _ayar_yukle()
        ayar["groq_model"] = self.groq_model
        _ayar_kaydet(ayar)
        # 2026-09-12: model degisimi erisim tablosunu yeniler.
        _COOLDOWN.clear()
        if self.groq_key:
            try:
                self._groq = GroqClient(self.groq_key, self.groq_model)
            except ValueError:
                self._groq = None

    def yerel_modeller(self) -> list:
        return self._ollama.modeller()

    def yerel_cevap(self, messages, model, tools=None):
        return self._ollama.cevapla(messages, model, tools=tools)

    def _tek_cagri(self, istemci, ad, messages, tools, override_model,
                   yapi_deger):
        """Tek saglayiciya cagri kurar; yapi_deger None ise eski davranis.

        FAZ 1.1: yapi_deger verildiginde adaptore yapi sozlesmesi tasınır.
        Tum mesajlar API-uyumlu formata temizlenir (content string garanti).
        """
        from brain.message_utils import mesajlari_temizle
        messages = mesajlari_temizle(messages)
        ekstra = {"yapi": yapi_deger} if yapi_deger else {}
        # override_model: GroqClient icin model degistirme (retry icin)
        if override_model and ad == "groq" and hasattr(istemci, 'cevapla'):
            import inspect
            params = inspect.signature(istemci.cevapla).parameters
            if 'model' in params:
                return istemci.cevapla(
                    messages, tools=tools, model=override_model, **ekstra)
        if tools:
            return istemci.cevapla(messages, tools=tools, **ekstra)
        return istemci.cevapla(messages, **ekstra)

    def cevapla(self, messages, yerel_model, tools=None,
                tercih=None, gorev_tipi=None, override_model=None, yapi=None):
        """Mesajlara cevap verir — Router v2 (P3, kota katmanı söküldü).

        Akis: secici motoru sirayi belirler → deneme; hata verirse siradaki
        devralir; hepsi duserse yerel Ollama son care.

        Donus: (yanit, gosterim) — gosterim "nvidia · kod isi" tarzinda
        seffaf secim bilgisi tasir.
        tercih: eski cagri uyumlulugu icin acik sira zorlamasi.
        yapi: sozlesme modu (FAZ 1.1) — dict|None; destekleyen saglayiciya
        tasınır, 400/invalid_request_error ile reddedilirse ayni saglayici
        yapi'siz bir kez daha denenir (_YAPI_DENEME self-healing onbellegi).
        """
        zincir = self._bulut_zinciri()
        mevcutlar = [ad for ad, _ in zincir]

        if tercih:
            one_alinan = sorted(
                (a for a in mevcutlar if a in tercih),
                key=lambda a: tercih.index(a),
            )
            kalanlar = [a for a in mevcutlar if a not in tercih]
            sirali = one_alinan + kalanlar
            gerekce = "acik tercihle siralandi"
            tip = gorev_tipi or "genel"
        else:
            soru = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    soru = m.get("content", "") or ""
                    break
            sirali, gerekce = secici.sec(
                text=soru, gorev_tipi=gorev_tipi,
                tools=bool(tools), mevcutlar=mevcutlar,
                karne_kullan=True,    # B1: deneyim sirayi geriye itebilir
                cooldown=_COOLDOWN)   # rate-limit cooldown bilgisi
            tip = secici.siniflandir(soru)

        istemciler = dict(zincir)
        hatalar = []
        for ad in sirali:
            istemci = istemciler.get(ad)
            if istemci is None:
                continue
            # Cooldown: 429 gelmisse atla
            kalan = _cooldown_kaldi(ad)
            if kalan > 0:
                logger.info("%s cooldown (%.0f sn), atlandi", ad, kalan)
                continue

            istat = model_stats_al()
            t0 = time.time()
            # FAZ 1.1: yapi istenmisse ve saglayici daha once kirmamissa
            # sozlesme tasınır; kirtilmis saglayicida yapi hic gonderilmez.
            yapi_bu = yapi if (yapi and _YAPI_DENEME.get(ad, True)) else None
            try:
                try:
                    yanit = self._tek_cagri(
                        istemci, ad, messages, tools, override_model, yapi_bu)
                except Exception as e:
                    # Saglayici yapi'yi bad-request ile reddetti → isaretle,
                    # ayni saglayiciyi yapısız HEMEN tekrar dene; hata zinciri
                    # bugunku gibi islenir.
                    if yapi_bu is not None and _yapi_desteksiz_mi(e):
                        _YAPI_DENEME[ad] = False
                        logger.warning(
                            "%s yapi'yi kabul etmedi (%s) — yapısız tek deneme",
                            ad, str(e)[:120])
                        yanit = self._tek_cagri(
                            istemci, ad, messages, tools, override_model, None)
                    else:
                        raise
                sure = time.time() - t0
                aile = _aile_coz(ad, getattr(istemci, "model", ""))
                _audit("OK kaynak=%s | %.1f sn | tools=%s | %s | aile=%s" %
                       (ad, sure, bool(tools), gerekce, aile))
                # Gercek token sayimi (2026-08-24): adaptorden gelen
                # kullanim bilgisini ayikla ve istatistige yaz.
                kullanim = None
                if isinstance(yanit, dict):
                    kullanim = yanit.pop("_kullanim", None)
                    # 2026-09-12: kesinti teshisi — length bitisi
                    # max_tokens duvaridir, loga dus (davranis degismez).
                    bitis = yanit.get("_bitis")
                    if bitis and bitis not in ("stop", "tool_calls"):
                        logger.warning(
                            "%s cevabi '%s' ile bitti (kesinti suphesi)",
                            ad, bitis)
                istat.kaydet(
                    ad, sure, basarili=True, tools=bool(tools),
                    token_in=(kullanim or {}).get("giris", 0),
                    token_out=(kullanim or {}).get("cikis", 0))
                # Secim gorunur olsun: one alinma varsa gosterimde tasi
                gosterim = ad
                if tip in ("kod", "arastirma", "hiz") and ad in sirali[:2]:
                    gosterim = "%s · %s isi" % (ad, tip)
                return yanit, gosterim
            except Exception as e:
                sure = time.time() - t0
                logger.warning("%s hatasi, siradaki deneniyor: %s", ad, e)
                hatalar.append("%s: %s" % (ad, str(e)[:80]))
                if _rate_limit_mi(e):
                    _cooldown_ekle(ad)
                    logger.info("%s rate-limit, cooldown baslatildi", ad)
                elif _erisim_engeli_mi(e):
                    # 2026-09-12: 403/401/paid-plan dakikada iyilesmez —
                    # her turda ölü saglayici denenmesin, 1 saat pas geç.
                    _cooldown_ekle(ad, sure=_ERISIM_COOLDOWN)
                    logger.info("%s erisim engeli, %d sn pas geciliyor", ad,
                                _ERISIM_COOLDOWN)
                elif _zaman_asimi_mi(e):
                    # 2026-09-11: zaman asimi da kisa cooldown alsin —
                    # GLM her istekte ayni duvara carpip patlamasin.
                    _cooldown_ekle(ad, sure=_ZAMAN_ASIMI_COOLDOWN)
                    logger.info("%s zaman asimi, %d sn cooldown", ad,
                                _ZAMAN_ASIMI_COOLDOWN)
                _audit("HATA kaynak=%s (%.1f sn): %s | aile=%s" %
                       (ad, sure, str(e)[:100],
                        _aile_coz(ad, getattr(istemci, "model", ""))))
                istat.kaydet(ad, sure, basarili=False, hata=str(e)[:100], tools=bool(tools))

        # Tum bulutlar dustu → yerel Ollama
        istat = model_stats_al()
        try:
            t0 = time.time()
            if yapi:
                yanit = self._ollama.cevapla(
                    messages, yerel_model, tools=tools, yapi=yapi)
            else:
                yanit = self._ollama.cevapla(messages, yerel_model, tools=tools)
            sure = time.time() - t0
            _audit("OK kaynak=yerel | %.1f sn | tools=%s | dustu=%d bulut"
                   % (sure, bool(tools), len(hatalar)))
            istat.kaydet("yerel", sure, basarili=True, tools=bool(tools))
            return yanit, "yerel"
        except Exception as e:
            istat.kaydet("yerel", 0, basarili=False, hata=str(e)[:100], tools=bool(tools))
            detay = "; ".join(hatalar) if hatalar else str(e)
            _audit("TAM BASARISIZLIK: %s" % detay[:150])
            raise RuntimeError(f"Hicbir model calismadi ({detay})") from e

    def cevapla_yayin(self, messages, yerel_model, tercih=None,
                      gorev_tipi=None):
        """Akan cevap uretir: yield (kaynak, parca).

        Aracsiz duz sohbet icindir (tools=None). Model arac isterse
        AracIstegi firlatir — cagiran tam yola duser. Hicbir saglayici
        akis acamazsa SonHata firlatir (tam yol TEKRAR denemez — kota yenmez).

        Not: akis sirasinda istatistik/token yazilmaz (kismi sayim
        butceyi bozar). Basari/zaman olcumu tam yolda yapilir.
        """
        from brain.yayin import AracIstegi as _Arac, SonHata, akit
        from brain import secici as _secici

        zincir = self._bulut_zinciri()
        mevcutlar = [ad for ad, _ in zincir]
        if tercih:
            one_alinan = sorted(
                (a for a in mevcutlar if a in tercih),
                key=lambda a: tercih.index(a),
            )
            sirali = one_alinan + [a for a in mevcutlar if a not in tercih]
            gerekce = "acik tercihle siralandi"
        else:
            soru = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    soru = m.get("content", "") or ""
                    break
            sirali, gerekce = _secici.sec(
                text=soru, gorev_tipi=gorev_tipi,
                tools=False, mevcutlar=mevcutlar,
                karne_kullan=True, cooldown=_COOLDOWN)

        istemciler = dict(zincir)
        hatalar = []
        for ad in sirali:
            istemci = istemciler.get(ad)
            if istemci is None:
                continue
            if _cooldown_kaldi(ad) > 0:
                continue
            try:
                if ad == "yerel":
                    from brain.yayin import ollama_akit
                    uretici = ollama_akit(
                        getattr(istemci, "base_url", OLLAMA_URL),
                        yerel_model, messages)
                else:
                    ham = getattr(istemci, "client", None)
                    model = getattr(istemci, "model", None)
                    if ham is None or not model:
                        continue
                    uretici = akit(ham, model, messages)
                basladi = False  # akis ortasi kopma takibi
                for parca in uretici:
                    basladi = True
                    yield ad, parca
                _audit("OK kaynak=%s | akis | %s" % (ad, gerekce))
                return
            except _Arac:
                raise
            except Exception as e:
                hata = str(e)[:100]
                # Akis ORTASINDA kopma: UI'da yari metin var, baska
                # saglayiciyla devam ETME (metin ikilenir). Dogrudan hata.
                if basladi:
                    _audit("AKIS KOPTU kaynak=%s: %s" % (ad, hata[:80]))
                    raise SonHata("cevap yolda kesildi (%s)" % ad)
                logger.warning("%s akis hatasi: %s", ad, hata)
                hatalar.append("%s: %s" % (ad, hata[:60]))
                if _rate_limit_mi(e):
                    _cooldown_ekle(ad)
                elif _erisim_engeli_mi(e):
                    _cooldown_ekle(ad, sure=_ERISIM_COOLDOWN)
                elif _zaman_asimi_mi(e):
                    # 2026-09-11: zaman asimi da kisa cooldown alsin.
                    _cooldown_ekle(ad, sure=_ZAMAN_ASIMI_COOLDOWN)
                continue

        # Yerel son care (zincirde yoksa dogrudan dene). Yerel hizli
        # oldugu icin once biriktirilir, sonra verilir — yari metin
        # ikilenme riski olmaz.
        try:
            from brain.yayin import ollama_akit
            if yerel_model:
                birikmis = list(ollama_akit(OLLAMA_URL, yerel_model,
                                            messages))
                for parca in birikmis:
                    yield "yerel", parca
                _audit("OK kaynak=yerel | akis")
                return
        except _Arac:
            raise
        except Exception as e:
            hatalar.append("yerel: %s" % str(e)[:60])

        detay = "; ".join(hatalar) if hatalar else "bilinmeyen hata"
        _audit("AKIS BASARISIZ: %s" % detay[:150])
        raise SonHata(detay)