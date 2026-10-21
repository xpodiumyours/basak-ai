/* eklenti/test/eylem.test.mjs — tıklama/yazma bekçisi (gerçek icerik.js).
 *
 * Gerçek Chrome yok; jsdom ile tek sayfa kurulur ve AYNI `icerik.js`
 * dosyasının gözlem + eylem sözleşmesi ölçülür:
 *   - gözlem her öğeye kalıcı `sira` verir (süzme sırayı kaydırmaz)
 *   - tıklama gerçekten tıklar, tıklama sonucu sayfayı anlatır
 *   - yazma değeri değiştirir ve input/change olaylarını tetikler
 *   - gizli / kapalı / şifre / dosya alanına eylem YOK
 *   - sayfa adresi değiştiyse eski kimlikle eylem reddedilir
 *   - kopmuş (DOM'dan çıkmış) öğeye eylem reddedilir
 *
 * Koşum:
 *   NODE_PATH=<jsdom kurulu node_modules> node eklenti/test/eylem.test.mjs
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

const SAYFA = `<!DOCTYPE html><html><head><title>Hesap</title></head><body>
  <h1>Hesap</h1>
  <label for="eposta">E-posta</label><input id="eposta" type="text">
  <textarea placeholder="Not"></textarea>
  <div id="not" contenteditable="true">eski</div>
  <input id="sifre" type="password" placeholder="Sifre" value="gizli-123">
  <input id="dosya" type="file">
  <button id="kaydet">Kaydet</button>
  <button id="pasif" disabled>Stokta yok</button>
  <div style="display:none"><button id="gizli">Gizli</button></div>
</body></html>`;

const dom = new JSDOM(SAYFA, { url: "https://ornek.test/hesap", runScripts: "outside-only" });
const pencere = dom.window;
pencere.eval(KAYNAK);

let tiklamaSayisi = 0;
pencere.document.getElementById("kaydet").addEventListener("click", () => {
  tiklamaSayisi += 1;
});

const olaylar = [];
pencere.document.addEventListener("input", (olay) => {
  olaylar.push("input:" + (olay.target.id || olay.target.tagName.toLowerCase()));
});
pencere.document.addEventListener("change", (olay) => {
  olaylar.push("change:" + (olay.target.id || olay.target.tagName.toLowerCase()));
});

function gozlem() {
  return pencere.__basakGozlem();
}

function sira(ad, rol) {
  const oge = gozlem().ogeler.find(
    (o) => o.ad === ad && (rol === undefined || o.rol === rol));
  assert.ok(oge, "öğe gözlemde yok: " + ad + (rol ? " (" + rol + ")" : ""));
  return oge.sira;
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

// ── Gözlem: kalıcı kimlik ────────────────────────────────────────────
test("her öğe kalıcı sira taşır ve kimlikler benzersizdir", () => {
  const ogeler = gozlem().ogeler;
  assert.ok(ogeler.length >= 5, String(ogeler.length));
  const kimlikler = ogeler.map((o) => o.sira);
  for (const k of kimlikler) assert.equal(typeof k, "number");
  assert.equal(new Set(kimlikler).size, kimlikler.length);
});

test("gizli öğe gözlemde yok (dolayısıyla kimliği de yok)", () => {
  assert.equal(gozlem().ogeler.some((o) => o.ad === "Gizli"), false);
});

test("kimlik yeniden gözlemde DEĞİŞMEZ", () => {
  const once = sira("Kaydet");
  const sonra = sira("Kaydet");
  assert.equal(once, sonra);
});

// ── Tıklama ──────────────────────────────────────────────────────────
test("tıklama gerçekten tıklar ve sonuç sayfayı anlatır", () => {
  const once = tiklamaSayisi;
  const cevap = pencere.__basakTikla(sira("Kaydet"));
  assert.equal(tiklamaSayisi, once + 1);
  assert.ok(cevap.sonuc, JSON.stringify(cevap));
  assert.equal(cevap.sonuc.yapildi, "tikla");
  assert.equal(cevap.sonuc.ad, "Kaydet");
  assert.equal(cevap.sonuc.url, "https://ornek.test/hesap");
});

test("kapalı (disabled) öğeye tıklanmaz", () => {
  const once = tiklamaSayisi;
  const cevap = pencere.__basakTikla(sira("Stokta yok"));
  assert.ok(cevap.hata, JSON.stringify(cevap));
  assert.equal(tiklamaSayisi, once);
});

test("bilinmeyen kimlik açık hata döner", () => {
  const cevap = pencere.__basakTikla(999999);
  assert.ok(cevap.hata, JSON.stringify(cevap));
  assert.match(cevap.hata, /bulunamadi/i);
});

test("gözlemden sonra DOM'dan çıkan öğeye tıklanmaz", () => {
  const dugme = pencere.document.getElementById("pasif");
  dugme.disabled = false;
  const kimlik = sira("Stokta yok");
  dugme.remove();
  const cevap = pencere.__basakTikla(kimlik);
  assert.ok(cevap.hata, JSON.stringify(cevap));
});

// ── Yazma ────────────────────────────────────────────────────────────
test("yazma değeri değiştirir ve input+change tetikler", () => {
  olaylar.length = 0;
  const cevap = pencere.__basakYaz(sira("E-posta", "textbox"), "casper@ornek.test");
  assert.ok(cevap.sonuc, JSON.stringify(cevap));
  assert.equal(pencere.document.getElementById("eposta").value, "casper@ornek.test");
  assert.deepEqual(olaylar, ["input:eposta", "change:eposta"]);
});

test("textarea'ya kırpmadan yazar", () => {
  const metin = "  iki bosluklu  ";
  const cevap = pencere.__basakYaz(sira("Not"), metin);
  assert.ok(cevap.sonuc, JSON.stringify(cevap));
  assert.equal(pencere.document.querySelector("textarea").value, metin);
});

test("contenteditable alana yazar", () => {
  const cevap = pencere.__basakYaz(sira("eski"), "yeni metin");
  assert.ok(cevap.sonuc, JSON.stringify(cevap));
  assert.equal(pencere.document.getElementById("not").textContent, "yeni metin");
});

test("şifre alanına YAZILMAZ ve değeri dışarı çıkmaz", () => {
  const sifre = pencere.document.getElementById("sifre");
  const once = sifre.value;
  const oge = gozlem().ogeler.find(
    (o) => o.rol === "textbox" && o.ad === "Sifre");
  assert.ok(oge, "şifre alanı gözlemde yok");
  assert.equal(oge.deger, "", "şifre değeri gözleme sızdı");
  const cevap = pencere.__basakYaz(oge.sira, "zorla-yaz");
  assert.ok(cevap.hata, JSON.stringify(cevap));
  assert.equal(sifre.value, once);
});

test("yazılamayan öğeye yazma reddedilir", () => {
  const cevap = pencere.__basakYaz(sira("Kaydet"), "olmaz");
  assert.ok(cevap.hata, JSON.stringify(cevap));
  assert.match(cevap.hata, /yazilabilir alan degil/i);
});

// ── Sayfa değişti ────────────────────────────────────────────────────
test("adres değişince eski kimlikle eylem reddedilir", () => {
  const kimlik = sira("Kaydet");
  pencere.history.pushState({}, "", "/hesap/onay");
  const cevap = pencere.__basakTikla(kimlik);
  assert.ok(cevap.hata, JSON.stringify(cevap));
  assert.match(cevap.hata, /adresi degisti/i);
});

console.log("\n" + gecen + " test geçti");
