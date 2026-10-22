"""tests/test_durum_js_calisir.py — durum sayfası GERÇEKTEN çalışıyor mu?

2026-10-21'de bulunan hata (Casper'in "vibe coding mi?" sorusunun cevabı):
`web/durum.js` içinde iki ayrı fonksiyon `satirEkle` adını taşıyordu.
JavaScript'te ikinci tanım birincisini SİLER. Sonuç: sayfa açılır açılmaz
"kutu.appendChild is not a function" patlaması veriyordu — yani kanıt
sayfası, tam da "çalışıyor mu" dediği anda çöken bir sayfaydı.

Bu test iki şeyi kalıcı kılar:

1. SÖZDİZİMİ: her web/eklenti betiği `node --check` ile taranır.
2. ÇALIŞMA: `web/durum.js` sahte bir tarayıcı (mini DOM) içinde GERÇEKTEN
   çalıştırılır. Sayfa kendi uçlarına istek atar; sahte sunucu cevap verir.
   Sayfa çökerse (istisna) test kırmızıya döner; render edilen satırlar
   kontrol edilir.

Sözleşme:
- Test ağa çıkmaz; sahte fetch/ WebSocket ile tamamen çevrimdışıdır.
- "Ölçülemeyen şey yeşil yazılmaz": bir kontrol satırı eksikse test kırmızı.
- Aynı isimli iki fonksiyon (sessiz ezme) statik taramayla yakalanır.
"""

import os
import re
import shutil
import subprocess
import sys

import pytest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js bu ortamda yok")


def _betik_klasoru():
    """Taranacak betik dosyaları (web/ + eklenti/)."""
    dosyalar = []
    for klasor in ("web", "eklenti"):
        yol = os.path.join(KOK, klasor)
        if not os.path.isdir(yol):
            continue
        for ad in sorted(os.listdir(yol)):
            if ad.endswith(".js"):
                dosyalar.append(os.path.join(klasor, ad))
    return dosyalar


# ── 1. Sözdizimi kapısı ───────────────────────────────────────────────


def test_her_web_betiği_sözdizimi_gecerli():
    """Bir betik parse edilemiyorsa o sayfa çöker; kapı kırmızıya döner."""
    hatalar = []
    for yol in _betik_klasoru():
        sonuc = subprocess.run(
            [NODE, "--check", os.path.join(KOK, yol)],
            capture_output=True, text=True, timeout=30,
            # KODLAMASI AÇIK: Windows CI'da varsayılan kodlama cp1252'dir;
            # metin=True oldugunda çıktı yerel kodlamayla çözülür ve Türkçe
            # karakterler bozuk metne dönüşür (ya da hata verir). Node UTF-8
            # yazar; biz de UTF-8 okuruz — platform ne olursa olsun aynı sonuç.
            encoding="utf-8", errors="replace",
        )
        if sonuc.returncode != 0:
            hatalar.append("%s: %s" % (yol, (sonuc.stderr or "").strip()[:300]))
    assert not hatalar, "Sözdizimi hatası:\n" + "\n".join(hatalar)


# ── 2. Sessiz ezme kapısı ─────────────────────────────────────────────


def test_ayni_isimli_fonksiyon_yok():
    """Aynı isimli iki fonksiyon = sessiz ezme = sürpriz hata.

    JavaScript'te ikinci `function ad()` tanımı birincisini siler; hata
    mesajı vermez, sayfa sadece beklenmedik yerde patlar. Bu, elle
    gözden kaçan en yaygın "vibe coding" hatasıdır.
    """
    hatalar = []
    desen = re.compile(r"^\s*function\s+([A-Za-z_$][\w$]*)\s*\(", re.M)
    for yol in _betik_klasoru():
        with open(os.path.join(KOK, yol), encoding="utf-8") as f:
            metin = f.read()
        sayac = {}
        for ad in desen.findall(metin):
            sayac[ad] = sayac.get(ad, 0) + 1
        tekrar = {k: v for k, v in sayac.items() if v > 1}
        if tekrar:
            hatalar.append("%s: %s" % (yol, tekrar))
    assert not hatalar, "Aynı isimli fonksiyon (sessiz ezme):\n" + "\n".join(
        hatalar)


# ── 3. Sayfa gerçekten çalışıyor mu ───────────────────────────────────


