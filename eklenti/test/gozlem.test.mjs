/* eklenti/test/gozlem.test.mjs — içerik betiği bekçisi.
 *
 * Gerçek Chrome yok; jsdom ile üç bambaşka sayfa şekli kurulur ve AYNI
 * `icerik.js` dosyasının ürettiği gözlem ölçülür:
 *   1. vitrin (başlık, metin, bağlantı, düğme, gizli düğme)
 *   2. form (etiket, placeholder, şifre, seçim, onay kutusu, boş alan)
 *   3. panel (tablo, rol=', tab', görsel, aria-disabled)
 *
 * Ölçülen sözleşme:
 *   - gizli öğe gönderilmez
 *   - ŞİFRE DEĞERİ asla dışarı çıkmaz
 *   - adsız ama etkileşimli alan korunur (sessiz kayıp yok)
 *   - rol eşlemesi ve kapalı durumu doğru
 *   - kodda site adı yok
 *
 * Koşum:
 *   NODE_PATH=<jsdom kurulu node_modules> node eklenti/test/gozlem.test.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";

const require = createRequire(import.meta.url);
let JSDOM;
try {
  ({ JSDOM } = require("jsdom"));
} catch (hata) {
  console.error("jsdom bulunamadı. NODE_PATH ile jsdom kurulu dizini ver.");
  process.exit(2);
}

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const KAYNAK = readFileSync(path.join(BURASI, "..", "icerik.js"), "utf8");

function gozlem(html, url, baslik) {
  const dom = new JSDOM(html, { url, runScripts: "outside-only" });
  if (baslik) dom.window.document.title = baslik;
  dom.window.eval(KAYNAK);
  return dom.window.__basakGozlem();
}

function adlar(sonuc) {
  return sonuc.ogeler.map((o) => o.ad);
}

let gecen = 0;
function test(ad, govde) {
  try {
    govde();
    gecen += 1;
    console.log("  ✓ " + ad);
  } catch (hata) {
    console.error("  ✗ " + ad + "\n    " + (hata && hata.message));
    process.exitCode = 1;
  }
}

// ── 1. Vitrin ────────────────────────────────────────────────────────
const VITRIN = `
  <h1>Kategori</h1>
  <p>24 ürün bulundu</p>
  <a href="/mavi-kalem">Mavi Kalem</a>
  <button>Sepete ekle</button>
  <button disabled>Stokta yok</button>
  <div style="display:none"><button>Gizli düğme</button></div>
  <div aria-hidden="true"><button>Ekran okuyucudan gizli</button></div>
`;

const v = gozlem(VITRIN, "https://ornek-vitrin.test/kategori", "Kategori");

test("vitrin: url ve başlık taşınır", () => {
  assert.equal(v.url, "https://ornek-vitrin.test/kategori");
  assert.equal(v.baslik, "Kategori");
});

test("vitrin: başlık/metin/bağlantı/düğme rolleri doğru", () => {
  const roller = v.ogeler.map((o) => o.rol);
  assert.ok(roller.includes("heading"), "heading yok");
  assert.ok(roller.includes("metin"), "metin yok");
  assert.ok(roller.includes("link"), "link yok");
  assert.equal(roller.filter((r) => r === "button").length, 2);
});

test("vitrin: gizli öğeler gönderilmez", () => {
  const hepsi = adlar(v).join(" | ");
  assert.ok(!hepsi.includes("Gizli düğme"), "display:none sızdı");
  assert.ok(!hepsi.includes("Ekran okuyucudan gizli"), "aria-hidden sızdı");
});

test("vitrin: kapalı düğme işaretlenir", () => {
  const kapali = [...v.ogeler.filter((o) => o.kapali).map((o) => o.ad)];
  assert.deepEqual(kapali, ["Stokta yok"]);
});

// ── 2. Form ──────────────────────────────────────────────────────────
const FORM = `
  <form>
    <label for="ad">Ad Soyad</label>
    <input id="ad" type="text" value="">
    <input type="email" placeholder="Eposta">
    <label for="sifre">Şifre</label>
    <input id="sifre" type="password" value="cok-gizli-123">
    <select><option selected>Ankara</option></select>
    <input type="checkbox" checked>
    <textarea></textarea>
    <input type="submit" value="Gönder">
  </form>
`;

const f = gozlem(FORM, "https://ornek-form.test/basvuru", "Başvuru");

test("form: etiket ve placeholder'dan ad okunur", () => {
  const hepsi = adlar(f).join(" | ");
  assert.ok(hepsi.includes("Ad Soyad"), "label[for] okunmadı");
  assert.ok(hepsi.includes("Eposta"), "placeholder okunmadı");
});

test("form: şifre alanı görünür ama DEĞERİ sızmaz", () => {
  const json = JSON.stringify(f);
  assert.ok(!json.includes("cok-gizli-123"), "şifre değeri sızdı!");
  const sifre = f.ogeler.find((o) => o.ad === "Şifre");
  assert.ok(sifre, "şifre alanı hiç yok");
  assert.equal(sifre.deger, "");
});

test("form: seçim, onay kutusu ve gönder düğmesi doğru", () => {
  const kutu = f.ogeler.find((o) => o.rol === "checkbox");
  assert.equal(kutu.deger, "true");
  const secim = f.ogeler.find((o) => o.rol === "combobox");
  assert.equal(secim.deger, "Ankara");
  const gonder = f.ogeler.find((o) => o.deger === "Gönder");
  assert.equal(gonder.rol, "button");
});

test("form: adsız ama etkileşimli alan korunur", () => {
  const bos = f.ogeler.filter((o) => o.rol === "textbox" && !o.ad);
  assert.ok(bos.length >= 1, "boş textarea sessizce düştü");
});

test("form: gizli input gönderilmez", () => {
  assert.ok(!f.ogeler.some((o) => o.rol === "gizli"));
});

// ── 3. Panel ─────────────────────────────────────────────────────────
const PANEL = `
  <h2>Günlük özet</h2>
  <table><tr><th>Ürün</th><td>Tadım Karışık</td></tr></table>
  <div role="tab">Ayarlar</div>
  <img alt="Logo" src="logo.png">
  <button aria-disabled="true">Kaydet</button>
`;

const p = gozlem(PANEL, "https://ornek-panel.test/panel", "Panel");

test("panel: tablo hücreleri metin olarak gelir", () => {
  const metinler = p.ogeler.filter((o) => o.rol === "metin").map((o) => o.ad);
  assert.ok(metinler.includes("Ürün"), "th yok");
  assert.ok(metinler.includes("Tadım Karışık"), "td yok");
});

test("panel: özel rol ve görsel korunur", () => {
  assert.ok(p.ogeler.some((o) => o.rol === "tab" && o.ad === "Ayarlar"));
  const gorsel = p.ogeler.find((o) => o.rol === "img");
  assert.equal(gorsel.ad, "Logo");
});

test("panel: aria-disabled kapalı sayılır", () => {
  const kaydet = p.ogeler.find((o) => o.ad === "Kaydet");
  assert.equal(kaydet.kapali, true);
});

// ── Genel ────────────────────────────────────────────────────────────
test("aynı kod üç farklı sayfada da çalışır", () => {
  for (const sonuc of [v, f, p]) {
    assert.ok(sonuc.ogeler.length >= 4, "öğe sayısı beklenenden az");
  }
});

test("kodda site adı gömülü değil", () => {
  assert.ok(!/https?:\/\//.test(KAYNAK), "kaynakta adres var");
  assert.ok(!/\b[a-z0-9-]+\.(com|net|org|io|dev|test)\b/.test(KAYNAK),
    "kaynakta alan adı var");
});

console.log("\n" + gecen + " test geçti" + (process.exitCode ? " (kırmızı var)" : ""));
