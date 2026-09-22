// common.js — saglik bilgisi + token akisi.
// Dis erisimde (LAN/internet) kopru token ister: bir kez sorar,
// localStorage'a yazar, sonra her HTTP isteginde tasir.
// Sormadan kutu cikarmaz: kod yalniz 401'de istenir.
//
// NOT: HTTP basliklari yalniz ISO-8859-1 (tek bayt) tasiyabilir.
// Kullanici Turkce karakter/bosluk yapistirirsa fetch BASLIK OKUMADA
// patlar ("non ISO-8859-1 code point") — istek hic gitmez, ekranda
// "Hata: Failed to execute fetch" gorunur. Bu yuzden kod her yazimda
// ve her okumada suzulur; sadece tek bayt gecerli karakterler kalir.
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

window.basakFetch = async (yol, secenek = {}) => {
  const t = window.basakToken();
  const basliklar = { ...(secenek.headers || {}) };
  if (t) basliklar["X-Basak-Token"] = t;
  let r = await fetch(yol, { ...secenek, headers: basliklar });
  if (r.status === 401) {
    const y = window.basakKodIste();
    if (!y) return r;
    location.reload();
    return r;
  }
  return r;
};

async function basakHealth() {
  try {
    const r = await window.basakFetch("/api/durum", { cache: "no-store" });
    const dot = document.getElementById("healthDot");
    const text = document.getElementById("healthText");
    const ok = r.ok;
    let d = {};
    try { d = await r.json(); } catch {}
    if (dot) dot.classList.toggle("ok", ok && d.ok);
    window.basakRuntime = d.runtime || "local";
    const imagePick = document.getElementById("imagePick");
    if (imagePick) imagePick.hidden = window.basakRuntime !== "vercel";
    const runtimeNote = document.getElementById("runtimeNote");
    if (runtimeNote) runtimeNote.firstChild.textContent = window.basakRuntime === "vercel" ?
      "Bulut Başak çalışıyor; bilgisayarın açık olmak zorunda değil. " :
      "Yerel Başak köprüsü çalışıyor. ";
    if (text) {
      if (r.status === 401) {
        text.textContent = "Kod gerekli";
      } else if (!ok || !d.ok) {
        text.textContent = "Köprü hatası";
      } else {
        const sag = (d.saglayicilar || []).join(", ") || "model yok";
        text.textContent = "Hazır · " + sag + " · " +
          (d.arac_sayisi || 0) + " araç · " + (d.commit || "?");
      }
    }

    const bar = document.getElementById("modelBarAlt")
      || document.getElementById("modelBar");
    if (bar) {
      bar.textContent = "";
      for (const m of (d.modeller || [])) {
        const chip = document.createElement("div");
        chip.className = "modelchip";
        const ad = document.createElement("strong");
        ad.textContent = m.ad;
        chip.appendChild(ad);

        const model = m.model && m.model !== "dogrulanamadi" ?
          " · " + m.model : "";
        const guc = document.createTextNode(
          model + " · " + ((m.gucleri || []).join("/") || "genel"));
        chip.appendChild(guc);

        const l = m.limit || {};
        const k = m.kullanim || {};
        const parca = [];
        if (l.saatlik_istek) parca.push((k.saat || 0) + "/" +
          l.saatlik_istek + " saat");
        if (l.gunluk_istek) parca.push((k.gun || 0) + "/" +
          l.gunluk_istek + " gün");
        if (l.aylik_istek) parca.push((k.ay || 0) + "/" +
          l.aylik_istek + " ay");
        if (l.gunluk_token) parca.push((k.bugun_token || 0) + "/" +
          l.gunluk_token + " token");
        if (!parca.length) parca.push("kota: sağlayıcı dinamik");

        const q = document.createElement("span");
        q.className = "quota";
        q.textContent = parca.join(" · ");
        chip.appendChild(q);
        bar.appendChild(chip);
      }
      const eksik = d.eksik_saglayicilar || [];
      if (eksik.length) {
        const chip = document.createElement("div");
        chip.className = "modelchip";
        const ad = document.createElement("strong");
        ad.textContent = "Bağlı değil";
        chip.appendChild(ad);
        const q = document.createElement("span");
        q.className = "quota";
        q.textContent = eksik.join(", ");
        chip.appendChild(q);
        bar.appendChild(chip);
      }
    }
    return ok && !!d.ok;
  } catch (e) {
    const text = document.getElementById("healthText");
    if (text) text.textContent = "Bağlantı yok";
    return false;
  }
}
window.basakHealth = basakHealth;
basakHealth();
setInterval(basakHealth, 30000);
