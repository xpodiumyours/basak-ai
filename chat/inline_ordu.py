"""Aynı istek içinde paralel alt ajan (ordu) — kalıcı işçi, hesap ve DB yok.

Vercel sunucusuz ortamında kalıcı işçi (worker.platform) yaşayamaz; burada
alt ajanlar **aynı sohbet isteği içinde** paralel thread'lerde, aynı Brain
ile aynı `chat.flow.mesaj_isle` döngüsü koşar. Kalıcı platform yolu (Neon
defter + worker) olduğu gibi korunur; bu modül yalnız web sohbetinin alt
ajan kapasitesini açar (AGENTS.md §9: ikinci beyin yok, tek çekirdek).

Kimlik: `ExecutionContext`'in "kalıcı hesap" doğrulaması yalnız kalıcı
yol için kalır; `inline=True` verilen zarf bu doğrulamadan geçmez. Kota
kapısı (`app._kota_kapisi`) isteğin kendisini daha önce zaten saymıştır;
burada her alt ajan ayrıca ana kullanıcının günlük kotasından harcar.

Yetenek sınırı çalışma biçimine bağlıdır, kelimeye değil (AGENTS.md §0):
- Ana ajan (sohbet): `capabilities.katalog_sec` ne veriyorsa o + ajanlar
  alanı; araç seçimini yine model yapar.
- Alt ajanlar: yalnız salt-okunur `capabilities.PUBLIC_TOOLS`. Alt ajan
  alt ajan açamaz (derinlik 1; `allowed_tools` ile yapılandırılır).
- Kota doluysa alt ajan açılmaz; hata modele görünür şekilde döner.

Bilinen sınır: istek bitince bekleyen alt ajan thread'leri dondurulur;
devamı kalıcı platform yolunun işidir. `wait_for_children` burada
**bekler** (kalıcı yolda çalışmayı duraklatır) — istek tek HTTP yanıtında
bitmek zorundadır.
"""

import json
import logging
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass

from chat.platform_context import ExecutionContext, bound

logger = logging.getLogger(__name__)

# Tek sohbet isteğinde ayni anda çalıştırılacak azami alt ajan sayısı.
AZAMI_PARALEL = 4


@dataclass(frozen=True)
class _Kiralik:
    """İstek içi zarfın kimlik taşıyan kira karşılığı (defter yok)."""
    user_id: str
    run_id: str


class _CocukAykici:
    """Alt ajanın `js_callback`'i: cevabı toplar, adımları ana ekrana taşır.

    Alt ajanın kelime kelime metin akışı ana ekranla karışmaz; yalnız
    çalışma adımları (toolStatus/toolDone/source/harita) ve hatalar
    `alt_ajan` kimliğiyle etiketlenerek ana olay toplayıcısına taşınır.
    Nihai cevap `alt_ajan_sonuclari` aracının sonucu olarak modele döner.
    """

    def __init__(self, kayit, ana_olay=None):
        self.kayit = kayit
        self.ana_olay = ana_olay
        self.cevap = ""
        self.kaynak = ""
        self.hata = ""

    def __call__(self, kod):
        if not isinstance(kod, str) or not kod.startswith("BasakUI."):
            return
        try:
            ad, icerik = kod[8:].split("(", 1)
            parca = json.loads("[%s]" % icerik.rsplit(")", 1)[0])
        except (TypeError, ValueError):
            return
        if ad == "bitir":
            self.cevap = str(parca[0]) if parca else ""
            self.kaynak = str(parca[1]) if len(parca) > 1 else ""
            return
        if ad in ("parca", "thinking", "runState"):
            return
        if ad == "error" and parca:
            self.hata = str(parca[0])
        if self.ana_olay is not None:
            self.ana_olay(ad, self.kayit["id"],
                          {"metin": str(parca[0])} if parca else {})

    def olay(self, tur, **veri):
        """Zengin olayları ana ekrana alt ajan kimliğiyle taşır."""
        if tur == "runState":
            return None
        veri.pop("_handoff", None)
        if self.ana_olay is not None:
            self.ana_olay(str(tur), self.kayit["id"], veri)
        return None


