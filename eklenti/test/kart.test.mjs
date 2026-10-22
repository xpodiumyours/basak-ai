/* eklenti/test/kart.test.mjs — sohbet ekranındaki eklenti kartı.
 *
 * Test edilen dosya `web/eklenti-kart.js` (sitenin kendi betiği), eklenti
 * değil. Kural aynı: kart yalnız arayüzdür; model çağırmaz, sunucuya
 * istek atmaz, kullanıcı metnini yorumlamaz.
 *
 * Ölçülen sözleşme:
 *   - eklenti yokken: "kurulu görünmüyor" + dört adım görünür
 *   - eklenti varken: "kurulu görünüyor", adımlar gizli, nokta yeşil
 *   - durum okunamazsa (zaman aşımı): nötr metin, adımlar görünür
 *   - "kapat" kararı KİŞİYE göre saklanır (Başak ID anahtarı)
 *   - kimlik hazır olunca kart o kimliği yazar
 *   - telefon/tablette kart HİÇ görünmez (eklenti oraya kurulamaz;
 *     uygulanamaz kurulum adımı göstermek yalan olur)
 *
 * Koşum: NODE_PATH=<jsdom> node eklenti/test/kart.test.mjs
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
const KAYNAK = readFileSync(path.join(BURASI, "..", "..", "web", "eklenti-kart.js"), "utf8");

const HTML = `<!doctype html><html lang="tr"><body>
  <section id="eklentiKarti" hidden>
    <div class="eklenti-ust">
      <span id="eklentiNokta" class="eklenti-nokta"></span>
      <strong>Başak'ı tarayıcında yanına al</strong>
      <button id="eklentiKapat" type="button">×</button>
    </div>
    <p id="eklentiDurum"></p>
    <ol id="eklentiAdimlar"><li>indir</li></ol>
    <p class="eklenti-alt"><span id="eklentiKimlik"></span></p>
  </section>
</body></html>`;

/**
 * Eklenti kurulu (onload), yok (onerror) ya da sessiz (zaman aşımı).
 * secenek.ua → tarayıcı kimliği (jsdom 30 constructor seçeneğini yok
 * saydığı için navigator üzerine yazılır); secenek.mobil →
 * userAgentData.mobile=true.
 */
function kur(sonuc, secenek = {}) {
  const dom = new JSDOM(HTML, {
    url: "https://basak-vercel.vercel.app/",
    runScripts: "outside-only"
  });
  if (secenek.ua) {
    Object.defineProperty(dom.window.navigator, "userAgent", {
      value: secenek.ua
    });
  }
  if (secenek.mobil) {
    Object.defineProperty(dom.window.navigator, "userAgentData", {
      value: { mobile: true }
    });
  }
  dom.window.Image = class {
    set src(_deger) {
      if (sonuc === "kurulu") setTimeout(() => this.onload && this.onload(), 0);
      else if (sonuc === "yok") setTimeout(() => this.onerror && this.onerror(), 0);
    }
  };
  if (sonuc === "kurulu") {
    dom.window.basakKimlik = { kullanici: "u123", basak_id: "1234 5678" };
  } else if (sonuc !== "kimliksiz") {
    dom.window.basakKimlik = { kullanici: "u123", basak_id: "1234 5678" };
  }
  dom.window.eval(KAYNAK);
  return dom;
}

const bekle = (ms = 20) => new Promise((coz) => setTimeout(coz, ms));

let gecen = 0;
async function test(ad, govde) {
  try {
    await govde();
    gecen += 1;
    console.log("  ✓ " + ad);
  } catch (hata) {
    console.error("  ✗ " + ad + "\n    " + (hata && hata.message));
    process.exitCode = 1;
  }
}

await test("eklenti yokken adımlar görünür", async () => {
  const dom = kur("yok");
  await bekle();
  const kart = dom.window.document.getElementById("eklentiKarti");
  assert.equal(kart.hidden, false);
  const durum = dom.window.document.getElementById("eklentiDurum").textContent;
  assert.match(durum, /kurulu görünmüyor/i);
  assert.equal(dom.window.document.getElementById("eklentiAdimlar").hidden, false);
});

