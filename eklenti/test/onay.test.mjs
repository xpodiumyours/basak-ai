/* eklenti/test/onay.test.mjs — onay kapısı bekçisi (gerçek arka.js).
 *
 * Chrome yok; `arka.js` bir vm bağlamında, sahte `chrome` API'siyle koşar.
 * Ölçülen sözleşme:
 *   - tıklama/yazma ONAYSIZ uygulanmaz
 *   - onay kartı hedefin adını gösterir (ne okuyacağını bilmek için)
 *   - "Vazgeç" eylemi durdurur, içerik betiğine hiç istek gitmez
 *   - panel kapalıysa (mesaj ulaşmazsa) eylem YAPILMAZ — fail-closed
 *   - "5 dakika sorma" yalnız o sekme için muafiyet verir
 *
 * Koşum: node eklenti/test/onay.test.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const KAYNAK = readFileSync(new URL("../arka.js", import.meta.url), "utf8");

function kur(ayar = {}) {
  const kayit = {
    gonderilen: [],        // içerik betiğine giden mesajlar
    onayIstekleri: [],     // panele giden onay kartları
    dinleyiciler: [],
    panelVar: ayar.panelVar !== false,
    muafiyetDeposu: {}
  };

  const sandbox = {
    console,
    setTimeout,
    clearTimeout,
    Date,
    Promise,
    JSON,
    Map,
    Math,
    String,
    Number,
    Array,
    Object,
    Error,
    chrome: {
      storage: {
        local: { get: async () => ({}), set: async () => {} },
        session: {
          get: async (anahtar) => ({ [anahtar]: kayit.muafiyetDeposu[anahtar] }),
          set: async (veri) => Object.assign(kayit.muafiyetDeposu, veri)
        }
      },
      action: {
        setBadgeText: async () => {},
        setBadgeBackgroundColor: async () => {}
      },
      tabs: {
        query: async () => [{ id: 5 }],
        sendMessage: async (_id, istek) => {
          kayit.gonderilen.push(istek);
          if (istek.tip === "gozlem") {
            return {
              url: "https://ornek.test/hesap",
              baslik: "Hesap",
              ogeler: [
                { sira: 11, rol: "textbox", ad: "E-posta", deger: "" },
                { sira: 12, rol: "button", ad: "Kaydet", deger: "" }
              ]
            };
          }
          if (istek.tip === "tikla") {
            return { sonuc: { yapildi: "tikla", sira: istek.sira } };
          }
          if (istek.tip === "yaz") {
            return { sonuc: { yapildi: "yaz", sira: istek.sira } };
          }
          return undefined;
        }
      },
      scripting: { executeScript: async () => {} },
      runtime: {
        onInstalled: { addListener: () => {} },
        onStartup: { addListener: () => {} },
        onMessage: { addListener: (fn) => kayit.dinleyiciler.push(fn) },
        sendMessage: async (mesaj) => {
          if (!mesaj || mesaj.tip !== "onay") return undefined;
          if (!kayit.panelVar) {
            throw new Error("Could not establish connection. Receiving end does not exist.");
          }
          kayit.onayIstekleri.push(mesaj);
          return undefined;
        }
      }
    },
    WebSocket: class {
      constructor() { this.readyState = 0; }
      send() {}
      close() {}
    }
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(KAYNAK, sandbox);
  return { sandbox, kayit };
}

async function bekle(kosul, sinir = 2000) {
  const baslangic = Date.now();
  while (Date.now() - baslangic < sinir) {
    if (kosul()) return;
    await new Promise((coz) => setTimeout(coz, 5));
  }
  throw new Error("beklenen durum oluşmadı");
}

function cevapla(kayit, istekId, onay, muaf = false) {
  for (const fn of kayit.dinleyiciler) {
    fn({ tip: "onay-cevap", istekId, onay, muaf }, {}, () => {});
  }
}

function tiklaSayisi(kayit) {
  return kayit.gonderilen.filter((x) => x.tip === "tikla").length;
}

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

await test("onay gelmeden eylem uygulanmaz", async () => {
  const { sandbox, kayit } = kur();
  const soz = sandbox.islemYap({ id: "c1", islem: "sayfa_tikla", veri: { sira: 12 } });

  await bekle(() => kayit.onayIstekleri.length === 1);
  assert.equal(tiklaSayisi(kayit), 0, "onay sorulmadan tıklandı");

  const istek = kayit.onayIstekleri[0];
  assert.equal(istek.ad, "Kaydet", "onay kartı hedefi göstermiyor");
  assert.equal(istek.rol, "button");
  assert.equal(istek.url, "https://ornek.test/hesap");

  cevapla(kayit, istek.istekId, true);
  const cevap = await soz;

  assert.equal(cevap.ok, true, JSON.stringify(cevap));
  assert.equal(tiklaSayisi(kayit), 1);
});

await test("Vazgeç eylemi tamamen durdurur", async () => {
  const { sandbox, kayit } = kur();
  const soz = sandbox.islemYap({ id: "c2", islem: "sayfa_tikla", veri: { sira: 12 } });

  await bekle(() => kayit.onayIstekleri.length === 1);
  cevapla(kayit, kayit.onayIstekleri[0].istekId, false);
  const cevap = await soz;

  assert.equal(cevap.ok, false, JSON.stringify(cevap));
  assert.match(cevap.hata, /onay/i);
  assert.equal(tiklaSayisi(kayit), 0);
});

await test("panel kapalıysa eylem yapılmaz (fail-closed)", async () => {
  const { sandbox, kayit } = kur({ panelVar: false });
  const cevap = await sandbox.islemYap({
    id: "c3", islem: "sayfa_yaz", veri: { sira: 11, metin: "casper@ornek.test" }
  });

  assert.equal(cevap.ok, false, JSON.stringify(cevap));
  assert.match(cevap.hata, /panel/i);
  assert.equal(kayit.gonderilen.filter((x) => x.tip === "yaz").length, 0);
});

await test("yazma onay kartı metni gösterir", async () => {
  const { sandbox, kayit } = kur();
  const soz = sandbox.islemYap({
    id: "c4", islem: "sayfa_yaz", veri: { sira: 11, metin: "casper@ornek.test" }
  });

  await bekle(() => kayit.onayIstekleri.length === 1);
  const istek = kayit.onayIstekleri[0];
  assert.equal(istek.ad, "E-posta");
  assert.equal(istek.metin, "casper@ornek.test");

  cevapla(kayit, istek.istekId, true);
  const cevap = await soz;
  assert.equal(cevap.ok, true, JSON.stringify(cevap));
});

await test("'5 dakika sorma' ikinci eylemde sormaz", async () => {
  const { sandbox, kayit } = kur();
  const soz = sandbox.islemYap({ id: "c5", islem: "sayfa_tikla", veri: { sira: 12 } });

  await bekle(() => kayit.onayIstekleri.length === 1);
  cevapla(kayit, kayit.onayIstekleri[0].istekId, true, true);
  const ilk = await soz;
  assert.equal(ilk.ok, true, JSON.stringify(ilk));
  await bekle(() => kayit.muafiyetDeposu.onayMuafiyet);

  const ikinci = await sandbox.islemYap({
    id: "c6", islem: "sayfa_yaz", veri: { sira: 11, metin: "x" }
  });

  assert.equal(ikinci.ok, true, JSON.stringify(ikinci));
  assert.equal(kayit.onayIstekleri.length, 1, "muafiyete rağmen yeniden sordu");
});

await test("gözlem (okuma) onay istemez", async () => {
  const { sandbox, kayit } = kur();
  const cevap = await sandbox.islemYap({ id: "c7", islem: "sayfa_gozlem" });

  assert.equal(cevap.ok, true, JSON.stringify(cevap));
  assert.equal(kayit.onayIstekleri.length, 0, "okuma için onay soruldu");
});

console.log("\n" + gecen + " test geçti");