_HARNESS = r"""
// Mini tarayıcı: gerçek DOM değil ama durum.js'in kullandığı her yüzey var.
const kok = process.argv[2];

function el() {
  const o = {
    className: "", _metin: "", hidden: false, disabled: false,
    dataset: {}, children: [], value: "", innerHTML: "",
    appendChild(c) { this.children.push(c); return c; },
    addEventListener() {}, removeEventListener() {},
    setAttribute() {}, removeAttribute() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    getAttribute() { return null; },
    focus() {}, click() {},
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
  };
  // Gercek DOM davranisi: textContent okundugunda cocuklarin metni de gelir.
  Object.defineProperty(o, "textContent", {
    get() {
      return this._metin + this.children.map((c) => c.textContent || "").join("");
    },
    set(v) { this._metin = String(v == null ? "" : v); this.children = []; },
  });
  return o;
}
const ids = {};
globalThis.document = {
  getElementById(id) { if (!ids[id]) ids[id] = el(); return ids[id]; },
  createElement() { return el(); },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  addEventListener() {},
  body: el(),
};

// Sahte sunucu: her uç gerçek bir cevap döndürür.
const DURUM = {
  ok: true, arac_sayisi: 62, saglayicilar: ["ornek"], eksik_saglayicilar: [],
  commit: "abc1234", runtime: "vercel", tasima: "canli-ndjson",
  checkpoint_resume: false,
};
const CALISMA = {
  notlar: { hata: null, liste: [{ ad: "a.md", baslik: "Not", ozet: "ozet" }] },
  yayin: { hata: null, liste: [{ tarih: "2026-10-21", metin: "is" }] },
  tablolar: { hata: null, liste: [] },
  gorevler: { hata: null, acik: 0, kapali: 0, toplam: 0, liste: [] },
};
const KABUL = {
  uretildi: "2026-10-21", komut: "pytest", test_gecen: 1, test_atlandi: 0,
  arac_sayisi: 62, yetenek_alani: 1, sinirlar: ["sinir bir"],
};

function jsonYanit(veri) {
  return {
    ok: true, status: 200,
    headers: { get: () => "application/json" },
    json: async () => veri,
    text: async () => JSON.stringify(veri),
  };
}

globalThis.fetch = async (yol) => {
  const p = String(yol);
  if (p.indexOf("/api/durum") >= 0) return jsonYanit(DURUM);
  if (p.indexOf("/api/calisma") >= 0) return jsonYanit(CALISMA);
  if (p.indexOf("/durum-kabul.json") >= 0) return jsonYanit(KABUL);
  return jsonYanit({ ok: true });
};

globalThis.window = {
  performance: globalThis.performance,
  basakFetch: (yol, secenek = {}) => globalThis.fetch(yol, secenek),
  addEventListener() {},
  matchMedia() { return { matches: false, addEventListener() {} }; },
};
globalThis.location = { protocol: "http:", host: "127.0.0.1:1" };

// Sohbet ucu: akis (NDJSON) doner.
globalThis.window.basakFetch = async (yol, secenek = {}) => {
  const p = String(yol);
  if (p.indexOf("/api/sohbet") >= 0) {
    const govde = '{"tur":"bitir","cevap":"7","kaynak":"ornek"}\n';
    const kodla = new TextEncoder().encode(govde);
    let okundu = false;
    return {
      ok: true, status: 200,
      headers: { get: (h) => (h === "content-type" ? "application/x-ndjson" : "") },
      body: {
        getReader() {
          return {
            async read() {
              if (okundu) return { done: true };
              okundu = true;
              return { value: kodla, done: false };
            },
          };
        },
      },
      json: async () => ({ ok: true, cevap: "7" }),
    };
  }
  return globalThis.fetch(yol, secenek);
};

// Kanal acilir: soket.onopen kendi nesnesi icinde tetiklenir.
globalThis.WebSocket = class {
  constructor() {
    this.onopen = null; this.onerror = null;
    setTimeout(() => { if (this.onopen) this.onopen(); }, 5);
  }
  close() {}
};

const hata = [];
process.on("uncaughtException", (e) => {
  hata.push(String((e && e.stack) || e));
  bitir();
});
process.on("unhandledRejection", (e) => {
  hata.push(String((e && e.stack) || e));
  bitir();
});

function bitir() {
  const satirlar = (ids["kontroller"] && ids["kontroller"].children) || [];
  const ozet = satirlar.map((s) => ({
    baslik: (s.children[0] || {}).textContent || "",
    durum: String((s.children[1] || {}).className || ""),
    metin: (s.children[1] || {}).textContent || "",
  }));
  const calismaMetni = (ids["calisma"] || {}).textContent || "";
  const kabulMetni = (ids["calisma"] || {}).children
    ? (ids["calisma"].children || []).map((c) => c.textContent).join(" | ")
    : "";
  console.log(JSON.stringify({
    hata: hata, satirlar: ozet, calisma: calismaMetni,
    kabul: kabulMetni, sonOlcum: (ids["sonOlcum"] || {}).textContent || "",
  }));
  process.exit(hata.length ? 1 : 0);
}

try {
  const kaynak = require("fs").readFileSync(kok + "/web/durum.js", "utf8");
  new Function(kaynak)();
} catch (e) {
  hata.push(String((e && e.stack) || e));
  bitir();
  return;
}
setTimeout(bitir, 2500);
"""


