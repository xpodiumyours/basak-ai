// common.js — saglik pigili. Tek arka uca bakar: yerel kopru.
async function basakHealth() {
  try {
    const r = await fetch("/api/matris", { cache: "no-store" });
    const dot = document.getElementById("healthDot");
    const text = document.getElementById("healthText");
    const ok = r.ok;
    if (dot) dot.classList.toggle("ok", ok);
    if (text) text.textContent = ok ? "Köprü hazır" : "Köprü hatası";
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