class _Depo:
    """İstek boyunca yaşayan alt ajan defteri (Postgres/worker yok).

    `tools/platform.execute` bu arayüz üzerinden iş kurar; kalıcı
    `RuntimeStore` ile aynı adları kullanır, aynı sözü verir: kimlik,
    paralel sınırı, ağaç sorgusu ve onay/red sonuçları.
    """

    max_children_per_parent = AZAMI_PARALEL

    def __init__(self, kota_harcakci=None):
        self._kilit = threading.Lock()
        self._kayitlar = {}
        self._ipler = {}
        self._kota_harcakci = kota_harcakci

    # — before_action / arac_dongusu arayüzü —
    def replay_completed(self, lease, call_id, name, args):
        return False  # aynı istek içinde tekrar oynatma yok

    def consume_approval(self, lease, action, resource, arguments):
        return False  # istek içi yolda onay kanalı yok

    def workspace_files(self, user_id, workspace_id, include_deleted=False):
        return []  # istek boyunca kalıcı dosya kaydı tutulmaz

    def publish_files(self, lease, workspace_id, changes):
        return None

    # — alt ajan arayüzü (tools/platform.execute) —
    def create(self, user_id, workspace_id, gorev, parent_id=None,
               model_ref="isci", dependencies=None, allowed_tools=None,
               acceptance=None, context=None, request_key=None):
        gorev = str(gorev or "").strip()
        if not gorev:
            raise ValueError("Her alt gorev aciklamasi gerekli")
        if not parent_id:
            raise ValueError("Alt ajan yalniz ana sohbet isteginde acilir")
        with self._kilit:
            # Sinir TOPLAM degil AKTIF sayidir: biten alt ajan yerine
            # siradaki acilir; istek icinde ardisik dalgalar serbesttir.
            aktif = sum(
                1 for k in self._kayitlar.values()
                if k.get("parent") == parent_id
                and k.get("durum") in ("queued", "running"))
            if aktif >= AZAMI_PARALEL:
                raise ValueError(
                    "Ayni anda alt ajan siniri (%d) doldu; calisanlarin "
                    "sonuclarini okuyup bekle." % AZAMI_PARALEL)
            kayit = {
                "id": "orda-" + uuid.uuid4().hex[:12],
                "durum": "queued",
                "gorev": gorev,
                "parent": parent_id,
                "model_ref": str(model_ref or "isci"),
            }
            self._kayitlar[kayit["id"]] = kayit
        # Kota kararı model çalışmadan önce verilir; doluysa alt ajan
        # hiç başlamaz ve nedeni modele görünür bir hatayla döner.
        if self._kota_harcakci is not None and not self._kota_harcakci():
            with self._kilit:
                kayit["durum"] = "blocked"
                kayit["hata"] = ("Gunluk ucretsiz kota doldu; alt ajan "
                                 "calistirilmadi")
            raise ValueError("Gunluk ucretsiz kota doldu; alt ajan "
                             "calistirilmadi")
        ipe = threading.Thread(target=self._kos, args=(kayit,),
                               name="orda-" + kayit["id"], daemon=True)
        with self._kilit:
            self._ipler[kayit["id"]] = ipe
            kayit["durum"] = "running"
        ipe.start()
        return dict(kayit)

    def tree(self, user_id, run_id):
        with self._kilit:
            return {"children": [
                {k: v for k, v in kayit.items() if k != "parent"}
                for kayit in self._kayitlar.values()
                if kayit.get("parent") == run_id
            ]}

    def _ipler_kopya(self):
        with self._kilit:
            return dict(self._ipler)

    def _kos(self, kayit):
        """Tek alt ajanı ana beyinle, izole geçmişle koşar."""
        from chat.ayar import sistem_blogu
        from chat.capabilities import PUBLIC_TOOLS
        from chat.flow import mesaj_isle
        from chat.kimlik import kullanici_kur
        from tools import TOOLS

        kontrol = self._kontrol
        try:
            # Yeni thread taze contextvar'la açılır: kişi kimliğini burada
            # kurmak zorundayız — yoksa varsayılan kullanıcı (casper) olarak
            # başkasının profiline/hafızasına okunurdu.
            kullanici_kur(kontrol.user_id)
            # Ana sohbetle aynı kişi kimliği; parent_run_id sayesinde alt
            # ajan geçmişe/anıya iz bırakmaz (chat.flow._kaydet).
            ctx = ExecutionContext(
                kontrol.user_id, kontrol.workspace_id, kayit["id"],
                parent_run_id=kayit["parent"],
                allowed_tools=frozenset(PUBLIC_TOOLS),
                brain=kontrol.brain, inline=True)
            ayikici = _CocukAykici(kayit, kontrol.alt_ajan_olay)
            katalog = [
                t for t in TOOLS
                if (t.get("function") or {}).get("name") in PUBLIC_TOOLS
            ]
            with bound(ctx):
                mesaj_isle(
                    kayit["gorev"], kontrol.brain,
                    sistem_blogu(kontrol.user_id), ayikici, katalog,
                    misafir=kontrol.misafir,
                    gecmis_override=[],
                    mola_zamani=kontrol.son_saniye)
            kayit["cevap"] = ayikici.cevap
            kayit["saglayici"] = ayikici.kaynak
            if ayikici.cevap:
                kayit["durum"] = "completed"
            else:
                kayit["durum"] = "failed"
                kayit["hata"] = ayikici.hata or "Alt ajan bos cevap dondu"
        except Exception as e:
            logger.warning("inline alt ajan basarisiz (%s): %s",
                           kayit.get("id"), e, exc_info=True)
            kayit["durum"] = "failed"
            kayit["hata"] = str(e)


