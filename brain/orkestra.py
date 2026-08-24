"""brain/orkestra.py — ORKESTRA: 10 durumlu muhakeme iskeleti.

Kilitli hedefin merkezi. Tasarim: defter/orkestra-0-tasarim.md

ILKELER:
- mesaj_isle yeniden yazilmaz; Orkestra dogrulanmis parcalari durumlarina
  baglayan acik cercevedir. Bilesenler disaridan enjekte edilir.
- Her kosum IZ birakir: {durum, atlandi, sebep, ozet} — sessiz atlama yasak.
- Uretim anahtari sonra: once gölge mod/eşdeğerlik kanıtı.

v1 (2026-08-24, ORKESTRA-1): DIVERSIFY ve CRITICIZE dolduruldu.
- DIVERSIFY: OPSIYONEL "ek_adaylar" bileseni varsa birincilden BASKA
  saglayicilar PARALEL olarak ayni soruyu yanıtlar (FAY-1 ruhu).
  Bilesen yoksa v0 davranisi aynen korunur (izde sebep bildirilir).
- CRITICIZE: OPSIYONEL "aday_puanla" bileseni adaylara DETERMINISTIK
  puan verir (kapı hükmi; yapay zeka yorumu YOK — OLCU ilkesi).
  Varsayilan puan: bos/"ölçemedim" adayı eler, digerleri eşittir.
- SELECT: en yüksek puani alan kazanir; eşitlikte BIRINCIL kazanir.
  Kazananin kaynak bilgisi rapora tasinir.

Kullanim:
    o = Orkestra(bilesenler)
    rapor = o.kos(soru)
    rapor["cevap"], rapor["iz"]
"""

import logging
import threading
from enum import Enum

logger = logging.getLogger(__name__)

YEDEK_CUMLE = "Bunu ölçemedim."


class Durum(Enum):
    OBSERVE = "OBSERVE"
    MODEL = "MODEL"
    QUESTION = "QUESTION"
    HYPOTHESIZE = "HYPOTHESIZE"
    DIVERSIFY = "DIVERSIFY"
    CRITICIZE = "CRITICIZE"
    EXPERIMENT = "EXPERIMENT"
    MEASURE = "MEASURE"
    SELECT = "SELECT"
    LEARN = "LEARN"


_GEREKLI_BILESENLER = (
    "observe",           # soru -> (temiz_metin, konusmaci)
    "model_baglami",     # -> str (bilgi + notlar bloğu)
    "anilar",            # soru -> [ {...}, ... ]
    "gecmis_pencere",    # gecmis -> pencere listesi
    "siniflandir",       # metin -> gorev tipi
    "dinamik_araclar",   # (metin, tools) -> sunulacak arac seti
    "aday_uret",         # (mesajlar, araclar) -> (yanit_dict, kaynak)
    "deney_kos",         # (tool_calls, mesajlar) -> (cevap, arac_ciktilari)|None
    "olcu_kapisi",       # (metin, olcumler) -> (temiz, rapor)
    "ham_olcum",         # olcumler -> satir listesi
    "ogren",             # (soru, cevap, onem) -> None
)

# Opsiyonel bilesenler (ORKESTRA-1): yoksa ilgili durum v0 gibi ATLANDI
# kaydiyla gecer — davranis degismez.
_OPSIYONEL = ("ek_adaylar", "aday_puanla")


