// common.js — saglik bilgisi + token akisi.
// Dis erisimde (LAN/internet) kopru token ister: bir kez sorar,
// localStorage'a yazar, sonra her HTTP isteginde tasir.
window.basakToken = () => {
  let t = localStorage.getItem("basak_token");
  if (!t) {
    t = (prompt("Başak köprüsü erişim kodu (token):") || "").trim();
    if (t) localStorage.setItem("basak_token", t);
  }
  return t;
};

window.basakFetch = (yol, secenek = {}) => {
  const t = window.basakToken();
  const basliklar = { ...(secenek.headers || {}) };
  if (t) basliklar["X-Basak-Token"] = t;
  return fetch(yol, { ...secenek, headers: basliklar });
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
