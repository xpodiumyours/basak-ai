// app.js — web sohbeti. Tek beyin kurali: yerel veya Vercel koprusu\n// ayni Python cekirdegine gider; web tarafinda ikinci beyin yoktur.
const chatEl = document.getElementById("chat");
const msgEl = document.getElementById("message");
const sendEl = document.getElementById("send");
const imageEl = document.getElementById("image");
const imageNameEl = document.getElementById("imageName");
let seciliGorsel = null;
let bulutGecmisi = [];
try {
  const kayitli = JSON.parse(localStorage.getItem("basak_cloud_history") || "[]");
  if (Array.isArray(kayitli)) bulutGecmisi = kayitli;
} catch {}

function bulutGecmisiniKaydet() {
  try { localStorage.setItem("basak_cloud_history", JSON.stringify(bulutGecmisi)); } catch {}
}

async function gorseliDataUrl(file) {
  if (!file || !String(file.type || "").startsWith("image/")) {
    throw new Error("Yalnız fotoğraf yüklenebilir");
  }
  const ham = await new Promise((coz, reddet) => {
    const r = new FileReader();
    r.onload = () => coz(r.result);
    r.onerror = () => reddet(new Error("Fotoğraf okunamadı"));
    r.readAsDataURL(file);
  });
  const img = await new Promise((coz, reddet) => {
    const i = new Image();
    i.onload = () => coz(i);
    i.onerror = () => reddet(new Error("Fotoğraf açılamadı"));
    i.src = ham;
  });
  const enBuyuk = 1600;
  const oran = Math.min(1, enBuyuk / Math.max(img.width, img.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(img.width * oran));
  canvas.height = Math.max(1, Math.round(img.height * oran));
  canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.82);
}

if (imageEl) {
  imageEl.addEventListener("change", () => {
    seciliGorsel = imageEl.files && imageEl.files[0] ? imageEl.files[0] : null;
    if (imageNameEl) imageNameEl.textContent = seciliGorsel ? seciliGorsel.name : "";
  });
}

const balonlar = new Map();
const sonAracDurumu = new Map();
const kapat = (el) => el && el.querySelector(".meta")?.remove();
const uyu = (ms) => new Promise((coz) => setTimeout(coz, ms));

function kacis(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// Guvenli mini bicim: once HTML'yi etkisizlestir, sonra yalniz
// **kalin**, `kod` ve satir sonu isle. Zararli kod calismaz.
function bicimle(metin) {
  let h = kacis(metin);
  h = h.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  h = h.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  return h.replace(/\n/g, "<br>");
}

function icerikYaz(b, metin) {
  b.dataset.ham = String(metin);
  let ic = b.querySelector(".icerik");
  if (!ic) {
    ic = document.createElement("div");
    ic.className = "icerik";
    b.prepend(ic);
  }
  ic.innerHTML = bicimle(metin);
}

function bubble(role, text, meta) {
  const el = document.createElement("div");
  el.className = "bubble " + role;
  icerikYaz(el, text);
  if (meta) {
    const m = document.createElement("span");
    m.className = "meta";
    m.textContent = meta;
    el.appendChild(m);
  }
  chatEl.appendChild(el);
  chatEl.scrollTop = chatEl.scrollHeight;
  return el;
}

function olayiIsle(o) {
  const no = o.istek;
  if (o.tur === "thinking") {
    if (!balonlar.has(no)) {
      balonlar.set(no, bubble("assistant", "Başak düşünüyor…"));
    }
    return false;
  }
  if (o.tur === "toolStatus") {
    sonAracDurumu.set(no, o.metin || "");
    let b = balonlar.get(no);
    if (b) {
      b.querySelector(".meta")?.remove();
      icerikYaz(b, "…");
      const m = document.createElement("span");
      m.className = "meta";
      m.textContent = o.metin;
      b.appendChild(m);
    } else {
      balonlar.set(no, bubble("assistant", "…", o.metin));
    }
    return false;
  }
  if (o.tur === "parca") {
    let b = balonlar.get(no);
    if (b) {
      kapat(b);
      const ham = b.dataset.ham ?? b.textContent;
      const ilk = ham === "…" || ham === "Başak düşünüyor…";
      icerikYaz(b, ilk ? o.metin : ham + o.metin);
    } else {
      b = bubble("assistant", o.metin);
      balonlar.set(no, b);
    }
    return false;
  }
  if (o.tur === "bitir") {
    let b = balonlar.get(no);
    if (b) {
      kapat(b);
      // Streaming olmayan ajan yolunda balonda yalniz "dusunuyor" kalmis
      // olabilir. Gercek final cevabi her durumda ekrana yaz.
      const ham = b.dataset.ham ?? b.textContent;
      if (!ham || ham === "Başak düşünüyor…" || ham === "…") {
        icerikYaz(b, o.cevap || "…");
      }
      const meta = [];
      if (o.kaynak) meta.push("Model: " + o.kaynak);
      if (sonAracDurumu.get(no)) {
        meta.push("Araç: " + sonAracDurumu.get(no));
      }
      if (meta.length) {
        const m = document.createElement("span");
        m.className = "meta";
        m.textContent = meta.join(" · ");
        b.appendChild(m);
      }
    } else {
      const meta = [];
      if (o.kaynak) meta.push("Model: " + o.kaynak);
      if (sonAracDurumu.get(no)) {
        meta.push("Araç: " + sonAracDurumu.get(no));
      }
      bubble("assistant", o.cevap || "…", meta.join(" · "));
    }
    sonAracDurumu.delete(no);
    balonlar.delete(no);
    return true;
  }
  if (o.tur === "error") {
    const b = balonlar.get(no);
    if (b) b.remove();
    bubble("assistant", "Hata: " + o.metin);
    sonAracDurumu.delete(no);
    balonlar.delete(no);
    return true;
  }
  return false;
}

async function olaylariTakipEt(no) {
  let son = 0;
  const baslangic = Date.now();
  while (Date.now() - baslangic < 12 * 60 * 1000) {
    const r = await window.basakFetch(
      "/api/olaylar?istek=" + encodeURIComponent(no) +
      "&son=" + encodeURIComponent(son),
      { cache: "no-store" },
    );
    if (!r.ok) throw new Error("Sohbet akışı okunamadı (" + r.status + ")");
    const d = await r.json();
    for (const o of (d.olaylar || [])) {
      if (olayiIsle(o)) return;
    }
    son = Number.isInteger(d.son) ? d.son : son;
    if (d.bitti) return;
    await uyu(350);
  }
  throw new Error("Başak yanıtı zaman aşımına uğradı");
}

const MISAFIR = new URLSearchParams(location.search).get("misafir") === "1";

// Kenar menusu: eski sohbetler + yeni. Misafirde gizli (perde).
async function listeyiYukle() {
  const kenar = document.getElementById("kenar");
  if (MISAFIR) {
    if (kenar) kenar.style.display = "none";
    return;
  }
  try {
    const r = await window.basakFetch("/api/sohbetler", { cache: "no-store" });
    if (!r.ok) return;
    const d = await r.json();
    const kutu = document.getElementById("liste");
    if (!kutu) return;
    kutu.textContent = "";
    for (const o of (d.liste || [])) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = o.baslik || "Sohbet";
      b.title = o.baslik || "Sohbet";
      b.addEventListener("click", () => sohbetiAc(o.id));
      kutu.appendChild(b);
    }
  } catch {}
}

