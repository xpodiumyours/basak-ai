/* eklenti/test/kutu.test.mjs — paylaşımlı kutu yoklaması (gerçek arka.js).
 *
 * Gerçek Chrome yok; jsdom penceresine sahte `chrome` + sahte `WebSocket`
 * konur, AYNI `arka.js` dosyası değerlendirilir:
 *   - bağlantı açılınca kutu yoklaması başlar
 *   - kutu işi mevcut islemYap yolundan koşar (onay kapısı delinmez)
 *   - sonuç kutuya geri yazılır (kutu_yaz)
 *   - bağlantı kapanınca yoklama durur
 *
 * Koşum:
 *   NODE_PATH=<jsdom kurulu node_modules> node eklenti/test/kutu.test.mjs
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
const KAYNAK = readFileSync(path.join(BURASI, "..", "arka.js"), "utf8");

const GOZLEM = {
  url: "https://ornek.test/hesap",
  baslik: "Hesap",
  ogeler: [{ sira: 1, rol: "dugme", ad: "Ekle", deger: "" }]
};

const ornekler = [];
class SahteWS {
  static OPEN = 1;
  constructor(adres) {
    this.url = adres;
    this.readyState = 0;
    this.gonderilen = [];
    ornekler.push(this);
    this.onopen = null;
    this.onclose = null;
    this.onmessage = null;
  }
  send(metin) { this.gonderilen.push(JSON.parse(metin)); }
  close() { this.readyState = 3; }
}

const gonderilenOnay = [];
const sahteChrome = {
  storage: {
    local: { get: async () => ({}), set: async () => {} },
    session: { get: async () => null, set: async () => {} }
  },
  action: { setBadgeText: () => {}, setBadgeBackgroundColor: () => {} },
  tabs: { query: async () => [{ id: 7 }] },
  scripting: {
    executeScript: async () => [{ result: GOZLEM, frameId: 0 }]
  },
  runtime: {
    onInstalled: { addListener: () => {} },
    onStartup: { addListener: () => {} },
    onMessage: { addListener: () => {} },
    sendMessage: async (mesaj) => {
      if (mesaj && mesaj.tip === "onay") {
        gonderilenOnay.push(mesaj);
        return { soruldu: true };
      }
      return {};
    }
  },
  sidePanel: { setPanelBehavior: () => Promise.resolve() }
};

const dom = new JSDOM(`<!DOCTYPE html><html><head></head><body></body></html>`,
  { url: "https://ornek.test/", runScripts: "outside-only" });
const pencere = dom.window;
pencere.WebSocket = SahteWS;
pencere.chrome = sahteChrome;
pencere.eval(KAYNAK);
// baglan() yüklenirken önce ayarları okur (async); bir tur beklenir.
await new Promise((coz) => setTimeout(coz, 30));

function test(ad, govde) {
  return Promise.resolve()
    .then(govde)
    .then(() => console.log("  ✓ " + ad))
    .catch((hata) => {
      console.error("  ✗ " + ad + ": " + (hata && hata.message || hata));
      process.exitCode = 1;
    });
}

const ws = ornekler[0];
assert.ok(ws, "arka.js yüklenince bağlanmaya çalışır");
ws.readyState = 1;
ws.onopen();

await test("kutu yoklaması kutu_al gönderir", async () => {
  const p = pencere.eval("kutuYokla()");
  const istek = ws.gonderilen.find((m) => m.islem === "kutu_al");
  assert.ok(istek, "kutu_al gönderilmedi: " + JSON.stringify(ws.gonderilen));
  ws.onmessage({ data: JSON.stringify({ id: istek.id, ok: true, sonuc: { bos: true } }) });
  await p;
});

await test("kutu işi islemYap yolundan koşar, sonuç kutuya yazılır", async () => {
  ws.gonderilen.length = 0;
  const p = pencere.eval("kutuYokla()");
  const istek = ws.gonderilen.find((m) => m.islem === "kutu_al");
  assert.ok(istek);
  const is = { id: 41, islem: "sayfa_gozlem", veri: {} };
  ws.onmessage({ data: JSON.stringify({ id: istek.id, ok: true, sonuc: is }) });
  await p;
  // Onay gerektirmeyen gözlemde panele soru gitmez.
  assert.equal(gonderilenOnay.length, 0);
  const yaz = ws.gonderilen.find((m) => m.islem === "kutu_yaz");
  assert.ok(yaz, "kutu_yaz gönderilmedi");
  assert.equal(yaz.veri.job, 41);
  assert.equal(yaz.veri.cevap.ok, true);
  assert.equal(yaz.veri.cevap.sonuc.url, GOZLEM.url);
});

await test("kosu_devam işi sayfaya dokunmadan kosu_id ile sürdürür", async () => {
  ws.gonderilen.length = 0;
  const p = pencere.eval("kutuYokla()");
  const istek = ws.gonderilen.find((m) => m.islem === "kutu_al");
  assert.ok(istek);
  const is = { id: 42, islem: "kosu_devam", veri: { kosu_id: "abc123" } };
  ws.onmessage({ data: JSON.stringify({ id: istek.id, ok: true, sonuc: is }) });
  // kutu_al cevabı bir microtask sonra işlenir; sohbet ondan sonra gider.
  await new Promise((coz) => setTimeout(coz, 0));
  const sohbet = ws.gonderilen.find((m) => m.islem === "sohbet");
  assert.ok(sohbet, "sohbet isteği gönderilmedi: " + JSON.stringify(ws.gonderilen));
  assert.equal(sohbet.veri.kosu_id, "abc123");
  assert.equal(sohbet.veri.metin, "Kaldığın yerden devam et.");
  // Onay kapısı sorulmaz: sayfa eylemi yok.
  assert.equal(gonderilenOnay.length, 0);
  ws.onmessage({ data: JSON.stringify({ id: sohbet.id, ok: true, sonuc: { cevap: "sürdü" } }) });
  await p;
  const yaz = ws.gonderilen.find((m) => m.islem === "kutu_yaz");
  assert.ok(yaz, "kutu_yaz gönderilmedi");
  assert.equal(yaz.veri.job, 42);
  assert.equal(yaz.veri.cevap.ok, true);
});

await test("bağlantı kapanınca yoklama durur", async () => {
  ws.onclose();
  ws.gonderilen.length = 0;
  await pencere.eval("kutuYokla()");
  assert.equal(ws.gonderilen.length, 0, "kapalı bağlantıda istek atıldı");
});

pencere.eval("kutuDurdur(); durdurPing();");
console.log("\nkutu yoklaması geçti");
