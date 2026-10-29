// common.js — kayıt zorunluluğu olmadan kullanıcı ayrımı + sağlık bilgisi.
// İlk ziyarette sunucu rastgele Başak ID üretir. Yetki, ID numarasıyla değil
// imzalı HttpOnly çerezle doğrulanır.

window.basakKimlik = null;
window.basakLegacyBridge = false;
let kimlikPromise = null;
let basakTokenSoruldu = false;

window.basakTokenTemiz = (s) =>
  String(s || "").split("").filter((c) => c.charCodeAt(0) <= 255).join("");
window.basakToken = () =>
  window.basakTokenTemiz(localStorage.getItem("basak_token") || "");
window.basakKodIste = () => {
  const ham = prompt("Başak köprüsü erişim kodu (token):") || "";
  const t = window.basakTokenTemiz(ham).trim();
  if (t) localStorage.setItem("basak_token", t);
  return t;
};

// Fotoğrafı GÖNDERMEDEN ÖNCE tarayıcıda küçültür.
// Neden: sunucu gövdesinin tavanı var (Vercel ~4,5 MB). 8 MP bir telefon
// fotoğrafının ham hâli base64 ile ~8-11 MB olur ve istek sunucuya hiç
// ulaşmaz (HTTP 413). 1600 px JPEG ise ~200-500 KB kalır.
// Dönen değer data URL'dir; fotoğraf değilse/okunamazsa hata atar.
window.basakFotografiKucult = async (dosya, enBuyukKenar = 1600,
                                     kalite = 0.82) => {
  if (!dosya || !String(dosya.type || "").startsWith("image/")) {
    throw new Error("Yalnız fotoğraf yüklenebilir");
  }
  const ham = await new Promise((coz, reddet) => {
    const r = new FileReader();
    r.onload = () => coz(r.result);
    r.onerror = () => reddet(new Error("Fotoğraf okunamadı"));
    r.readAsDataURL(dosya);
  });
  const resim = await new Promise((coz, reddet) => {
    const i = new Image();
    i.onload = () => coz(i);
    i.onerror = () => reddet(new Error("Fotoğraf açılamadı"));
    i.src = ham;
  });
  const oran = Math.min(1, enBuyukKenar / Math.max(resim.width, resim.height));
  const tuval = document.createElement("canvas");
  tuval.width = Math.max(1, Math.round(resim.width * oran));
  tuval.height = Math.max(1, Math.round(resim.height * oran));
  tuval.getContext("2d").drawImage(resim, 0, 0, tuval.width, tuval.height);
  return tuval.toDataURL("image/jpeg", kalite);
};

async function kimlikHazirla(zorla = false) {
  if (kimlikPromise && !zorla) return kimlikPromise;

  kimlikPromise = (async () => {
    const r = await fetch("/api/kimlik", {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    let d = {};
    try { d = await r.json(); } catch {}
    if (r.status === 404) {
      // Yerel eski köprü /api/kimlik bilmiyorsa özel yerel oturum korunur.
      window.basakLegacyBridge = true;
      d = { ok: true, kullanici: "casper", basak_id: "Yerel / özel oturum", legacy: true };
    } else if (!r.ok || !d.ok || !d.kullanici) {
      throw new Error(d.error || "Başak kimliği oluşturulamadı.");
    }
    window.basakKimlik = d;
    try {
      localStorage.setItem("basak_son_kullanici", String(d.kullanici));
      localStorage.setItem("basak_son_id", String(d.basak_id || d.kullanici));
    } catch {}
    window.dispatchEvent(new CustomEvent("basak:kimlik", { detail: d }));
    return d;
  })();

  try {
    return await kimlikPromise;
  } catch (e) {
    kimlikPromise = null;
    throw e;
  }
}
window.basakKimlikHazir = (async () => {
  if (window.BasakPrivateAccess) await window.BasakPrivateAccess.ready;
  return kimlikHazirla();
})();

window.basakFetch = async (yol, secenek = {}) => {
  if (yol !== "/api/kimlik") await window.basakKimlikHazir;

  const kos = () => {
    const basliklar = new Headers(secenek.headers || {});
    if (window.basakLegacyBridge) {
      const t = window.basakToken();
      if (t) basliklar.set("X-Basak-Token", t);
    }
    return fetch(yol, { credentials: "same-origin", ...secenek, headers: basliklar });
  };

  let r = await kos();
  if (r.status === 401 && yol !== "/api/kimlik") {
    let hata = "";
    try { hata = (await r.clone().json()).error || ""; } catch {}
    if (window.basakLegacyBridge && hata === "token gecersiz" && !basakTokenSoruldu) {
      basakTokenSoruldu = true;
      if (window.basakKodIste()) r = await kos();
      return r;
    }
    if (!window.basakLegacyBridge) {
      window.basakKimlikHazir = kimlikHazirla(true);
      await window.basakKimlikHazir;
      r = await kos();
    }
  }
  return r;
};

// Ust durum yalniz sorun varken gorunur; saglikliyken calisma durumunu
// zaten calisma karti gosterir, ikinci bir "Hazır" yazisi yaniltir.
function saglikGoster(sorun) {
  const kutu = document.getElementById("healthStatus");
  const text = document.getElementById("healthText");
  if (text) text.textContent = sorun || "";
  if (kutu) kutu.hidden = !sorun;
}

async function basakHealth() {
  try {
    await window.basakKimlikHazir;
    const r = await window.basakFetch("/api/durum", { cache: "no-store" });
    const dot = document.getElementById("healthDot");
    const ok = r.ok;
    let d = {};
    try { d = await r.json(); } catch {}
    if (dot) dot.classList.toggle("ok", ok && d.ok);
    window.basakRuntime = d.runtime || "local";
    const imagePick = document.getElementById("imagePick");
    if (imagePick) imagePick.hidden = window.basakRuntime !== "vercel";
    saglikGoster(ok && d.ok ? "" : "Bağlantı sorunu");
    return ok && !!d.ok;
  } catch (e) {
    saglikGoster("Bağlantı yok");
    return false;
  }
}
window.basakHealth = basakHealth;

window.basakKimlikHazir
  .then(() => {
    basakHealth();
    setInterval(basakHealth, 30000);
    return window.basakFetch("/api/sohbetler", { cache: "no-store" });
  })
  .catch((e) => {
    saglikGoster(e.message || "Başak’a ulaşılamadı.");
  });
