"""tests/test_web_akis_kesilme.py — akis yarida kesilince dogru sebep soylenir.

P2 onizleme (2026-09-25): sunucu 300 sn'de isi durdurunca son satir yarim
kaldi; web/app.js onu JSON sanip "Başak canlı akışında geçersiz veri
alındı." dedi. Bu testler canliYanitiOku'yu Node'un gercek ReadableStream'i
ile calistirir (tarayici ile ayni Web Streams API'si).
"""

import json
import pathlib
import re
import shutil
import subprocess
import tempfile

import pytest

KOK = pathlib.Path(__file__).resolve().parents[1]
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node yok")


def _fonksiyon_kaynagi():
    js = (KOK / "web" / "app.js").read_text(encoding="utf-8")
    m = re.search(
        r"(const KESILME_SURE_ESIGI_MS[\s\S]*?)\nasync function jsonOku",
        js)
    if m is None:
        # Eski kodda esik sabiti yok; fonksiyonu tek basina al.
        m = re.search(
            r"(async function canliYanitiOku[\s\S]*?)\nasync function jsonOku",
            js)
    return m.group(1)


def _kos(parcalar, gecen_ms=0, abort=False):
    betik = """
const olayiBaslangicBalonunaBagla = () => {};
const olayiIsle = () => false;
let _simdi = 1000;
const _gercekNow = Date.now;
Date.now = () => _simdi;
%(kaynak)s
const parcalar = %(parcalar)s;
const kodla = new TextEncoder();
const akis = new ReadableStream({
  pull(c) {
    if (parcalar.length) { c.enqueue(kodla.encode(parcalar.shift())); return; }
    _simdi += %(gecen)d;
    if (%(abort)s) {
      const e = new Error("iptal"); e.name = "AbortError"; c.error(e); return;
    }
    c.close();
  }
});
canliYanitiOku({ body: akis }, null).then(
  s => console.log(JSON.stringify({ ok: true, sonuc: s })),
  e => console.log(JSON.stringify({ ok: false, ad: e.name, mesaj: e.message })),
);
""" % {
        "kaynak": _fonksiyon_kaynagi(),
        "parcalar": json.dumps(parcalar),
        "gecen": gecen_ms,
        "abort": "true" if abort else "false",
    }
    # Windows'ta varsayilan kodlama cp1252: betik dosyaya UTF-8 yazilir,
    # cikti UTF-8 olarak cozulur (Node stdout'u her zaman UTF-8 yazar).
    with tempfile.TemporaryDirectory() as klasor:
        dosya = pathlib.Path(klasor) / "akis_testi.js"
        dosya.write_text(betik, encoding="utf-8")
        cikti = subprocess.run(
            [NODE, str(dosya)], capture_output=True, encoding="utf-8",
            timeout=30)
    assert cikti.returncode == 0, cikti.stderr
    return json.loads(cikti.stdout.strip().splitlines()[-1])


def test_yarim_son_satir_gecersiz_veri_degil_kesilmedir():
    s = _kos(['{"tur":"ping"}\n', '{"tur":"parca","metin":"yar'])
    assert s["ok"] is False
    assert "geçersiz veri" not in s["mesaj"]
    assert s["mesaj"] == "Başak yanıtı tamamlanmadan bağlantı kapandı."


def test_sure_dolunca_sebep_soylenir():
    s = _kos(['{"tur":"ping"}\n', '{"tur":"parca"'], gecen_ms=300_000)
    assert s["ok"] is False
    assert "5 dakikalık çalışma süresini doldurdu" in s["mesaj"]


def test_satir_sonsuz_tam_bitir_normal_islenir():
    s = _kos(['{"tur":"bitir","cevap":"tamam","kaynak":"groq"}'])
    assert s["ok"] is True
    assert s["sonuc"]["cevap"] == "tamam"


def test_akis_ortasindaki_bozuk_satir_hata_olarak_kalir():
    s = _kos(['bozuk\n', '{"tur":"bitir","cevap":"x"}\n'])
    assert s["ok"] is False
    assert s["mesaj"] == "Başak canlı akışında geçersiz veri alındı."


def test_durdur_iptali_aynen_iletilir():
    s = _kos(['{"tur":"ping"}\n'], abort=True)
    assert s["ok"] is False
    assert s["ad"] == "AbortError"


def test_mola_olayi_hata_degil_karar_bekler():
    s = _kos(['{"tur":"ping"}\n', '{"tur":"checkpoint","adim":3}\n'])
    assert s["ok"] is True
    assert s["sonuc"]["mola"] is True
    assert s["sonuc"]["ok"] is False