def _sayfayi_calistir():
    """durum.js'i sahte tarayıcıda çalıştırır; (hata, ozet) döner."""
    betik = os.path.join(KOK, "_durum_harness.js")
    with open(betik, "w", encoding="utf-8") as f:
        f.write(_HARNESS)
    try:
        sonuc = subprocess.run(
            [NODE, betik, KOK],
            capture_output=True, text=True, timeout=60,
            # Windows CI'da varsayılan kodlama cp1252'dir; harness UTF-8 yazar
            # ve çıktıda Türkçe karakterler vardır. Yerel kodlamayla çözmek
            # metni bozar (test "Canlıya çıkan işler" aramasını bulamaz).
            # Kodlama AÇIK: her platformda aynı metin.
            encoding="utf-8", errors="replace",
        )
    finally:
        if os.path.exists(betik):
            os.remove(betik)
    assert sonuc.returncode in (0, 1), (
        "Harness beklenmedik şekilde bitti:\n" + (sonuc.stderr or "")[:800])
    satir = sonuc.stdout.strip().splitlines()
    assert satir, "Sayfa hiç çıktı üretmedi:\n" + (sonuc.stderr or "")[:800]
    import json
    return json.loads(satir[-1])


def test_durum_sayfasi_hata_vermeden_acilir():
    """Kritik kapı: sayfa açılırken istisna atmamalı.

    2026-10-21 hatası (sessiz ezilen `satirEkle`) tam burada yakalandı.
    """
    sonuc = _sayfayi_calistir()
    assert not sonuc["hata"], "Sayfa çöktü:\n" + "\n".join(sonuc["hata"])


def test_durum_sayfasi_olcum_satirlarini_cizer():
    """Her kontrol satırı çizilir ve ölçüm sonucu yazılır."""
    sonuc = _sayfayi_calistir()
    basliklar = [s["baslik"] for s in sonuc["satirlar"]]
    for beklenen in ("Beyin yanıt veriyor", "Kaç araç var",
                     "Hangi modeller bağlı", "Tarayıcı eklentisi kanalı",
                     "Canlı sürüm"):
        assert beklenen in basliklar, basliklar
    assert len(sonuc["satirlar"]) >= 7, basliklar
    # Ölçüm gerçekten sonuçlandı (sonsuza kadar "ölçülüyor" kalmadı).
    assert "Son ölçüm" in sonuc["sonOlcum"], sonuc["sonOlcum"]


def test_durum_sayfasi_beyin_olcumunu_gercek_yanitla_yapar():
    """Beyin satırı sahte "yeşil" yazmaz; gelen cevabı gösterir."""
    sonuc = _sayfayi_calistir()
    beyin = [s for s in sonuc["satirlar"] if s["baslik"] == "Beyin yanıt veriyor"]
    assert beyin, sonuc["satirlar"]
    satir = beyin[0]
    assert "pass" in satir["durum"], satir
    assert "7" in satir["metin"], satir
    assert "ornek" in satir["metin"], satir


def test_durum_sayfasi_calisma_ozetini_gosterir():
    """Saatlerdir süren çalışmanın özeti çekirdekten okunur."""
    sonuc = _sayfayi_calistir()
    metin = sonuc["calisma"]
    assert "Canlıya çıkan işler" in metin, metin[:400]
    assert "Çalışma notları" in metin, metin[:400]
    assert "Fikir tabloları" in metin, metin[:400]
    assert "Görevler" in metin, metin[:400]
    # Kayıtlı ölçüm bloğu da çizilir.
    assert "2026-10-21" in sonuc["kabul"], sonuc["kabul"][:400]
