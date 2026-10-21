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

async function sekmeAl() {
  const sekmeler = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  const sekme = sekmeler && sekmeler[0];
  if (!sekme || !sekme.id) throw new Error("açık sekme bulunamadı");
  return sekme;
}

async function sekmeyeSor(istek, sekme) {
  const hedef = sekme || (await sekmeAl());
  try {
    return await chrome.tabs.sendMessage(hedef.id, istek);
  } catch (hata) {
    // Eklenti kurulmadan önce açılmış sekmede içerik betiği yoktur.
    try {
      await chrome.scripting.executeScript({ target: { tabId: hedef.id }, files: ["icerik.js"] });
      return await chrome.tabs.sendMessage(hedef.id, istek);
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

/* ── Onay kapısı ────────────────────────────────────────────────────
 * Kural: tıklama ve yazma, KULLANICI ONAYI OLMADAN uygulanmaz. Karar
 * kodun değil kullanıcının: panel bir kart gösterir, Onayla/Vazgeç der.
 * Panel kapalıysa istek kimseye ulaşmaz → eylem YAPILMAZ (fail-closed).
 * "5 dakika sorma" kutusu işaretlenirse yalnız o sekme için muafiyet
 * saklanır; süre dolunca kapı yine sorar.
 */
const ONAY_SURESI = 60000;        // panel cevabı için üst sınır (ms)
const ONAY_MUAFIYET = 5 * 60 * 1000;
let onaySayaci = 0;
const bekleyenOnay = new Map();   // istekId -> {coz, zaman, sekmeId}

async function muafiyetOku() {
  try {
    const veri = await chrome.storage.session.get("onayMuafiyet");
    return veri ? veri.onayMuafiyet || null : null;
  } catch (hata) {
    return null;                  // oturum deposu yoksa muafiyet de yok
  }
}

async function muafiyetYaz(sekmeId) {
  try {
    await chrome.storage.session.set({
      onayMuafiyet: { sekmeId, bitis: Date.now() + ONAY_MUAFIYET }
    });
  } catch (hata) { /* muafiyet yazılamazsa her eylemde sorulur */ }
}

async function onayIste(sekme, islem, ayrinti) {
  const muaf = await muafiyetOku();
  if (muaf && muaf.sekmeId === sekme.id && muaf.bitis > Date.now()) {
    return { onay: true, muaf: true };
  }

  onaySayaci += 1;
  const istekId = "o" + onaySayaci;
  const cevap = new Promise((coz) => {
    const zaman = setTimeout(() => {
      const kayit = bekleyenOnay.get(istekId);
      if (!kayit) return;
      bekleyenOnay.delete(istekId);
      coz({ onay: false, hata: "Onay gelmedi (60 saniye)." });
    }, ONAY_SURESI);
    bekleyenOnay.set(istekId, { coz, zaman, sekmeId: sekme.id });
  });

  try {
    await chrome.runtime.sendMessage({
      tip: "onay", istekId, islem,
      sekmeId: sekme.id,
      ad: ayrinti.ad || "",
      rol: ayrinti.rol || "",
      metin: ayrinti.metin || "",
      url: ayrinti.url || ""
    });
  } catch (hata) {
    // Panel açık değil: soru kimseye ulaşmadı. Sessizce uygulamak yok.
    const kayit = bekleyenOnay.get(istekId);
    if (kayit) {
      clearTimeout(kayit.zaman);
      bekleyenOnay.delete(istekId);
    }
    return { onay: false,
      hata: "Onay için Başak paneli açık olmalı (araç çubuğu simgesi)." };
  }
  return cevap;
}

async function eylemAyrinti(sekme, sira, metin) {
  const ayrinti = { ad: "", rol: "", url: "", metin: metin || "" };
  try {
    const gozlem = await sekmeyeSor({ tip: "gozlem" }, sekme);
    if (gozlem && !gozlem.hata) {
      ayrinti.url = gozlem.url || "";
      const oge = (gozlem.ogeler || []).find((o) => o.sira === sira);
      if (oge) {
        ayrinti.ad = oge.ad || "";
        ayrinti.rol = oge.rol || "";
      }
    }
  } catch (hata) { /* ayrıntı yoksa da onay sorulur */ }
  return ayrinti;
}

async function eylemiUygula(mesaj, istek, sekme, metin) {
  const veri = mesaj.veri || {};
  const ayrinti = await eylemAyrinti(sekme, veri.sira, metin);
  const onay = await onayIste(sekme, mesaj.islem, ayrinti);
  if (!onay.onay) {
    return { id: mesaj.id, ok: false, hata: onay.hata || "Kullanıcı onay vermedi." };
  }
  const cevap = await sekmeyeSor(istek, sekme);
  if (!cevap) throw new Error("sayfa cevap vermedi (sekme yenilenmeli)");
  if (cevap.hata) return { id: mesaj.id, ok: false, hata: cevap.hata };
  return { id: mesaj.id, ok: true, sonuc: cevap.sonuc };
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
      const sekme = await sekmeAl();
      return await eylemiUygula(mesaj, { tip: "tikla", sira: veri.sira }, sekme, "");
    }
    if (mesaj.islem === "sayfa_yaz") {
      const sekme = await sekmeAl();
      return await eylemiUygula(
        mesaj, { tip: "yaz", sira: veri.sira, metin: veri.metin }, sekme, veri.metin);
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
  if (mesaj.tip === "onay-cevap") {
    const kayit = bekleyenOnay.get(mesaj.istekId);
    if (!kayit) { yanitla({ ok: false, hata: "onay isteği bulunamadı" }); return true; }
    clearTimeout(kayit.zaman);
    bekleyenOnay.delete(mesaj.istekId);
    if (mesaj.onay && mesaj.muaf) muafiyetYaz(kayit.sekmeId);
    kayit.coz({ onay: !!mesaj.onay });
    yanitla({ ok: true });
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
