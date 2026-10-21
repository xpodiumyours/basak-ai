/* eklenti/test/sahte_eklenti.mjs — tarayıcısız uçtan uca prova.
 *
 * Gerçek `icerik.js` bir jsdom sayfasında koşar; gerçek WebSocket
 * istemcisi Başak köprüsüne bağlanır. Böylece "eklenti -> köprü ->
 * çekirdek" zinciri Chrome olmadan ölçülür.
 *
 * Kullanım:  node sahte_eklenti.mjs <port> [sayfa-tipi]
 * Çıkış: köprüye bağlanır, istek geldikçe gözlem gönderir, SIGTERM'de kapanır.
 */

import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const WebSocket = require("ws");

let JSDOM;
try {
  ({ JSDOM } = require("jsdom"));
} catch (hata) {
  console.error("jsdom gerekli");
  process.exit(2);
}

const BURASI = path.dirname(fileURLToPath(import.meta.url));
const KAYNAK = readFileSync(path.join(BURASI, "..", "icerik.js"), "utf8");

const SAYFALAR = {
  form: `<!DOCTYPE html><html><head><title>Başvuru</title></head><body>
    <h1>Başvuru formu</h1>
    <label for="ad">Ad Soyad</label><input id="ad" type="text">
    <input type="email" placeholder="E-posta">
    <label for="s">Şifre</label><input id="s" type="password" value="cok-gizli-123">
    <select><option selected>Ankara</option></select>
    <input type="checkbox" checked>
    <button>Gönder</button>
  </body></html>`,
  vitrin: `<!DOCTYPE html><html><head><title>Kategori</title></head><body>
    <h1>Kategori</h1><p>24 ürün</p>
    <a href="/a">Mavi Kalem</a><button>Sepete ekle</button>
    <button disabled>Stokta yok</button>
    <div style="display:none"><button>Gizli</button></div>
  </body></html>`
};

const port = process.argv[2] || "8788";
const tip = process.argv[3] || "form";
const html = SAYFALAR[tip] || SAYFALAR.form;

const dom = new JSDOM(html, {
  url: "https://ornek-" + tip + ".test/sayfa",
  runScripts: "outside-only"
});
dom.window.eval(KAYNAK);

const ws = new WebSocket("ws://127.0.0.1:" + port + "/");

ws.on("open", () => {
  console.log("sahte eklenti baglandi: " + tip);
});

ws.on("message", (veri) => {
  let mesaj;
  try { mesaj = JSON.parse(String(veri)); } catch (hata) { return; }
  if (mesaj.islem !== "sayfa_gozlem") {
    ws.send(JSON.stringify({ id: mesaj.id, ok: false, hata: "bilinmeyen islem" }));
    return;
  }
  const gozlem = dom.window.__basakGozlem();
  console.log("gozlem gonderildi: " + gozlem.ogeler.length + " oge");
  ws.send(JSON.stringify({ id: mesaj.id, ok: true, sonuc: gozlem }));
});

ws.on("close", () => process.exit(0));
ws.on("error", (hata) => {
  console.error("baglanti hatasi: " + hata.message);
  process.exit(1);
});
