"""tools/is_kuyrugu.py — Kalıcı iş kuyruğu (FAZ 3, CANLI-KAPISI.md).

Amaç: "Görev kaybı = 0 / yeniden başlatınca devam = %100" kabulü.
Uzun görevler ADIMLARA bölünür; her adım ÖNCE ve SONRA diske yazılır.
Uygulama ölürse kaldığı adım görünür; aynı ONAYLANMIŞ adım asla iki kez
koşmaz; yarım kalan adım tekrar denenir (en fazla maksimum_deneme).

Saklama kararı (2026-08-24): plan taslağındaki 4 ayrı dosya YERİNE tek
`kuyruk.json` + ATOMİK yazım (tmp+rename). Çökme iki dosya arasında
yakalanırsa görev ikiye bölünür/kaybolur; tek dosyada durum her zaman
tutarlıdır. Planın `durum` alanı job içinde aynen korunur.

Adım sözleşmesi: adımlar çağrılabilir DEĞİL İSİMDİR (kalıcılık için);
koşucu `adim_haritasi {isim: fn}` verir. fn(soylem) -> herhangi değer;
soylam = {"is_id", "adim", "deneme", "ciktilar"}.
Yarım kalan adım en az-bir-kez koşabilir → adımlar IDEMPOTENT yazılmalı
(kuyruk bunu zorunlu kılamaz, sözleşmedir).
"""

import json
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KUYRUK_KOK = os.path.join(BASE, "data", "jobs")
KUYRUK_DOSYA = os.path.join(KUYRUK_KOK, "kuyruk.json")

BEKLIYOR = "bekliyor"
CALISIYOR = "calisiyor"
BITTI = "bitti"
HATALI = "hatali"

_kilit = threading.Lock()


def _varsayilan_sure_butcesi():
    """ayarlar.json'daki 'maksimum_gorev_suresi' (sn); yoksa 300."""
    try:
        from tools.permissions import _ayar_deger
        deger = _ayar_deger("maksimum_gorev_suresi", 300)
        return max(5, int(deger or 300))
    except Exception:
        return 300


def _simdi():
    return time.strftime("%Y-%m-%d %H:%M:%S")


