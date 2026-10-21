/* eklenti/arka.js — servis çalışanı: Başak'a bağlanır, sayfayı iletir.
 *
 * Tek işi var: çekirdekten gelen "sayfa_gozlem" isteğini açık sekmeye
 * sorup cevabı geri yazmak. Karar vermez, sayfa yorumlamaz, model çağırmaz
 * (AGENTS.md §9: beyin çekirdekte, eklenti yalnız göz ve el).
 */

// BULUT kanali (2026-10-21): eklenti artik canli Basak'a baglanir.
// Yerel gelistirme icin panelden adresi ws://127.0.0.1:8788 yapilabilir.
const VARSAYILAN_SUNUCU = "wss://basak-vercel.vercel.app/api/eklenti";
const EN_COK_BEKLEME = 30000;
// Servis calisani bosta ~30 sn sonra olur; acik WebSocket'i canli tutmak
// icin duzenli ping gonderilir. Sunucu islemsiz mesaji yanitsiz yutar.
const PING_ARALIK = 20000;

let baglanti = null;
let pingZamani = null;
let deneme = 0;
let yenidenZaman = null;   // zamanlanmış yeniden bağlanma (tek tane)
let durum = "kapali";      // kapali | baglaniyor | bagli | hata
let sonHata = "";
let sayac = 0;
let cagriSayaci = 0;
const bekleyenSohbet = new Map();   // panel mesaji -> cozucu

async function ayarlariAl() {
  const veri = await chrome.storage.local.get(["sunucu", "anahtar"]);
  return {
    sunucu: String(veri.sunucu || VARSAYILAN_SUNUCU).trim(),
    anahtar: String(veri.anahtar || "").trim()
  };
}

function durumuYaz(yeni, hata) {
  durum = yeni;
  sonHata = hata || "";
  chrome.action.setBadgeText({ text: yeni === "bagli" ? "●" : "" });
  chrome.action.setBadgeBackgroundColor({ color: "#00e5ff" });
}

async function sekmeyeSor(istek) {
  const sekmeler = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  const sekme = sekmeler && sekmeler[0];
  if (!sekme || !sekme.id) throw new Error("açık sekme bulunamadı");
  try {
    return await chrome.tabs.sendMessage(sekme.id, istek);
  } catch (hata) {
    // Eklenti kurulmadan önce açılmış sekmede içerik betiği yoktur.
    try {
      await chrome.scripting.executeScript({ target: { tabId: sekme.id }, files: ["icerik.js"] });
      return await chrome.tabs.sendMessage(sekme.id, istek);
    } catch (hata2) {
      throw new Error("bu sekme okunamıyor (chrome:// veya mağaza sayfası olabilir)");
    }
  }
}

async function gozlemAl() {
  return sekmeyeSor({ tip: "gozlem" });
}

function sohbetGonder(metin, gecmis) {
  return new Promise((coz) => {
    const yazi = metin.trim();
    if (!yazi) { coz({ ok: false, hata: "mesaj boş" }); return; }
    if (!baglanti || baglanti.readyState !== WebSocket.OPEN) {
      coz({ ok: false, hata: "Bağlantı yok — önce Bağlan'a bas." });
      return;
    }
    cagriSayaci += 1;
    const id = "p" + cagriSayaci;
    const zaman = setTimeout(() => {
      bekleyenSohbet.delete(id);
      coz({ ok: false, hata: "Başak 90 saniye içinde yanıt vermedi." });
    }, 90000);
    bekleyenSohbet.set(id, { coz, zaman });
    baglanti.send(JSON.stringify({
      id, islem: "sohbet",
      veri: { metin: yazi, gecmis: Array.isArray(gecmis) ? gecmis : [] }
    }));
  });
}

async function islemYap(mesaj) {
  const veri = mesaj.veri || {};
  try {
    if (mesaj.islem === "sayfa_gozlem") {
      const gozlem = await gozlemAl();
      if (!gozlem) throw new Error("sayfa cevap vermedi (sekme yenilenmeli)");
      if (gozlem.hata) return { id: mesaj.id, ok: false, hata: gozlem.hata };
      return { id: mesaj.id, ok: true, sonuc: gozlem };
    }
    if (mesaj.islem === "sayfa_tikla") {
      const cevap = await sekmeyeSor({ tip: "tikla", sira: veri.sira });
      if (!cevap) throw new Error("sayfa cevap vermedi (sekme yenilenmeli)");
      if (cevap.hata) return { id: mesaj.id, ok: false, hata: cevap.hata };
      return { id: mesaj.id, ok: true, sonuc: cevap.sonuc };
    }
    if (mesaj.islem === "sayfa_yaz") {
      const cevap = await sekmeyeSor({ tip: "yaz", sira: veri.sira, metin: veri.metin });
      if (!cevap) throw new Error("sayfa cevap vermedi (sekme yenilenmeli)");
      if (cevap.hata) return { id: mesaj.id, ok: false, hata: cevap.hata };
      return { id: mesaj.id, ok: true, sonuc: cevap.sonuc };
    }
  } catch (hata) {
    return { id: mesaj.id, ok: false, hata: String(hata.message || hata) };
  }
  return { id: mesaj.id, ok: false, hata: "bilinmeyen işlem: " + mesaj.islem };
}