class InlineKontrol:
    """Sohbet isteği boyunca bağlanan hafif çalışma kontrolü.

    Kalıcı `Control`un arayüzünü taır; kalıcı defter/işçi yerine istek
    boyunca yaşayan `_Depo` kullanır.
    """

    inline = True

    def __init__(self, user_id, workspace_id, run_id, brain,
                 son_saniye=None, olay_verici=None, kota_harcakci=None,
                 iptal=None, misafir=False):
        from chat.kimlik import slugla
        self.user_id = slugla(user_id)
        self.workspace_id = workspace_id
        self.brain = brain
        self.son_saniye = son_saniye
        self.iptal = iptal
        self.misafir = bool(misafir)
        self.lease = _Kiralik(self.user_id, run_id)
        self._adimlar = {}
        self._son_durum = None
        self.depo = _Depo(kota_harcakci=kota_harcakci)
        self.depo._kontrol = self
        self.store = self.depo  # tools/platform.execute control.store okur
        self._olay_verici = olay_verici

    def alt_ajan_olay(self, tur, alt_ajan, veri):
        """Alt ajan adımını ana olay toplayıcısına etiketli taşır."""
        if self._olay_verici is None:
            return
        self._olay_verici(str(tur), str(alt_ajan), dict(veri or {}))

    # — iptal —
    def check_cancelled(self):
        if self.iptal is not None and self.iptal.is_set():
            from chat.platform_runtime import RunCancelled
            raise RunCancelled()

    # — devam/kayıt (istek içi; kalıcı değil) —
    def checkpoint(self, continuation):
        self._son_durum = continuation

    def drain_steering(self):
        return []

    def begin_action(self, call_id, tool, args, side_effect=False):
        return None  # istek içinde tekrar oynatma kaydı yok

    def finish_action(self, call_id, result, ok):
        self._adimlar[call_id] = {"ok": bool(ok)}

    # — kayıt/yayın (istek içi no-op) —
    def event(self, type_, payload=None, **kwargs):
        return None

    def artifact(self, kind, title="", uri="", **metadata):
        return None

    def record_check(self, check_id, ok, evidence):
        return None

    def request_approval(self, action, resource, arguments):
        # İstek içi yolda onay kanalı kurulmaz; onay isteyen araçlar
        # (bağlantı/tarayıcı) zaten bu katalogda değil. Bilinmeyen yol:
        # fail-closed.
        raise PermissionError(
            "Bu islem bu sohbet isteginde onay kanali olmadan "
            "calistirilamaz")

    def wait_for_children(self, child_ids):
        """Alt ajanları bu istek için **bekler** (kalıcı yolda duraklatır)."""
        child_ids = list(dict.fromkeys(child_ids))
        if not child_ids:
            raise ValueError("Alt gorev kimlikleri gerekli")
        for rid in child_ids:
            kayit = self.depo._kayitlar.get(rid)
            if kayit is None or kayit.get("parent") != self.lease.run_id:
                raise PermissionError(
                    "Beklenen gorev bu istegin alt gorevi degil")
        ipler = self.depo._ipler_kopya()
        for rid in child_ids:
            ipe = ipler.get(rid)
            if ipe is None:
                continue
            bekle = None
            if self.son_saniye is not None:
                bekle = max(0.0, self.son_saniye - time.monotonic())
            ipe.join(bekle)


@contextmanager
def inline_baglam(kid, brain, olay_verici=None, iptal=None,
                  son_saniye=None, kota_harcakci=None, misafir=False):
    """Sohbet isteği boyunca inline ordu zarfını bağlar.

    kid: ana kullanıcının kimliği (anonim web kimliği de olabilir).
    olay_verici: (tur, alt_ajan_id, veri) — alt ajan adımları ana ekrana.
    iptal: istemci bağlantıyı kapattığında set edilen threading.Event.
    son_saniye: time.monotonic tabanlı süre sınırı (mola bütçesi).
    kota_harcakci: her alt ajan açılışında bool dönen kota fonksiyonu.
    misafir: ana istek misafir modundaysa alt ajanlar da misafirdir.
    """
    kontrol = InlineKontrol(
        kid, "inline", "ordu-" + uuid.uuid4().hex[:12], brain,
        son_saniye=son_saniye, olay_verici=olay_verici,
        kota_harcakci=kota_harcakci, iptal=iptal, misafir=misafir)
    ctx = ExecutionContext(
        kontrol.user_id, kontrol.workspace_id, kontrol.lease.run_id,
        allowed_tools=None, control=kontrol, brain=brain, inline=True)
    with bound(ctx):
        yield ctx