async function sohbetiAc(id) {
  try {
    const r = await window.basakFetch(
      "/api/sohbet/" + encodeURIComponent(id), { cache: "no-store" });
    if (!r.ok) return;
    const d = await r.json();
    chatEl.textContent = "";
    balonlar.clear();
    for (const m of (d.mesajlar || [])) {
      if (m.role === "user") bubble("user", m.content || "");
      else if (m.role === "assistant") bubble("assistant", m.content || "");
    }
  } catch {}
}

async function yeniSohbet() {
  try {
    await window.basakFetch("/api/yeni", { method: "POST" });
  } catch {}
  chatEl.textContent = "";
  balonlar.clear();
  bulutGecmisi = [];
  bulutGecmisiniKaydet();
  seciliGorsel = null;
  if (imageEl) imageEl.value = "";
  if (imageNameEl) imageNameEl.textContent = "";
  bubble("assistant", "Yeni sohbet hazır. Mesajını yazabilirsin.");
  listeyiYukle();
}

const yeniDugme = document.getElementById("yeni");
if (yeniDugme) yeniDugme.addEventListener("click", yeniSohbet);
listeyiYukle();

async function send() {
  const text = msgEl.value.trim();
  const gorsel = seciliGorsel;
  if ((!text && !gorsel) || sendEl.disabled) return;
  const gonderilecekMetin = text || "Bu görüntüyü açıkla.";
  msgEl.value = "";
  bubble("user", text || ("[Fotoğraf] " + gorsel.name));
  sendEl.disabled = true;
  try {
    let ek = null;
    if (gorsel && window.basakRuntime === "vercel") {
      ek = { ad: gorsel.name, tur: "image", data_url: await gorseliDataUrl(gorsel) };
    }
    const r = await window.basakFetch("/api/sohbet", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        metin: gonderilecekMetin,
        misafir: MISAFIR,
        gecmis: bulutGecmisi,
        ek,
      }),
    });
    const d = await r.json();

    if (Array.isArray(d.olaylar)) {
      for (const o of d.olaylar) olayiIsle(o);
      if (!r.ok || !d.ok) throw new Error(d.error || "Sohbet isteği başarısız");
      if (d.cevap) {
        bulutGecmisi.push({ role: "user", content: gonderilecekMetin });
        bulutGecmisi.push({ role: "assistant", content: d.cevap });
        bulutGecmisiniKaydet();
      }
      seciliGorsel = null;
      if (imageEl) imageEl.value = "";
      if (imageNameEl) imageNameEl.textContent = "";
      return;
    }

    if (!r.ok || !d.ok || !d.istek) {
      throw new Error(d.error || "Sohbet isteği başarısız");
    }
    if (!balonlar.has(d.istek)) {
      balonlar.set(d.istek, bubble("assistant", "Başak düşünüyor…"));
    }
    await olaylariTakipEt(d.istek);
  } catch (err) {
    bubble("assistant", "Hata: " + (err.message || err));
  } finally {
    sendEl.disabled = false;
    msgEl.focus();
  }
}

sendEl.addEventListener("click", send);
document.querySelectorAll(".ornek").forEach((d) => {
  d.addEventListener("click", () => {
    msgEl.value = d.textContent.trim();
    msgEl.focus();
  });
});
msgEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
msgEl.focus();
