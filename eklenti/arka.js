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
const bekleyenKutu = new Map();     // kutu yoklamasi -> cozucu
/* Paylasimli kutu yoklamasi (P6b): web sohbeti baska instance'ta kalsa
 * bile kutuya biraktigi isi bu baglanti alir. Is mevcut islemYap yolundan
 * kosar: onay kapisi aynen gecerli, karar verilmez. */
const KUTU_ARALIK = 3000;
const KUTU_SURE = 15000;
let kutuZaman = null;
let kutuMesgul = false;

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

async function sekmeyeSor(istek, sekme, cerceveId) {
  const hedef = sekme || (await sekmeAl());
  const secenek = (cerceveId === undefined || cerceveId === null)
    ? undefined : { frameId: Number(cerceveId) };
  try {
    return await chrome.tabs.sendMessage(hedef.id, istek, secenek);
  } catch (hata) {
    // Eklenti kurulmadan önce açılmış sekmede içerik betiği yoktur.
    try {
      await chrome.scripting.executeScript({
        target: { tabId: hedef.id, allFrames: true }, files: ["icerik.js"] });
      return await chrome.tabs.sendMessage(hedef.id, istek, secenek);
    } catch (hata2) {
      throw new Error("bu sekme okunamıyor (chrome:// veya mağaza sayfası olabilir)");
    }
  }
}

/* Çerçeveler: sayfanın gömülü çerçeveleri (iframe) AYNI gözlemde
 * birleşir. Her çerçeve kendi kimliğini taşır ("0" = ana çerçeve);
 * eylem ref'teki çerçeveye yönlenir. Yürütme ana dünyadan değil,
 * betiğin İZOLE dünyasından okunur: __basakGozlem orada yaşar.
 */
function gozlemleriBirlestir(sonuclar) {
  const ogeler = [];
  let url = "";
  let baslik = "";
  let anaVar = false;
  for (const kayit of sonuclar || []) {
    const gozlem = kayit && kayit.result;
    if (!gozlem || gozlem.hata || !Array.isArray(gozlem.ogeler)) continue;
    const cerceve = String(kayit.frameId);
    if (cerceve === "0" && !anaVar) {
      url = gozlem.url || url;
      baslik = gozlem.baslik || baslik;
      anaVar = true;
    }
    for (const oge of gozlem.ogeler) {
      const kopya = {};
      for (const anahtar in oge) kopya[anahtar] = oge[anahtar];
      kopya.cerceve = cerceve;
      ogeler.push(kopya);
    }
  }
  if (!anaVar && ogeler.length) {
    url = url || "";
  }
  return { url, baslik, ogeler };
}