function durdurPing() {
  if (pingZamani !== null) {
    clearInterval(pingZamani);
    pingZamani = null;
  }
}

/* Yeniden bağlanma: Vercel bağlantıyı fonksiyon süresinde (Hobby 300 sn)
 * kapatır, ağ da kopabilir. Deneme SINIRSIZDIR; bekleme 1→2→4→8→16→30 sn.
 * `deneme` yalnız başarılı bağlantıda sıfırlanır. */
function yenidenDene() {
  if (yenidenZaman !== null) return;
  const bekle = Math.min(EN_COK_BEKLEME, 1000 * Math.pow(2, Math.min(deneme, 5)));
  deneme += 1;
  yenidenZaman = setTimeout(() => { yenidenZaman = null; baglan(); }, bekle);
}

/* Bağlantı kopunca bekleyen panel mesajı sessizce askıda kalmasın:
 * 90 sn bekletmek yerine açık hata döneriz (mesaj sunucuya ulaşmış da
 * olabilir, ulaşmamış da — kullanıcı tekrar gönderir). */
function bekleyenleriBosaltt(sebep) {
  for (const [id, kayit] of bekleyenSohbet) {
    clearTimeout(kayit.zaman);
    kayit.coz({ ok: false, hata: sebep });
    bekleyenSohbet.delete(id);
  }
}

async function baglan() {
  if (baglanti && (baglanti.readyState === WebSocket.OPEN ||
                   baglanti.readyState === WebSocket.CONNECTING)) return;
  const { sunucu, anahtar } = await ayarlariAl();
  const adres = anahtar
    ? sunucu + (sunucu.includes("?") ? "&" : "?") + "token=" + encodeURIComponent(anahtar)
    : sunucu;
  durumuYaz("baglaniyor");
  let ws;
  try {
    ws = new WebSocket(adres);
  } catch (hata) {
    durumuYaz("hata", "adres geçersiz: " + sunucu);
    return;
  }
  baglanti = ws;

  ws.onopen = () => {
    deneme = 0;
    if (yenidenZaman !== null) { clearTimeout(yenidenZaman); yenidenZaman = null; }
    durumuYaz("bagli");
    durdurPing();
    pingZamani = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        try { ws.send(JSON.stringify({ ping: Date.now() })); } catch (hata) {}
      }
    }, PING_ARALIK);
  };
  ws.onclose = () => {
    durdurPing();
    if (durum !== "hata") durumuYaz("kapali", "bağlantı kapandı, yeniden bağlanılıyor…");
    baglanti = null;
    bekleyenleriBosaltt("Bağlantı yenilendi; mesaj yanıtsız kaldı — tekrar gönder.");
    yenidenDene();
  };
  ws.onerror = () => {
    durumuYaz("hata", "Başak'a ulaşılamadı: " + sunucu);
  };
  ws.onmessage = async (olay) => {
    let mesaj;
    try {
      mesaj = JSON.parse(olay.data);
    } catch (hata) {
      return;
    }
    sayac += 1;

    // Panel sohbetinin cevabı mı?
    if (!mesaj.islem && mesaj.id && bekleyenSohbet.has(mesaj.id)) {
      const kayit = bekleyenSohbet.get(mesaj.id);
      bekleyenSohbet.delete(mesaj.id);
      clearTimeout(kayit.zaman);
      kayit.coz(mesaj);
      return;
    }

    // Çekirdekten gelen istek (sayfa_gozlem).
    const cevap = await islemYap(mesaj);
    if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(cevap));
  };
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
  baglan();
});
chrome.runtime.onStartup.addListener(() => { baglan(); });

chrome.runtime.onMessage.addListener((mesaj, _gonderen, yanitla) => {
  if (!mesaj || !mesaj.tip) return;

  if (mesaj.tip === "durum") {
    yanitla({ durum, sonHata, sayac });
    return true;
  }
  if (mesaj.tip === "baglan") {
    (async () => {
      if (mesaj.sunucu !== undefined || mesaj.anahtar !== undefined) {
        await chrome.storage.local.set({
          sunucu: String(mesaj.sunucu || "").trim() || VARSAYILAN_SUNUCU,
          anahtar: String(mesaj.anahtar || "").trim()
        });
      }
      if (baglanti) { try { baglanti.close(); } catch (hata) {} baglanti = null; }
      deneme = 0;
      if (yenidenZaman !== null) { clearTimeout(yenidenZaman); yenidenZaman = null; }
      await baglan();
      yanitla({ durum, sonHata });
    })();
    return true;
  }
  if (mesaj.tip === "sohbet") {
    (async () => {
      yanitla(await sohbetGonder(String(mesaj.metin || ""), mesaj.gecmis));
    })();
    return true;
  }
  if (mesaj.tip === "onizleme") {
    (async () => {
      try {
        yanitla({ ok: true, gozlem: await gozlemAl() });
      } catch (hata) {
        yanitla({ ok: false, hata: String(hata.message || hata) });
      }
    })();
    return true;
  }
  return undefined;
});

baglan();
