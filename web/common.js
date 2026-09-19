// common.js — saglik pigili + token akisi.
// Dis erisimde (LAN/internet) kopru token ister: bir kez sorar,
// localStorage'a yazar, sonra her istekte tasir (SSE icin ?token=).
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

window.basakSse = (yol) => {
  const t = window.basakToken();
  const ayirac = yol.includes("?") ? "&" : "?";
  return new EventSource(t ? yol + ayirac + "token=" +
    encodeURIComponent(t) : yol);
};

async function basakHealth() {
  try {
    const r = await window.basakFetch("/api/matris", { cache: "no-store" });
    const dot = document.getElementById("healthDot");
    const text = document.getElementById("healthText");
    const ok = r.ok;
    if (dot) dot.classList.toggle("ok", ok);
    if (text) text.textContent = ok ? "Köprü hazır" :
      (r.status === 401 ? "Kod gerekli" : "Köprü hatası");
    return ok;
  } catch (e) {
    const text = document.getElementById("healthText");
    if (text) text.textContent = "Bağlantı yok";
    return false;
  }
}
window.basakHealth = basakHealth;
basakHealth();
setInterval(basakHealth, 30000);