class IsKuyrugu:
    """Kalıcı, adımlı iş kuyruğu — tek JSON, atomik yazım."""

    def __init__(self, dosya=None):
        self.dosya = dosya or KUYRUK_DOSYA
        self._yerel_kilit = threading.Lock()

    # ---------- saklama ----------

    def _oku(self):
        try:
            with open(self.dosya, "r", encoding="utf-8") as f:
                veri = json.load(f)
            if isinstance(veri, list):
                return veri
        except (OSError, ValueError):
            pass
        return []

    def _yaz(self, isler):
        os.makedirs(os.path.dirname(self.dosya), exist_ok=True)
        tmp = self.dosya + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(isler, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.dosya)          # atomik — çökme güvenli

    def _bul_ve_guncelle(self, is_id, guncelleme_fn):
        """Job'ı bulur, fn(job) uygular, TEK atomik yazımla saklar."""
        with self._yerel_kilit:
            isler = self._oku()
            for job in isler:
                if job.get("id") == is_id:
                    guncelleme_fn(job)
                    job["guncelleme"] = _simdi()
                    self._yaz(isler)
                    return job
        raise KeyError("İş bulunamadı: %s" % is_id)

    # ---------- genel API ----------

    def ekle(self, baslik, adimlar, maksimum_deneme=2,
             kullanici_onayi=True, onay_gerekli=False):
        """Yeni iş açar; durum='bekliyor', mevcut_adim=0."""
        with self._yerel_kilit:
            isler = self._oku()
            numaralar = [int(j["id"].split("-")[-1]) for j in isler
                         if str(j.get("id", "")).startswith("is-")]
            yeni_id = "is-%06d" % (max(numaralar, default=0) + 1)
            job = {
                "id": yeni_id,
                "baslik": (baslik or "")[:120],
                "adimlar": [str(a) for a in adimlar],
                "mevcut_adim": 0,           # sıradaki koşacak adım indeksi
                "calisan_adim": None,       # yarım kalmış adım (resume görür)
                "durum": BEKLIYOR,
                "maksimum_deneme": max(1, int(maksimum_deneme)),
                "deneme_sayisi": 0,
                "son_hata": None,
                "kullanici_onayi": bool(kullanici_onayi),
                "onay_gerekli": bool(onay_gerekli),
                "olusturma": _simdi(),
                "guncelleme": _simdi(),
            }
            isler.append(job)
            self._yaz(isler)
            return dict(job)

    def liste(self, durum=None):
        isler = self._oku()
        if durum:
            return [dict(j) for j in isler if j.get("durum") == durum]
        return [dict(j) for j in isler]

    def al(self, is_id):
        for job in self._oku():
            if job.get("id") == is_id:
                return dict(job)
        raise KeyError("İş bulunamadı: %s" % is_id)

    def onayla(self, is_id):
        def g(job):
            job["kullanici_onayi"] = True
        return self._bul_ve_guncelle(is_id, g)

    # ---------- koşum ----------

    def kos_bekleyenleri(self, adim_haritasi, sure_butcesi=None):
        """Bekleyen/yarım kalan işleri sırayla koşturur.

        sure_butcesi: bu çağrının toplam duvar saati bütçesi (sn).
        Bütçe dolarsa iş 'bekliyor' kalır — SONRAKİ çağrı kaldığı adımdan
        sürer ('kota açılınca devam' davranışının temeli).
        """
        butce = float(sure_butcesi) if sure_butcesi \
            else _varsayilan_sure_butcesi()
        t0 = time.time()
        rapor = {"kosulan_is": [], "bekletilen_is": [], "gecen_sn": 0.0}

        for job in self.liste():
            if time.time() - t0 >= butce:
                rapor["bekletilen_is"].append(
                    {"id": job["id"], "sebep": "sure_butcesi"})
                continue
            if job.get("durum") not in (BEKLIYOR, CALISIYOR):
                continue
            if job.get("onay_gerekli") and not job.get("kullanici_onayi"):
                rapor["bekletilen_is"].append(
                    {"id": job["id"], "sebep": "onay bekliyor"})
                continue

            sonuc = self._kos_tek(job["id"], adim_haritasi,
                                  t0, butce)
            rapor["kosulan_is"].append(sonuc)
            if time.time() - t0 >= butce:
                rapor["bekletilen_is"].append(
                    {"id": job["id"], "sebep": "sure_butcesi"})

        rapor["gecen_sn"] = round(time.time() - t0, 2)
        return rapor

    def _kos_tek(self, is_id, adim_haritasi, t0, butce):
        """Tek işin adımlarını bütçe dolana/hata/bitişe kadar koşturur."""
        eksik = [a for a in self.al(is_id)["adimlar"]
                 if a not in adim_haritasi]
        if eksik:
            return self._duraklat(is_id,
                                  "adım fonksiyonu yok: %s" % ", ".join(eksik))

        while True:
            job = self.al(is_id)

            if job["durum"] == BITTI:
                return {"id": is_id, "sonuc": BITTI}
            if job["durum"] == HATALI:
                return {"id": is_id, "sonuc": HATALI,
                        "son_hata": job.get("son_hata")}
            if time.time() - t0 >= butce:
                return self._duraklat(is_id, "sure_butcesi")

            idx = job["mevcut_adim"]
            if idx >= len(job["adimlar"]):
                def bitir(j):
                    j["durum"] = BITTI
                    j["calisan_adim"] = None
                self._bul_ve_guncelle(is_id, bitir)
                return {"id": is_id, "sonuc": BITTI}

            adim_adi = job["adimlar"][idx]
            deneme = job["deneme_sayisi"] + 1

            def baslat(j):
                j["durum"] = CALISIYOR
                j["calisan_adim"] = idx       # çökme olursa resume burayı görür
                j["deneme_sayisi"] = deneme
            self._bul_ve_guncelle(is_id, baslat)

            soylem = {"is_id": is_id, "adim": adim_adi,
                      "deneme": deneme,
                      "ciktilar": job.get("ciktilar", {})}

            try:
                cikti = adim_haritasi[adim_adi](soylem) or {}
            except Exception as e:
                hata = "%s: %s" % (type(e).__name__, str(e)[:150])
                if deneme < job["maksimum_deneme"]:
                    def yeniden_dene(j):
                        j["durum"] = BEKLIYOR      # aynı adım tekrar denenir
                        j["calisan_adim"] = None
                        j["son_hata"] = hata
                    self._bul_ve_guncelle(is_id, yeniden_dene)
                    logger.warning("İş %s adım '%s' deneme %d başarısız: %s",
                                   is_id, adim_adi, deneme, hata)
                    continue
                def hatali_kapat(j):
                    j["durum"] = HATALI
                    j["calisan_adim"] = None
                    j["son_hata"] = hata
                self._bul_ve_guncelle(is_id, hatali_kapat)
                return {"id": is_id, "sonuc": HATALI, "son_hata": hata}

            def ilerle(j):
                j["mevcut_adim"] = idx + 1          # ONAYLANDI — bir daha koşmaz
                j["calisan_adim"] = None
                j["son_hata"] = None
                j["deneme_sayisi"] = 0              # sayaç ADIM BAŞINA (hata düzeltmesi)
                ciktilar = j.setdefault("ciktilar", {})
                if isinstance(cikti, dict):
                    ciktilar[adim_adi] = {
                        k: v for k, v in cikti.items()
                        if isinstance(v, (str, int, float, bool, list))}
                else:
                    ciktilar[adim_adi] = {"ozet": str(cikti)[:200]}
            self._bul_ve_guncelle(is_id, ilerle)

    def _duraklat(self, is_id, sebep):
        def duraklat(j):
            if j["durum"] == CALISIYOR and j["calisan_adim"] is None:
                j["durum"] = BEKLIYOR
        try:
            self._bul_ve_guncelle(is_id, duraklat)
        except KeyError:
            pass
        return {"id": is_id, "sonuc": "bekletildi", "sebep": sebep}


def kuyruk_al(dosya=None):
    """Modül-seviye tekil erişim (chat/zamanlayıcı entegrasyonu için)."""
    global _tekil
    try:
        return _tekil
    except NameError:
        _tekil = IsKuyrugu(dosya)
    return _tekil
