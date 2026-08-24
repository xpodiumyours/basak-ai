"""brain/orkestra.py — ORKESTRA-0: 10 durumlu muhakeme iskeleti.

Kilitli hedefin merkezi. Tasarim: defter/orkestra-0-tasarim.md

ILKELER:
- mesaj_isle yeniden yazilmaz; Orkestra dogrulanmis parcalari durumlarina
  baglayan acik cercevedir. Bilesenler disaridan enjekte edilir.
- Her kosum IZ birakir: {durum, atlandi, sebep, ozet} — sessiz atlama yasak.
- v0 davranisi bugunku akisla esdegerdir; yeni yetenekler sonraki
  dilimlerde durumlarin icine eklenir (DIVERSIFY=FAY-1 jürisi vb).
- Uretim anahtari sonra: once gölge mod/eşdeğerlik kanıtı.

Kullanim:
    o = Orkestra(bilesenler)
    rapor = o.kos(soru)
    rapor["cevap"], rapor["iz"]
"""

from enum import Enum


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
    "deney_kos",         # (tool_calls) -> (cevap, arac_ciktilari) | None
    "olcu_kapisi",       # (metin, olcumler) -> (temiz, rapor)
    "ham_olcum",         # olcumler -> satir listesi
    "ogren",             # (soru, cevap, onem) -> None
)


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

    # ---------- kosum ----------

    def kos(self, soru, gecmis=None, tools=None, onem=1):
        """Soruyu durum makinesinden gecirir; rapor dondurur."""
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

        # --- HYPOTHESIZE (v0: tek aday) ---
        mesajlar = [{"role": "system", "content": "SYS"}]
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

        # --- DIVERSIFY (v0: atlandi — FAY-1 jürisi bekler) ---
        self._adim(Durum.DIVERSIFY, atlandi=True,
                   sebep="tek aday yeterli; FAY-1 bekleniyor")

        # --- CRITICIZE (v0: atlandi — FAY hattı bekler) ---
        self._adim(Durum.CRITICIZE, atlandi=True,
                   sebep="yerini olcu kapisi tutuyor; FAY-1 bekleniyor")

        # --- EXPERIMENT ---
        tool_calls = yanit.get("tool_calls") if isinstance(yanit, dict) \
            else None
        olcumler = []
        if tool_calls:
            deney_sonucu = self.b["deney_kos"](tool_calls)
            if deney_sonucu:
                cevap, olcumler = deney_sonucu
                yanit = {"content": cevap}
                self._adim(Durum.EXPERIMENT,
                           ozet="%d arac kostu" % len(tool_calls))
            else:
                self._adim(Durum.EXPERIMENT, atlandi=True,
                           sebep="dongu kapandi")
        else:
            self._adim(Durum.EXPERIMENT, atlandi=True,
                       sebep="arac cagrisi yok")

        # --- MEASURE ---
        ham_metin = yanit.get("content") if isinstance(yanit, dict) \
            else str(yanit or "")
        temiz_cevap, kapi_raporu = self.b["olcu_kapisi"](ham_metin,
                                                         olcumler)
        self._adim(Durum.MEASURE,
                   ozet="kapidan gecen=%d kr, elenen=%d"
                        % (len(temiz_cevap), len(kapi_raporu)))

        # --- SELECT (v0: tek aday; kapi bos ise ham olcum) ---
        if temiz_cevap == "Bunu ölçemedim." and olcumler:
            satirlar = self.b["ham_olcum"](olcumler)
            temiz_cevap = ("\n".join(satirlar)) if satirlar else temiz_cevap
        self._adim(Durum.SELECT, ozet="secildi (%d kr)"
                                        % len(temiz_cevap))

        # --- LEARN ---
        self.b["ogren"](temiz, temiz_cevap, onem)
        self._adim(Durum.LEARN, ozet="episodic+karneler")

        return {"cevap": temiz_cevap, "iz": self.iz,
                "kaynak": self.kaynak, "konusmaci": konusmaci}
