"""Vercel canli akis sozlesmesi — gercek beyne/ag'a cikmadan."""

import asyncio
import json
import threading
import shutil
import subprocess

import pytest

from fastapi import Request
from fastapi.responses import StreamingResponse

import app as app_modulu


def _request(veri, accept=""):
    ham = json.dumps(veri).encode("utf-8")
    gonderildi = False

    async def receive():
        nonlocal gonderildi
        if not gonderildi:
            gonderildi = True
            return {"type": "http.request", "body": ham, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    headers = [(b"content-type", b"application/json")]
    if accept:
        headers.append((b"accept", accept.encode("ascii")))

    return Request({
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/api/sohbet",
        "raw_path": b"/api/sohbet",
        "query_string": b"",
        "headers": headers,
        "client": ("203.0.113.9", 4242),
        "server": ("testserver", 443),
    }, receive)


def _hazirla(monkeypatch, mesaj_isle):
    import chat.flow as flow
    import chat.kimlik as kimlik
    import chat.prompts as prompts

    monkeypatch.setattr(app_modulu, "_kimlik", lambda _r: "test-user")
    monkeypatch.setattr(app_modulu, "_cekirdek", lambda: (object(), []))
    monkeypatch.setattr(kimlik, "kullanici_kur", lambda _kid: None)
    monkeypatch.setattr(prompts, "kisilik_blogu", lambda *_a, **_k: "sistem")
    monkeypatch.setattr(flow, "mesaj_isle", mesaj_isle)


def _json_satir(parca):
    if isinstance(parca, bytes):
        parca = parca.decode("utf-8")
    return json.loads(parca.strip())


def test_stream_ilk_olayi_worker_bitmeden_verir(monkeypatch):
    devam = threading.Event()

    def sahte(_metin, _beyin, _sistem, js, _tools, **_kwargs):
        js("BasakUI.thinking()")
        js('BasakUI.toolStatus("İnternette aranıyor: deneme")')
        devam.wait(timeout=2)
        js('BasakUI.bitir("tamam", "sahte")')

    _hazirla(monkeypatch, sahte)

    async def senaryo():
        cevap = await app_modulu.sohbet(
            _request({"metin": "ara"}, "application/x-ndjson")
        )
        assert isinstance(cevap, StreamingResponse)
        it = cevap.body_iterator

        ilk = _json_satir(await asyncio.wait_for(anext(it), timeout=1))
        ikinci = _json_satir(await asyncio.wait_for(anext(it), timeout=1))
        assert not devam.is_set()
        assert ilk["tur"] == "thinking"
        assert ikinci["tur"] == "toolStatus"

        devam.set()
        kalan = []
        async for parca in it:
            kalan.append(_json_satir(parca))
        return kalan

    kalan = asyncio.run(senaryo())
    assert any(o.get("tur") == "bitir" and o.get("cevap") == "tamam"
               for o in kalan)


def test_bitir_gorunur_ama_worker_bitmeden_stream_kapanmaz(monkeypatch):
    son_is = threading.Event()
    bitirebilir = threading.Event()

    def sahte(_metin, _beyin, _sistem, js, _tools, **_kwargs):
        js("BasakUI.thinking()")
        js('BasakUI.bitir("cevap", "sahte")')
        son_is.set()
        bitirebilir.wait(timeout=2)

    _hazirla(monkeypatch, sahte)

    async def senaryo():
        cevap = await app_modulu.sohbet(
            _request({"metin": "x"}, "application/x-ndjson")
        )
        it = cevap.body_iterator
        assert _json_satir(await anext(it))["tur"] == "thinking"
        bitis = _json_satir(await anext(it))
        assert bitis["tur"] == "bitir"
        assert son_is.is_set()

        sonraki = asyncio.create_task(anext(it))
        await asyncio.sleep(0.05)
        assert not sonraki.done(), "worker bitmeden stream kapandi"
        bitirebilir.set()
        try:
            await asyncio.wait_for(sonraki, timeout=1)
        except StopAsyncIteration:
            pass

    asyncio.run(senaryo())


def test_stream_worker_hatasi_error_olayi_olur(monkeypatch):
    def patla(*_a, **_k):
        raise RuntimeError("deneme patlamasi")

    _hazirla(monkeypatch, patla)

    async def senaryo():
        cevap = await app_modulu.sohbet(
            _request({"metin": "x"}, "application/x-ndjson")
        )
        return [_json_satir(p) async for p in cevap.body_iterator]

    olaylar = asyncio.run(senaryo())
    assert olaylar[-1]["tur"] == "error"
    assert "deneme patlamasi" in olaylar[-1]["metin"]


def test_accept_yoksa_eski_toplu_json_korunur(monkeypatch):
    def sahte(_metin, _beyin, _sistem, js, _tools, **_kwargs):
        js("BasakUI.thinking()")
        js('BasakUI.bitir("eski yol", "sahte")')

    _hazirla(monkeypatch, sahte)
    cevap = asyncio.run(app_modulu.sohbet(_request({"metin": "x"})))
    assert isinstance(cevap, dict)
    assert cevap["ok"] is True
    assert cevap["cevap"] == "eski yol"
    assert [o["tur"] for o in cevap["olaylar"]] == ["thinking", "bitir"]


def test_vercel_suresi_300():
    veri = json.load(open("vercel.json", encoding="utf-8"))
    assert veri["functions"]["app.py"]["maxDuration"] == 300


def test_vercel_durum_canli_tasimayi_bildirir():
    metin = open("app.py", encoding="utf-8").read()
    assert '"tasima": "canli-ndjson"' in metin


def test_web_stream_sozlesmesi_ve_gecmis_ham_cevabi_korur():
    ekran = open("web/app.js", encoding="utf-8").read()
    assert '"accept":"application/x-ndjson"' in ekran
    assert "r.body.getReader()" in ekran
    assert "new TextDecoder()" in ekran
    assert "canliYanitiOku" in ekran
    assert "olayiIsle(o)" in ekran
    assert 'content:sonuc.cevap' in ekran
    assert "Mesaj Başak’a iletiliyor…" in ekran
    assert "Düşünüyorum…" in ekran


def test_web_javascript_sozdizimi_gecerli():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js bu ortamda yok")
    sonuc = subprocess.run(
        [node, "--check", "web/app.js"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert sonuc.returncode == 0, sonuc.stderr or sonuc.stdout



def _node_kos(script):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js bu ortamda yok")
    sonuc = subprocess.run(
        [node, "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert sonuc.returncode == 0, sonuc.stderr or sonuc.stdout


def test_web_jsonl_parser_network_parcalarinda_bolunse_de_calismali():
    ekran = open("web/app.js", encoding="utf-8").read()
    bas = ekran.index("async function canliYanitiOku")
    son = ekran.index("\n\nasync function jsonOku", bas)
    fonksiyon = ekran[bas:son]

    script = r"""
const olaylar = [];
function olayiBaslangicBalonunaBagla(_o, _b) {}
function olayiIsle(o) { olaylar.push(o); }
""" + fonksiyon + r"""
(async () => {
  const metin =
    '{"istek":"abc","tur":"thinking"}\n' +
    '{"istek":"abc","tur":"toolStatus","metin":"İnternette aranıyor: deneme"}\n' +
    '{"istek":"abc","tur":"parca","metin":"Mer"}\n' +
    '{"istek":"abc","tur":"parca","metin":"haba"}\n' +
    '{"istek":"abc","tur":"bitir","cevap":"Merhaba","kaynak":"sahte"}\n';

  const tum = new TextEncoder().encode(metin);
  const sinirlar = [1, 4, 9, 17, 29, 43, 58, 73, 91, 117, 149, tum.length];
  const parcalar = [];
  let onceki = 0;
  for (const s of sinirlar) {
    const bitis = Math.min(s, tum.length);
    if (bitis > onceki) parcalar.push(tum.slice(onceki, bitis));
    onceki = bitis;
  }
  if (onceki < tum.length) parcalar.push(tum.slice(onceki));

  let i = 0;
  const r = {
    body: {
      getReader() {
        return {
          async read() {
            if (i >= parcalar.length) return { value: undefined, done: true };
            return { value: parcalar[i++], done: false };
          }
        };
      }
    }
  };

  const sonuc = await canliYanitiOku(r, {});
  const turler = olaylar.map(o => o.tur).join(",");
  if (turler !== "thinking,toolStatus,parca,parca,bitir") {
    throw new Error("olay sirasi bozuk: " + turler);
  }
  if (!sonuc.ok || sonuc.cevap !== "Merhaba" || sonuc.kaynak !== "sahte") {
    throw new Error("final sonuc bozuk: " + JSON.stringify(sonuc));
  }
})().catch(e => { console.error(e); process.exit(1); });
"""
    _node_kos(script)


def test_web_ui_gercek_olaylari_detayli_gosterir_ve_sirlari_maskeler():
    ekran = open("web/app.js", encoding="utf-8").read()

    gb = ekran.index("function guvenliDurumBilgisi")
    gs = ekran.index("\n\nfunction calismaKaydi", gb)
    guvenli = ekran[gb:gs]

    ob = ekran.index("function olayiIsle(o)")
    os = ekran.index("\n\nfunction olayiBaslangicBalonunaBagla", ob)
    olay_isle = ekran[ob:os]

    script = r"""
const balonlar = new Map();
const durumlar = [];
const yazilar = [];
let kapatildi = 0;

function bubble(_role, text) {
  return {
    dataset: { ham: String(text || "") },
    querySelector() { return null; },
    closest() { return null; },
    remove() {}
  };
}
function durumSatiri(b, metin) {
  const gorunen = guvenliDurum(metin);
  b.durum = gorunen;
  durumlar.push(gorunen);
}
function durumuKapat(b) {
  delete b.durum;
  kapatildi += 1;
}
function calismaYanitaGecti(b) {
  durumuKapat(b);
}
function calismaBitir(b) {
  durumuKapat(b);
}
function icerikYaz(b, metin) {
  b.dataset.ham = String(metin || "");
  yazilar.push(b.dataset.ham);
}
function sohbetAlta() {}
""" + guvenli + "\n" + olay_isle + r"""

const b = bubble("assistant", "");
balonlar.set("abc", b);

olayiIsle({istek:"abc", tur:"thinking"});
if (b.durum !== "Düşünüyorum…") {
  throw new Error("thinking görünmedi: " + b.durum);
}

olayiIsle({
  istek:"abc",
  tur:"toolStatus",
  metin:"İnternette aranıyor: GPT-5.6 güncel gelişmeler"
});
if (b.durum !== "İnternette aranıyor — GPT-5.6 güncel gelişmeler") {
  throw new Error("arama detayı görünmedi: " + b.durum);
}

olayiIsle({
  istek:"abc",
  tur:"toolStatus",
  metin:"Sayfa okunuyor: https://ornek.test/haber/123?token=GIZLI&lang=tr"
});
if (b.durum !== "Sayfa okunuyor — ornek.test/haber/123") {
  throw new Error("sayfa detayı yanlış: " + b.durum);
}
if (durumlar.some(x => x.includes("GIZLI"))) {
  throw new Error("gizli token kullanıcıya sızdı");
}

olayiIsle({
  istek:"abc",
  tur:"toolStatus",
  metin:"Dosya okunuyor: C:\\\\Users\\\\furkan\\\\proje\\\\rapor.txt"
});
if (!b.durum.endsWith("…/proje/rapor.txt")) {
  throw new Error("dosya bağlamı güvenli gösterilmedi: " + b.durum);
}
if (b.durum.includes("Users") || b.durum.includes("furkan")) {
  throw new Error("tam yerel dosya yolu kullanıcıya sızdı");
}

olayiIsle({istek:"abc", tur:"parca", metin:"Mer"});
olayiIsle({istek:"abc", tur:"parca", metin:"haba"});
if (b.dataset.ham !== "Merhaba") {
  throw new Error("parçalar birleşmedi: " + b.dataset.ham);
}

olayiIsle({istek:"abc", tur:"bitir", cevap:"Merhaba", kaynak:"sahte"});
if (b.dataset.ham !== "Merhaba") {
  throw new Error("bitir cevabı bozdu: " + b.dataset.ham);
}
if (balonlar.has("abc")) {
  throw new Error("bitir sonrası istek balonu temizlenmedi");
}
if (kapatildi < 1) {
  throw new Error("canlı durum finalde kapanmadı");
}
"""
    _node_kos(script)


def test_web_bitirden_sonra_baglanti_koparsa_final_cevap_korunur():
    ekran = open("web/app.js", encoding="utf-8").read()
    bas = ekran.index("async function canliYanitiOku")
    son = ekran.index("\n\nasync function jsonOku", bas)
    fonksiyon = ekran[bas:son]

    script = r"""
const olaylar = [];
function olayiBaslangicBalonunaBagla(_o, _b) {}
function olayiIsle(o) { olaylar.push(o); }
""" + fonksiyon + r"""
(async () => {
  const veri = new TextEncoder().encode(
    '{"istek":"abc","tur":"bitir","cevap":"Korunan cevap","kaynak":"sahte"}\n'
  );
  let sira = 0;
  const r = {
    body: {
      getReader() {
        return {
          async read() {
            if (sira++ === 0) return { value: veri, done: false };
            throw new Error("bitir sonrasi baglanti koptu");
          }
        };
      }
    }
  };
  const sonuc = await canliYanitiOku(r, {});
  if (!sonuc.ok || sonuc.cevap !== "Korunan cevap") {
    throw new Error("final cevap korunmadi: " + JSON.stringify(sonuc));
  }
})().catch(e => { console.error(e); process.exit(1); });
"""
    _node_kos(script)


def test_uzun_is_sirasinda_sohbet_degistirme_engeli_var():
    ekran = open("web/app.js", encoding="utf-8").read()
    ac = ekran.split("function sohbetiAc(id)", 1)[1].split(
        "\n}\n\nconst durumSaatleri", 1
    )[0]
    yeni = ekran.split("async function yeniSohbet()", 1)[1].split(
        "\n}\n\nfor (const id", 1
    )[0]
    assert "if (gonderiliyor)" in ac
    assert "if (gonderiliyor)" in yeni


def test_preview_calisma_karti_sozlesmesi():
    ekran = open("web/app.js", encoding="utf-8").read()
    stil = open("web/chat.css", encoding="utf-8").read()

    assert "function calismaKaydi" in ekran
    assert "function aktifAdimiTamamla" in ekran
    assert "function calismaBitir" in ekran
    assert "function calismaDurdur" in ekran
    assert 'detaylar.textContent = "Detaylar"' in ekran
    assert 'durdur.textContent = "Durdur"' in ekran
    assert '" adım tamamlandı"' in ekran
    assert "new AbortController()" in ekran
    assert "signal:aktifIstekDenetleyici.signal" in ekran

    assert ".work-card{" in stil
    assert ".work-current-detail{" in stil
    assert ".work-details{" in stil
    assert ".work-stop{" in stil
    assert "@media(prefers-reduced-motion:reduce)" in stil
    assert "min-height:40px" in stil


def test_preview_durdur_backend_iptal_bayragini_tasir():
    kaynak = open("app.py", encoding="utf-8").read()
    assert "class _AkisIptal(Exception)" in kaynak
    assert "threading.Event() if akis else None" in kaynak
    assert "if self.iptal_edildi():" in kaynak
    assert "except _AkisIptal:" in kaynak
    assert "_canli_olaylar(kuyruk, gorev, kayit.istek, iptal)" in kaynak


def test_stream_generator_kapaninca_worker_iptal_bayragi_set_edilir():
    import asyncio
    import threading

    async def senaryo():
        kuyruk = asyncio.Queue()
        iptal = threading.Event()
        worker = asyncio.create_task(asyncio.sleep(30))
        akis = app_modulu._canli_olaylar(
            kuyruk, worker, "iptal-test", iptal
        )
        ilk = asyncio.create_task(akis.__anext__())
        await asyncio.sleep(0)
        ilk.cancel()
        try:
            await ilk
        except BaseException:
            pass
        worker.cancel()
        try:
            await worker
        except BaseException:
            pass
        return iptal.is_set()

    assert asyncio.run(senaryo()) is True