async function gozlemAl() {
  const sekme = await sekmeAl();
  let sonuclar;
  try {
    sonuclar = await chrome.scripting.executeScript({
      target: { tabId: sekme.id, allFrames: true },
      func: () => (typeof __basakGozlem === "function" ? __basakGozlem() : null)
    });
  } catch (hata) {
    return { hata: "bu sekme okunamıyor (chrome:// veya mağaza sayfası olabilir)" };
  }
  return gozlemleriBirlestir(sonuclar);
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

/* ── Paylasimli kutu (web sohbetinden dogrudan surus) ─────────────── */
function kutuIste(islem, veri, sure) {
  return new Promise((coz) => {
    if (!baglanti || baglanti.readyState !== WebSocket.OPEN) {
      coz({ ok: false, hata: "Bağlantı yok." });
      return;
    }
    cagriSayaci += 1;
    const id = "k" + cagriSayaci;
    const zaman = setTimeout(() => {
      bekleyenKutu.delete(id);
      coz({ ok: false, hata: "kutu cevabi gelmedi" });
    }, sure || KUTU_SURE);
    bekleyenKutu.set(id, { coz, zaman });
    try {
      baglanti.send(JSON.stringify({ id, islem, veri: veri || {} }));
    } catch (hata) {
      bekleyenKutu.delete(id);
      clearTimeout(zaman);
      coz({ ok: false, hata: "gonderilemedi" });
    }
  });
}

async function kutuYokla() {
  if (kutuMesgul) return;
  if (!baglanti || baglanti.readyState !== WebSocket.OPEN) return;
  kutuMesgul = true;
  try {
    const cevap = await kutuIste("kutu_al", {});
    const is = cevap && cevap.ok && cevap.sonuc;
    if (!is || is.bos || !is.id || !is.islem) return;
    let uyg;
    try {
      uyg = await islemYap({ id: is.id, islem: is.islem, veri: is.veri || {} });
    } catch (hata) {
      uyg = { id: is.id, ok: false, hata: String(hata && hata.message || hata) };
    }
    await kutuIste("kutu_yaz", { job: is.id, cevap: uyg });
  } finally {
    kutuMesgul = false;
  }
}

function kutuBaslat() {
  kutuDurdur();
  kutuZaman = setInterval(() => { kutuYokla(); }, KUTU_ARALIK);
}

function kutuDurdur() {
  if (kutuZaman !== null) { clearInterval(kutuZaman); kutuZaman = null; }
  kutuMesgul = false;
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

async function eylemAyrinti(sekme, sira, metin, cerceveId) {
  const ayrinti = { ad: "", rol: "", url: "", metin: metin || "" };
  try {
    // Ayrıntı HEDEF çerçeveden okunur: sıra numaraları çerçeve başına
    // olduğu için birleşik listede arama yanlış öğeyi bulabilirdi.
    const gozlem = await sekmeyeSor({ tip: "gozlem" }, sekme, cerceveId);
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
  const cerceveId = (veri.cerceve === undefined || veri.cerceve === null)
    ? undefined : String(veri.cerceve);
  const ayrinti = await eylemAyrinti(sekme, veri.sira, metin, cerceveId);
  const onay = await onayIste(sekme, mesaj.islem, ayrinti);
  if (!onay.onay) {
    return { id: mesaj.id, ok: false, hata: onay.hata || "Kullanıcı onay vermedi." };
  }
  const cevap = await sekmeyeSor(istek, sekme, cerceveId);
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
    // Çerçeve kimliği ref'ten gelir (veri.cerceve); içerik betiği fazla
    // alanı görmezden gelir, arka plan hedef çerçeveye yönlendirir.
    if (mesaj.islem === "sayfa_tikla") {
      const sekme = await sekmeAl();
      return await eylemiUygula(
        mesaj, { tip: "tikla", sira: veri.sira, cerceve: veri.cerceve }, sekme, "");
    }
    if (mesaj.islem === "sayfa_yaz") {
      const sekme = await sekmeAl();
      return await eylemiUygula(
        mesaj, { tip: "yaz", sira: veri.sira, metin: veri.metin,
                 cerceve: veri.cerceve }, sekme, veri.metin);
    }
    // Tus form gönderebilir: tıklama/yazma ile aynı onay kapısından geçer.
    if (mesaj.islem === "sayfa_tus") {
      const sekme = await sekmeAl();
      return await eylemiUygula(
        mesaj, { tip: "tus", sira: veri.sira, tus: veri.tus,
                 cerceve: veri.cerceve }, sekme, "");
    }
    // Kaydırma veri değiştirmez: onay istenmez (salt-okunur eylem).
    if (mesaj.islem === "sayfa_kaydir") {
      const sekme = await sekmeAl();
      const cerceveId = (veri.cerceve === undefined || veri.cerceve === null)
        ? undefined : String(veri.cerceve);
      const cevap = await sekmeyeSor(
        { tip: "kaydir", sira: veri.sira, miktar: veri.miktar }, sekme, cerceveId);
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
  for (const [id, kayit] of bekleyenKutu) {
    clearTimeout(kayit.zaman);
    kayit.coz({ ok: false, hata: sebep });
    bekleyenKutu.delete(id);
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
    kutuBaslat();
    pingZamani = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        try { ws.send(JSON.stringify({ ping: Date.now() })); } catch (hata) {}
      }
    }, PING_ARALIK);
  };
  ws.onclose = () => {
    durdurPing();
    kutuDurdur();
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

    // Paylasimli kutu yoklamasinin cevabi mi?
    if (!mesaj.islem && mesaj.id && bekleyenKutu.has(mesaj.id)) {
      const kayit = bekleyenKutu.get(mesaj.id);
      bekleyenKutu.delete(mesaj.id);
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
  // Ayarlar sayfasındaki "Bağlantıyı sına": KAYDETMEDEN dener.
  if (mesaj.tip === "sina") {
    (async () => {
      const bas = Date.now();
      const sunucu = String(mesaj.sunucu || "").trim() || VARSAYILAN_SUNUCU;
      const anahtar = String(mesaj.anahtar || "").trim();
      const adres = anahtar
        ? sunucu + (sunucu.includes("?") ? "&" : "?") +
          "token=" + encodeURIComponent(anahtar)
        : sunucu;
      let ws;
      try {
        ws = new WebSocket(adres);
      } catch (hata) {
        yanitla({ ok: false, hata: "adres geçersiz: " + sunucu });
        return;
      }
      const sonuc = await new Promise((coz) => {
        const zaman = setTimeout(() => {
          try { ws.close(); } catch (hata) {}
          coz({ ok: false, hata: "zaman aşımı (8 sn)" });
        }, 8000);
        ws.onopen = () => {
          clearTimeout(zaman);
          try { ws.close(); } catch (hata) {}
          coz({ ok: true, ms: Date.now() - bas, durum: "bagli" });
        };
        ws.onerror = () => {
          clearTimeout(zaman);
          coz({ ok: false, hata: "adrese ulaşılamadı: " + sunucu });
        };
      });
      yanitla(sonuc);
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