class Orkestra:
    """Durum makinesi çerçevesi — parçalar enjekte edilir."""

    def __init__(self, bilesenler):
        eksik = [a for a in _GEREKLI_BILESENLER if a not in bilesenler]
        if eksik:
            raise ValueError("Eksik bilesenler: %s" % ", ".join(eksik))
        self.b = bilesenler
        self.iz = []
        self.kaynak = ""

    # ---------- yardimcilar ----------

    def _adim(self, durum, atlandi=False, sebep="", ozet=""):
        self.iz.append({"durum": durum.value, "atlandi": atlandi,
                        "sebep": sebep, "ozet": ozet[:120]})

    @staticmethod
    def _icerik(yanit):
        return yanit.get("content") if isinstance(yanit, dict) \
            else str(yanit or "")

    @staticmethod
    def _tool_calls(yanit):
        return yanit.get("tool_calls") if isinstance(yanit, dict) else None

    # ---------- kosum ----------

    def kos(self, soru, gecmis=None, tools=None, onem=1, sistem="SYS"):
        """Soruyu durum makinesinden gecirir; rapor dondurur.

        sistem: modele giden kisilik/kural promptu (uretimde KISILIK).
        v0'da sabit "SYS" kalmisti — ana yola geciste kimlik kaybini
        onlemek icin tasinabilir yapildi.
        """
        self.iz = []

        # --- OBSERVE ---
        temiz, konusmaci = self.b["observe"](soru)
        self._adim(Durum.OBSERVE,
                   ozet="konusmaci=%s" % (konusmaci or "-"))
        if not temiz:
            return {"hata": "Bos mesaj", "iz": self.iz}

        # --- MODEL ---
        baglam = self.b["model_baglami"]()
        anilar = self.b["anilar"](temiz)
        pencere = self.b["gecmis_pencere"](gecmis or [])
        self._adim(Durum.MODEL,
                   ozet="baglam=%d kr, ani=%d, gecmis=%d"
                        % (len(baglam), len(anilar), len(pencere)))

        # --- QUESTION ---
        tip = self.b["siniflandir"](temiz)
        aktif_araclar = self.b["dinamik_araclar"](temiz.lower(), tools or [])
        self._adim(Durum.QUESTION,
                   ozet="tip=%s, arac=%d" % (tip, len(aktif_araclar)))

        # --- HYPOTHESIZE (birincil aday) ---
        mesajlar = [{"role": "system", "content": sistem}]
        if baglam:
            mesajlar.append({"role": "system",
                             "content": "Notlar:\n" + baglam})
        for a in anilar:
            mesajlar.append({"role": "system",
                             "content": "Ani: " + a.get("text", "")[:500]})
        mesajlar += pencere + [{"role": "user", "content": temiz}]
        try:
            yanit, kaynak = self.b["aday_uret"](mesajlar, aktif_araclar)
        except Exception as e:
            self._adim(Durum.HYPOTHESIZE, ozet="hata")
            return {"hata": str(e)[:150], "iz": self.iz}
        self.kaynak = kaynak
        self._adim(Durum.HYPOTHESIZE, ozet="kaynak=%s" % kaynak)

        # Aday havuzu: [(etiket, kaynak, yanit)] — birincil hep ilk sırada
        adaylar = [("birincil", kaynak, yanit)]

        # --- DIVERSIFY (v1: opsiyonel paralel ek adaylar) ---
        if "ek_adaylar" in self.b:
            try:
                alternatifler = self.b["ek_adaylar"](
                    self.kaynak, mesajlar,
                    arac_var=bool(self._tool_calls(yanit)))
            except Exception as e:
                logger.warning("ek_adaylar hatasi: %s", e)
                alternatifler = None
            if alternatifler is None:
                self._adim(Durum.DIVERSIFY, atlandi=True,
                           sebep="juri kurulum hatasi")
            elif not alternatifler:
                self._adim(Durum.DIVERSIFY, atlandi=True,
                           sebep="juri bileşeni var ama uygun aday yok "
                                 "(anahtar kapali/kota/tek saglayici)")
            else:
                sonuclar = []
                kilit = threading.Lock()

                def _kos(ad_fn):
                    ad, fn = ad_fn
                    try:
                        r = fn(mesajlar)
                    except Exception as e:
                        logger.warning("Juri adadi %s hata verdi: %s", ad, e)
                        r = None
                    with kilit:
                        sonuclar.append((ad, r))

                threads = [threading.Thread(target=_kos, args=(af,))
                           for af in alternatifler]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

                gelen = [(ad, r) for ad, r in sonuclar if r is not None]
                gelen.sort(key=lambda x: x[0])
                for ad, r in gelen:
                    adaylar.append((ad, ad, r))
                self._adim(Durum.DIVERSIFY,
                           ozet="%d ek aday (%s)"
                                % (len(gelen),
                                   ", ".join(ad for ad, _ in gelen)))
        else:
            self._adim(Durum.DIVERSIFY, atlandi=True,
                       sebep="tek aday yeterli; FAY-1 bekleniyor")

        # --- CRITICIZE (v1: deterministik puan; AI yorumu YOK) ---
        # Adayların ŞU ANKİ metni kapıdan geçirilip puanlanır. Araçsız
        # adayların metni burada nihaidir; araçlı adaylar EXPERIMENT
        # sonrası yeniden değerlendirilir.
        olcumler_map = {}      # etiket -> arac_ciktilari

        def _varsayilan_puan(tem, elenen):
            # Bos / tamamen elenmis aday elenir; digerleri esittir.
            if not tem or tem.strip() == YEDEK_CUMLE:
                return -50
            return 0

        puanla = self.b.get("aday_puanla", _varsayilan_puan)
        skorlar = {}
        for etiket, _, yanit_a in adaylar:
            tem = self._icerik(yanit_a)
            try:
                _, kapi_raporu = self.b["olcu_kapisi"](
                    tem, olcumler_map.get(etiket, []))
                skorlar[etiket] = puanla(tem, len(kapi_raporu))
            except Exception as e:
                logger.warning("aday_puanla hatasi (%s): %s", etiket, e)
                skorlar[etiket] = -100
        ozet = ", ".join("%s=%s" % (o[0], skorlar.get(o[0]))
                         for o in adaylar)
        self._adim(Durum.CRITICIZE, ozet="puan: " + ozet)

        # --- EXPERIMENT (aday basina; yetki tavani QUESTION'da sabit) ---
        deney_kosan = 0
        tool_cagiran = False
        for i, (etiket, kyk, yanit_a) in enumerate(adaylar):
            tool_calls = self._tool_calls(yanit_a)
            if not tool_calls:
                continue
            tool_cagiran = True
            deney_sonucu = self.b["deney_kos"](tool_calls, mesajlar)
            if deney_sonucu:
                cevap, olc = deney_sonucu
                adaylar[i] = (etiket, kyk, {"content": cevap})
                olcumler_map[etiket] = olc
                deney_kosan += 1
                # Araç cevabını değiştirdi → puanı tazele
                yeni_tem = self._icerik(adaylar[i][2])
                try:
                    _, kr = self.b["olcu_kapisi"](yeni_tem, olc)
                    skorlar[etiket] = puanla(yeni_tem, len(kr))
                except Exception:
                    pass
        if deney_kosan:
            self._adim(Durum.EXPERIMENT,
                       ozet="%d adayda arac kostu" % deney_kosan)
        elif tool_cagiran:
            self._adim(Durum.EXPERIMENT, atlandi=True,
                       sebep="dongu kapandi")
        else:
            self._adim(Durum.EXPERIMENT, atlandi=True,
                       sebep="arac cagrisi yok")

        # --- MEASURE (nihai geçiş: her aday kapıdan bir kez daha) ---
        olculen = []           # [etiket, kaynak, temiz, elenen_sayisi]
        for etiket, kyk, yanit_a in adaylar:
            ham_metin = self._icerik(yanit_a)
            temiz_cevap, kapi_raporu = self.b["olcu_kapisi"](
                ham_metin, olcumler_map.get(etiket, []))
            olculen.append([etiket, kyk, temiz_cevap,
                            len(kapi_raporu)])
        toplam_elenen = sum(o[3] for o in olculen)
        self._adim(Durum.MEASURE,
                   ozet="aday=%d, kapidan gecen=%d, elenen=%d"
                        % (len(olculen),
                           sum(1 for o in olculen if o[2]), toplam_elenen))

        # --- SELECT ---
        # max ilk maksimumu alir; birincil listede ilk sirada oldugundan
        # esitlikte birincil kazanir — v0 davranisi varsayilan olarak korunur.
        en_iyi = max(olculen,
                     key=lambda o: (skorlar.get(o[0], -100), -o[3]))
        kazanan_etiket, kazanan_kaynak, kazanan_temiz, _ = en_iyi
        if kazanan_temiz == YEDEK_CUMLE \
                and olcumler_map.get(kazanan_etiket):
            satirlar = self.b["ham_olcum"](olcumler_map[kazanan_etiket])
            if satirlar:
                kazanan_temiz = "\n".join(satirlar)
        self.kaynak = kazanan_kaynak
        self._adim(Durum.SELECT,
                   ozet="kazanan=%s (%d kr)" % (kazanan_etiket,
                                                len(kazanan_temiz)))

        # --- LEARN ---
        self.b["ogren"](temiz, kazanan_temiz, onem)
        self._adim(Durum.LEARN, ozet="episodic+karneler")

        return {"cevap": kazanan_temiz, "iz": self.iz,
                "kaynak": self.kaynak, "konusmaci": konusmaci}
