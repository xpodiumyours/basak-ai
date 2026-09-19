"""brain/brain.py — Basak'in ana beyin sinifi.

Ozgu-ajan (Faz 2): SADECE ucretsiz bulut zinciri. Yerel model yok —
hata verirse siradaki bulut devralir, hepsi duserse acik hata doner.
"""

import json
import logging
import os
import time
from datetime import datetime

from brain.groq import MODELLER, GroqClient  # MODELLER sabiti + anahtar yenileme
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

# COOLDOWN: rate-limit (429) gelince provider gecici olarak atla
import time as _time_mod
_COOLDOWN = {}  # {ad: bitis_zamani}
_COOLDOWN_SURE = 20

# Zaman asimi cooldown'u (2026-09-11, 2026-09-19'da uzatildi):
# 429 kadar agir degil ama tekrar tekrar denenirse her mesaja ayni
# bekleme cezasi biner. Olcum (hiz_olcum.py): GLM her istekte 20.62 sn'de
# zaman asimina ugruyordu; 10 sn'lik cooldown bir sonraki mesajda doldugu
# icin ceza HER mesajda yeniden odeniyordu. 300 sn: olu saglayici 5 dakika
# atlanir, zincir kalanlarla aninda cevap verir.
_ZAMAN_ASIMI_COOLDOWN = 300

def _cooldown_kaldi(ad):
    bitis = _COOLDOWN.get(ad, 0)
    kalan = bitis - _time_mod.time()
    return max(0, kalan)

def _cooldown_ekle(ad, sure=None):
    _COOLDOWN[ad] = _time_mod.time() + (sure or _COOLDOWN_SURE)

def _rate_limit_mi(hata):
    s = str(hata).lower()
    return any(k in s for k in ("429", "rate", "limit", "too many", "quota"))