await test("eklenti kuruluyken adımlar gizlenir, nokta yeşil", async () => {
  const dom = kur("kurulu");
  await bekle();
  const doc = dom.window.document;
  assert.match(doc.getElementById("eklentiDurum").textContent, /kurulu görünüyor/i);
  assert.equal(doc.getElementById("eklentiAdimlar").hidden, true);
  assert.match(doc.getElementById("eklentiNokta").className, /kurulu/);
});

await test("durum okunamazsa nötr metin (uydurmaz)", async () => {
  const dom = kur("bilinmiyor");
  await bekle(100);
  const doc = dom.window.document;
  // Zaman aşımını beklemeden önce de nötr metin yazılmış olmalı.
  assert.match(doc.getElementById("eklentiDurum").textContent, /bildirmedi/i);
  assert.equal(doc.getElementById("eklentiAdimlar").hidden, false);
});

await test("kapat kararı kişiye özel saklanır", async () => {
  const dom = kur("yok");
  await bekle();
  const pencere = dom.window;
  pencere.document.getElementById("eklentiKapat").click();
  assert.equal(pencere.document.getElementById("eklentiKarti").hidden, true);
  assert.equal(pencere.localStorage.getItem("basak_eklenti_kart_v1:u123"), "kapali");

  // Aynı kullanıcı için sonraki ziyarette kart kapalı kalır.
  const ikinci = kur("yok");
  ikinci.window.localStorage.setItem("basak_eklenti_kart_v1:u123", "kapali");
  ikinci.window.eval(KAYNAK);
  await bekle();
  assert.equal(ikinci.window.document.getElementById("eklentiKarti").hidden, true);
});

await test("kimlik satırı Başak ID'sini yazar", async () => {
  const dom = kur("yok");
  await bekle();
  const metin = dom.window.document.getElementById("eklentiKimlik").textContent;
  assert.match(metin, /Başak ID 1234 5678/);
});

await test("kimlik sonradan gelirse kart güncellenir", async () => {
  const dom = kur("kimliksiz");
  await bekle();
  assert.match(dom.window.document.getElementById("eklentiKimlik").textContent,
               /bu tarayıcıya özel/i);
  dom.window.basakKimlik = { kullanici: "u999", basak_id: "9999 0000" };
  dom.window.dispatchEvent(new dom.window.CustomEvent("basak:kimlik"));
  await bekle();
  assert.match(dom.window.document.getElementById("eklentiKimlik").textContent,
               /9999 0000/);
});

await test("telefonda kart hiç görünmez — imkânsız kurulum tarif edilmez", async () => {
  const dom = kur("yok", {
    ua: "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
      + "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
  });
  await bekle();
  const doc = dom.window.document;
  assert.equal(doc.getElementById("eklentiKarti").hidden, true);
  assert.equal(doc.getElementById("eklentiDurum").textContent, "");
  assert.equal(doc.getElementById("eklentiAdimlar").hidden, false, "adım yazılmadıysa görünür kalır");
});

await test("userAgentData mobil diyorsa kart gizli kalır", async () => {
  const dom = kur("yok", { mobil: true });
  await bekle();
  assert.equal(dom.window.document.getElementById("eklentiKarti").hidden, true);
});

await test("masaüstünde kart yine görünür (mobil kuralı masaüstüne sızmaz)", async () => {
  const dom = kur("yok", {
    ua: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      + "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
  });
  await bekle();
  const kart = dom.window.document.getElementById("eklentiKarti");
  assert.equal(kart.hidden, false);
  assert.match(dom.window.document.getElementById("eklentiDurum").textContent,
               /kurulu görünmüyor/i);
});

await test("kart sunucuya istek atmaz, model çağırmaz", () => {
  assert.equal(/\bfetch\s*\(/.test(KAYNAK), false, "kart fetch kullanıyor");
  assert.equal(/XMLHttpRequest|WebSocket|EventSource/.test(KAYNAK), false);
  assert.equal(/openai|groq|gemini|openrouter/i.test(KAYNAK), false);
});

console.log("\n" + gecen + " test geçti");
