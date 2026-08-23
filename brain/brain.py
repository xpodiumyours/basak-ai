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
from brain.gemini import GeminiClient
from brain.glm import GLMClient
from brain.nvidia import NvidiaClient
from brain.openrouter import OpenRouterClient
from brain.cloudflare import CloudflareClient
from brain.cohere import CohereClient
from brain.qwen import QwenClient
from brain.ollama import OllamaClient
from brain.stats import model_stats_al
from brain.kota import KotaYoneticisi
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


class Brain:
    def __init__(self):
        ayar = _ayar_yukle()
        # P3 kota yoneticisi: ucretli engeli varsayilan ACIK
        self.kota = KotaYoneticisi(
            ucretli_engelli=bool(ayar.get("ucretli_engelli", True)))
        self.groq_key = (
            os.environ.get("GROQ_API_KEY") or ayar.get("groq_key") or ""
        )
        self.groq_model = ayar.get("groq_model", MODELLER["varsayilan"])
        self._groq = None
        self._ollama = OllamaClient()
        if self.groq_key:
            try:
                self._groq = GroqClient(self.groq_key, self.groq_model)
            except ValueError as e:
                logger.warning("Groq baslatilamadi: %s", e)

        # Ikinci bulut saglayici: Gemini (env GEMINI_API_KEY veya ayar dosyasi)
        self.gemini_key = (
            os.environ.get("GEMINI_API_KEY") or ayar.get("gemini_key") or ""
        )
        self._gemini = None
        if self.gemini_key:
            try:
                self._gemini = GeminiClient(self.gemini_key)
            except ValueError as e:
                logger.warning("Gemini baslatilamadi: %s", e)

        # Ucuncu bulut saglayici: GLM (Z.ai resmi platformu)
        self.zai_key = (
            os.environ.get("ZAI_API_KEY") or ayar.get("zai_key") or ""
        )
        self._glm = None
        if self.zai_key:
            try:
                self._glm = GLMClient(self.zai_key)
            except ValueError as e:
                logger.warning("GLM baslatilamadi: %s", e)

        # Altinci bulut saglayici: NVIDIA NIM (GPT-OSS / Nemotron / Kimi)
        self.nvidia_key = (
            os.environ.get("NVIDIA_API_KEY") or ayar.get("nvidia_key") or ""
        )
        self._nvidia = None
        if self.nvidia_key:
            try:
                self._nvidia = NvidiaClient(
                    self.nvidia_key, model=ayar.get("nvidia_model"))
            except ValueError as e:
                logger.warning("NVIDIA baslatilamadi: %s", e)

        # Yedinci bulut saglayici: OpenRouter (sadece :free modeller, son care)
        self.openrouter_key = (
            os.environ.get("OPENROUTER_API_KEY") or ayar.get("openrouter_key") or ""
        )
        self._openrouter = None
        if self.openrouter_key:
            try:
                self._openrouter = OpenRouterClient(self.openrouter_key)
            except ValueError as e:
                logger.warning("OpenRouter baslatilamadi: %s", e)

        # Sekizinci bulut saglayici: Cloudflare Workers AI (ucretsiz)
        self.cloudflare_account = (
            os.environ.get("CLOUDFLARE_ACCOUNT_ID")
            or ayar.get("cloudflare_account_id") or ""
        )
        self.cloudflare_key = (
            os.environ.get("CLOUDFLARE_API_TOKEN")
            or ayar.get("cloudflare_api_token") or ""
        )
        self._cloudflare = None
        if self.cloudflare_account and self.cloudflare_key:
            try:
                self._cloudflare = CloudflareClient(
                    self.cloudflare_account, self.cloudflare_key)
            except ValueError as e:
                logger.warning("Cloudflare baslatilamadi: %s", e)

        # Dokuzuncu bulut saglayici: Cohere (ucretsiz Trial key)
        self.cohere_key = (
            os.environ.get("COHERE_API_KEY")
            or ayar.get("cohere_key") or ""
        )
        self._cohere = None
        if self.cohere_key:
            try:
                self._cohere = CohereClient(self.cohere_key)
            except ValueError as e:
                logger.warning("Cohere baslatilamadi: %s", e)

        # Onuncu bulut saglayici: QwenCloud (DashScope)
        self.dashscope_key = (
            os.environ.get("DASHSCOPE_API_KEY")
            or ayar.get("dashscope_key") or ""
        )
        self._qwen = None
        if self.dashscope_key:
            try:
                self._qwen = QwenClient(self.dashscope_key)
            except ValueError as e:
                logger.warning("QwenCloud baslatilamadi: %s", e)

    def _bulut_zinciri(self) -> list:
        """Oncelik sirasi: Groq -> GLM -> Cloudflare -> Cohere -> NVIDIA
        -> OpenRouter -> QwenCloud -> Gemini. Son care: Ollama (yerel)."""
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
        if self._openrouter is not None and self._openrouter.musait():
            zincir.append(("openrouter", self._openrouter))
        if self._qwen is not None and self._qwen.musait():
            zincir.append(("qwen", self._qwen))
        if self._gemini is not None and self._gemini.musait():
            zincir.append(("gemini", self._gemini))
        return zincir

    def bulut_musait(self) -> bool:
        # Herhangi bir bulut saglayici hazirsa True. Ollama son caredir.
        return bool(self._bulut_zinciri())

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

    def yerel_modeller(self) -> list:
        return self._ollama.modeller()

    def yerel_cevap(self, messages, model, tools=None):
        return self._ollama.cevapla(messages, model, tools=tools)

    def cevapla(self, messages, yerel_model, tools=None,
                tercih=None, gorev_tipi=None):
        """Mesajlara cevap verir — Router v2 (P3).

        Akis: secici motoru sirayi belirler (gorev turune gore, gerekcesiyle)
        → kota/saglik filtresi engellileri atlar → deneme; hata verirse
        siradaki devralir; hepsi duserse yerel Ollama son care.

        Donus: (yanit, gosterim) — gosterim "nvidia · kod isi" tarzinda
        seffaf secim bilgisi tasir.
        tercih: eski cagri uyumlulugu icin acik sira zorlamasi.
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
                tools=bool(tools), mevcutlar=mevcutlar)
            tip = secici.siniflandir(soru)

        istemciler = dict(zincir)
        hatalar = []
        for ad in sirali:
            istemci = istemciler.get(ad)
            if istemci is None:
                continue

            # P3: kota / ucretli / soguma engeli
            engel = self.kota.engel_nedeni(ad, registry.kart(ad))
            if engel:
                logger.info("%s atlandi: %s", ad, engel)
                _audit("ATLANDI kaynak=%s | neden=%s" % (ad, engel))
                hatalar.append("%s: %s" % (ad, engel))
                continue

            istat = model_stats_al()
            t0 = time.time()
            try:
                if tools:
                    yanit = istemci.cevapla(messages, tools=tools)
                else:
                    yanit = istemci.cevapla(messages)
                sure = time.time() - t0
                istek_no = self.kota.harca(ad)
                _audit("OK kaynak=%s | %.1f sn | tools=%s | istek=%d | %s" %
                       (ad, sure, bool(tools), istek_no, gerekce))
                istat.kaydet(ad, sure, basarili=True, tools=bool(tools))
                # Secim gorunur olsun: one alinma varsa gosterimde tasi
                gosterim = ad
                if tip in ("kod", "arastirma", "hiz") and ad in sirali[:2]:
                    gosterim = "%s · %s isi" % (ad, tip)
                return yanit, gosterim
            except Exception as e:
                sure = time.time() - t0
                logger.warning("%s hatasi, siradaki deneniyor: %s", ad, e)
                hatalar.append("%s: %s" % (ad, str(e)[:80]))
                self.kota.hata_isle(ad, str(e))
                _audit("HATA kaynak=%s (%.1f sn): %s" %
                       (ad, sure, str(e)[:100]))
                istat.kaydet(ad, sure, basarili=False, hata=str(e)[:100], tools=bool(tools))

        # Tum bulutlar dustu → yerel Ollama
        istat = model_stats_al()
        try:
            t0 = time.time()
            yanit = self._ollama.cevapla(messages, yerel_model, tools=tools)
            sure = time.time() - t0
            istek_no = self.kota.harca("yerel")
            _audit("OK kaynak=yerel | %.1f sn | tools=%s | istek=%d | dustu=%d bulut"
                   % (sure, bool(tools), istek_no, len(hatalar)))
            istat.kaydet("yerel", sure, basarili=True, tools=bool(tools))
            return yanit, "yerel"
        except Exception as e:
            istat.kaydet("yerel", 0, basarili=False, hata=str(e)[:100], tools=bool(tools))
            detay = "; ".join(hatalar) if hatalar else str(e)
            _audit("TAM BASARISIZLIK: %s" % detay[:150])
            raise RuntimeError(f"Hicbir model calismadi ({detay})") from e