def _bekleme_suresi(hata):
    """Saglayicinin soyledigi bekleme suresi (sn) — yoksa None.

    429/413 mesajlari "try again in 10.7s" tasir; sabit 20 sn yerine
    soylenene uyulur (bosuna erken donup kota yenmez). Tavan 180 sn:
    saf teknik bekleme, secim karari degil.
    """
    import re as _re
    s = str(hata)
    m = _re.search(r"try again in ([\d.]+)s", s)
    if not m:
        m = _re.search(r"(?i)retry[-\s]?after[:\s]+([\d.]+)", s)
    if not m:
        return None
    try:
        return max(1.0, min(180.0, float(m.group(1))))
    except ValueError:
        return None


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

    def _bulut_zinciri(self, tools: bool = False,
                       tool_required: bool = False) -> list:
        """Musait bulut istemcilerini toplar: [(ad, istemci)].

        DIKKAT: Bu listenin sirasi ONCELIK SIRASI DEGILDIR. Gercek
        sirayi secici.sec() belirler (registry.VARSAYILAN_SIRA temel).
        Buradaki sira yalnizca secici'ye mevcut havuzu vermek ve
        'tercih'siz eski cagrilarda yedek siralamak icindir.

        Teknik filtreler (P0 — yeni router degil):
        - musaitlik (istemci kurulu + anahtar var)
        - tool destegi (aracli cagrida registry karti tools=False ise girmez)
        Ucretli ozel saglayici EN SONDA durur.
        """
        _tool_istiyor = bool(tools)
        def _uygun(ad, istemci) -> bool:
            if not registry.otomatik_ucretsiz_mi(ad):
                return False
            try:
                if istemci is None or not istemci.musait():
                    return False
            except Exception:
                return False
            if _tool_istiyor:
                try:
                    if not registry.tool_destegi_var_mi(ad):
                        return False
                    if (tool_required
                            and not registry.ajan_destegi_var_mi(ad)):
                        return False
                    if tool_required:
                        denetle = getattr(istemci, "ajan_musait", None)
                        if callable(denetle) and not denetle():
                            return False
                except Exception:
                    pass
            return True
        zincir = []
        if _uygun("groq", self._groq):
            zincir.append(("groq", self._groq))
        if _uygun("glm", self._glm):
            zincir.append(("glm", self._glm))
        if _uygun("cloudflare", self._cloudflare):
            zincir.append(("cloudflare", self._cloudflare))
        if _uygun("cohere", self._cohere):
            zincir.append(("cohere", self._cohere))
        if _uygun("nvidia", self._nvidia):
            zincir.append(("nvidia", self._nvidia))
        if _uygun("kilo", self._kilo):
            zincir.append(("kilo", self._kilo))
        if _uygun("openrouter", self._openrouter):
            zincir.append(("openrouter", self._openrouter))
        if _uygun("qwen", self._qwen):
            zincir.append(("qwen", self._qwen))
        if _uygun("gemini", self._gemini):
            zincir.append(("gemini", self._gemini))
        # Ozel/ucretli saglayici otomatik zincire girmez.
        _genel = getattr(self, "_genel", None)
        if _uygun("genel", _genel):
            zincir.append(("genel", _genel))
        return zincir

    def bulut_musait(self) -> bool:
        # Herhangi bir bulut saglayici hazirsa True.
        return bool(self._bulut_zinciri())

    def ajan_musait(self) -> bool:
        """Zorunlu function-call protokolu dogrulanmis beyin var mi?"""
        return bool(self._bulut_zinciri(
            tools=True, tool_required=True))

    def anahtar_ayarla(self, key: str):
        self.groq_key = key.strip()
        ayar = _ayar_yukle()
        ayar["groq_key"] = self.groq_key
        _ayar_kaydet(ayar)
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
        if self.groq_key:
            try:
                self._groq = GroqClient(self.groq_key, self.groq_model)
            except ValueError:
                self._groq = None

    def _tek_cagri(self, istemci, ad, messages, tools, override_model,
                   yapi_deger, tool_choice=None):
        """Tek saglayiciya cagri kurar; yapi_deger None ise eski davranis.

        FAZ 1.1: yapi_deger verildiginde adaptore yapi sozlesmesi tasınır.
        Tum mesajlar API-uyumlu formata temizlenir (content string garanti).
        """
        from brain.message_utils import mesajlari_temizle
        messages = mesajlari_temizle(messages)
        ekstra = {"yapi": yapi_deger} if yapi_deger else {}
        if tool_choice is not None:
            # Basak disarida tek "required" ajan sozlesmesi kullanir;
            # saglayiciya ise kendi resmi protokolune uygun deger gider.
            ekstra["tool_choice"] = (
                registry.ajan_tool_choice(ad)
                if tool_choice == "required" else tool_choice
            )
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

    def cevapla(self, messages, yerel_model=None, tools=None,
                tercih=None, gorev_tipi=None, override_model=None, yapi=None,
                tool_choice=None):
        """Mesajlara cevap verir — Router v2 (bulut zinciri).

        Akis: secici motoru sirayi belirler → deneme; hata verirse siradaki
        devralir; hepsi duserse RuntimeError (yerel yedek YOK — Faz 2).

        Donus: (yanit, gosterim) — gosterim "nvidia" tarzinda seffaf
        secim bilgisi tasir.
        tercih: eski cagri uyumlulugu icin acik sira zorlamasi.
        yerel_model: uyumluluk icin durur, kullanilmaz (bulut kendi
        modelini secer).
        yapi: sozlesme modu (FAZ 1.1) — dict|None; destekleyen saglayiciya
        tasınır, 400/invalid_request_error ile reddedilirse ayni saglayici
        yapi'siz bir kez daha denenir (_YAPI_DENEME self-healing onbellegi).
        """
        if tool_choice == "required":
            zincir = self._bulut_zinciri(
                tools=bool(tools), tool_required=True)
        else:
            # Eski/ajan-disi yolun cagri imzasi aynen korunur. Test doubles
            # ve harici kullanimlar yeni kwarg bilmek zorunda degildir.
            zincir = self._bulut_zinciri(tools=bool(tools))
        mevcutlar = [ad for ad, _ in zincir]

        if tercih:
            one_alinan = sorted(
                (a for a in mevcutlar if a in tercih),
                key=lambda a: tercih.index(a),
            )
            kalanlar = [a for a in mevcutlar if a not in tercih]
            sirali = one_alinan + kalanlar
            gerekce = "acik tercihle siralandi"
        else:
            # P0 (2026-09-15): gorev_tipi / karne / siniflandirici ana AI
            # yolundan cikti. Secim yalniz teknik gerceklerle sinirli:
            # musaitlik (_bulut_zinciri), ucretsiz olma + tool destegi
            # (registry), rate-limit atlama (cooldown). Yeni router YOK.
            sirali, gerekce = secici.sec(mevcutlar=mevcutlar)

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
                        istemci, ad, messages, tools, override_model, yapi_bu,
                        tool_choice)
                except Exception as e:
                    # Saglayici yapi'yi bad-request ile reddetti → isaretle,
                    # ayni saglayiciyi yapısız HEMEN tekrar dene; hata zinciri
                    # bugunku gibi islenir.
                    if yapi_bu is not None and _yapi_desteksiz_mi(e):
                        _YAPI_DENEME[ad] = False
                        logger.warning(
                            "%s yapi'yi kabul etmedi (%s) — yapısız tek deneme",
                            ad, str(e))
                        yanit = self._tek_cagri(
                            istemci, ad, messages, tools, override_model, None,
                            tool_choice)
                    else:
                        raise
                # Ajan turunda saglayici "auto" kullanmak zorundaysa bile
                # duz metin Basak icin basari sayilmaz. Model gercek bir
                # tool-call dondurmezse ayni istek siradaki uygun saglayiciya
                # devredilir. Boylece model secimi korunur, chatbot kacagi yok.
                if tool_choice == "required":
                    araclar = (yanit.get("tool_calls")
                               if isinstance(yanit, dict) else None)
                    if not araclar:
                        raise RuntimeError(
                            "ajan protokolu: saglayici tool-call dondurmedi")
                sure = time.time() - t0
                _audit("OK kaynak=%s | %.1f sn | tools=%s | %s" %
                       (ad, sure, bool(tools), gerekce))
                # Gercek token sayimi (2026-08-24): adaptorden gelen
                # kullanim bilgisini ayikla ve istatistige yaz.
                kullanim = None
                if isinstance(yanit, dict):
                    kullanim = yanit.pop("_kullanim", None)
                istat.kaydet(
                    ad, sure, basarili=True, tools=bool(tools),
                    token_in=(kullanim or {}).get("giris", 0),
                    token_out=(kullanim or {}).get("cikis", 0))
                # Secim gorunur olsun: hangi saglayici cevapladysa adi tasinir.
                return yanit, ad
            except Exception as e:
                sure = time.time() - t0
                logger.warning("%s hatasi, siradaki deneniyor: %s", ad, e)
                hatalar.append("%s: %s" % (ad, str(e)))
                if _rate_limit_mi(e):
                    bekle = _bekleme_suresi(e)
                    _cooldown_ekle(ad, sure=bekle)
                    logger.info("%s rate-limit, %.0f sn cooldown",
                                ad, bekle or _COOLDOWN_SURE)
                elif _zaman_asimi_mi(e):
                    # 2026-09-11: zaman asimi da kisa cooldown alsin —
                    # GLM her istekte ayni duvara carpip patlamasin.
                    _cooldown_ekle(ad, sure=_ZAMAN_ASIMI_COOLDOWN)
                    logger.info("%s zaman asimi, %d sn cooldown", ad,
                                _ZAMAN_ASIMI_COOLDOWN)
                _audit("HATA kaynak=%s (%.1f sn): %s" %
                       (ad, sure, str(e)))
                istat.kaydet(ad, sure, basarili=False, hata=str(e), tools=bool(tools))

        # Tum bulutlar dustu → acik hata (yerel yedek yok — Faz 2).
        detay = "; ".join(hatalar) if hatalar else "bulut zinciri bos"
        _audit("TAM BASARISIZLIK: %s" % detay)
        raise RuntimeError(f"Hicbir model calismadi ({detay})")

    def cevapla_yayin(self, messages, yerel_model=None, tercih=None,
                      gorev_tipi=None, tools=None):
        """Akan cevap uretir: yield (kaynak, parca).

        Aracsiz duz sohbet icindir (tools=None). Model arac isterse
        AracIstegi firlatir — cagiran tam yola duser. Hicbir saglayici
        akis acamazsa SonHata firlatir (tam yol TEKRAR denemez — kota yenmez).
        yerel_model: uyumluluk icin durur, kullanilmaz.

        Not: akis sirasinda istatistik/token yazilmaz (kismi sayim
        butceyi bozar). Basari/zaman olcumu tam yolda yapilir.
        """
        from brain.yayin import AracIstegi as _Arac, SonHata, akit
        from brain import secici as _secici

        zincir = self._bulut_zinciri(tools=bool(tools))
        mevcutlar = [ad for ad, _ in zincir]
        if tercih:
            one_alinan = sorted(
                (a for a in mevcutlar if a in tercih),
                key=lambda a: tercih.index(a),
            )
            sirali = one_alinan + [a for a in mevcutlar if a not in tercih]
            gerekce = "acik tercihle siralandi"
        else:
            # P0: gorev_tipi ana yoldan cikti; yalniz teknik sira.
            sirali, gerekce = _secici.sec(mevcutlar=mevcutlar)

        istemciler = dict(zincir)
        hatalar = []
        for ad in sirali:
            istemci = istemciler.get(ad)
            if istemci is None:
                continue
            if _cooldown_kaldi(ad) > 0:
                continue
            try:
                ham = getattr(istemci, "client", None)
                model = getattr(istemci, "model", None)
                if ham is None or not model:
                    continue
                uretici = akit(ham, model, messages, tools=tools)
                basladi = False  # akis ortasi kopma takibi
                for parca in uretici:
                    basladi = True
                    yield ad, parca
                _audit("OK kaynak=%s | akis | %s" % (ad, gerekce))
                return
            except _Arac:
                raise
            except Exception as e:
                hata = str(e)
                # Akis ORTASINDA kopma: UI'da yari metin var, baska
                # saglayiciyla devam ETME (metin ikilenir). Dogrudan hata.
                if basladi:
                    _audit("AKIS KOPTU kaynak=%s: %s" % (ad, hata))
                    raise SonHata("cevap yolda kesildi (%s)" % ad)
                logger.warning("%s akis hatasi: %s", ad, hata)
                hatalar.append("%s: %s" % (ad, hata))
                if _rate_limit_mi(e):
                    _cooldown_ekle(ad, sure=_bekleme_suresi(e))
                elif _zaman_asimi_mi(e):
                    # 2026-09-11: zaman asimi da kisa cooldown alsin.
                    _cooldown_ekle(ad, sure=_ZAMAN_ASIMI_COOLDOWN)
                continue

        detay = "; ".join(hatalar) if hatalar else "bilinmeyen hata"
        _audit("AKIS BASARISIZ: %s" % detay)
        raise SonHata(detay)