// app.js — Başak web sohbet yüzü.
// Tek beyin kuralı korunur: bu dosya yalnız arayüz, tarayıcı geçmişi ve HTTP köprüsüdür.

const chatEl = document.getElementById("chat");
const chatScrollEl = document.getElementById("chatScroll");
const heroEl = document.getElementById("hero");
const msgEl = document.getElementById("message");
const sendEl = document.getElementById("send");
const imageEl = document.getElementById("image");
const imageNameEl = document.getElementById("imageName");
const previewEl = document.getElementById("attachmentPreview");
const previewThumbEl = document.getElementById("attachmentThumb");
const removeImageEl = document.getElementById("removeImage");
const micEl = document.getElementById("micButton");
const composerNoteEl = document.getElementById("composerNote");
const historyListEl = document.getElementById("historyList");
const historyEmptyEl = document.getElementById("historyEmpty");
const sidebarEl = document.getElementById("sidebar");
const sidebarToggleEl = document.getElementById("sidebarToggle");
const sidebarBackdropEl = document.getElementById("sidebarBackdrop");
const kimlikSatirEl = document.getElementById("kimlikSatir");
const kullaniciAdEl = document.getElementById("kullaniciAd");
const CHATS_BASE = "basak_cloud_chats_v2";
const ACTIVE_BASE = "basak_cloud_active_chat_v2";
const UYARI_NOTU = "Başak hata yapabilir. Önemli bilgileri doğrulayın.";

function kimlikDegeri() {
  return String(window.basakKimlik?.kullanici || "").trim();
}
function depoAnahtari(taban) {
  const kid = kimlikDegeri();
  if (!kid) throw new Error("Başak kimliği hazır değil");
  return taban + ":" + kid;
}

let seciliGorsel = null;
let onizlemeUrl = "";
let gonderiliyor = false;
let chats = [];
let activeChatId = "";
let bulutGecmisi = [];

function sohbetId() {
  if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
  return "chat-" + Date.now() + "-" + Math.random().toString(16).slice(2);
}

function sohbetBasligi(messages) {
  const ilk = (messages || []).find((m) => m.role === "user" && String(m.content || "").trim());
  const ham = ilk ? String(ilk.content).trim().replace(/\s+/g, " ") : "Yeni sohbet";
  return ham.length > 38 ? ham.slice(0, 38) + "…" : ham;
}

function depoyuYukle() {
  chats = [];
  activeChatId = "";
  bulutGecmisi = [];
  try {
    const kayitli = JSON.parse(localStorage.getItem(depoAnahtari(CHATS_BASE)) || "[]");
    if (Array.isArray(kayitli)) chats = kayitli;
  } catch {}
  try { activeChatId = localStorage.getItem(depoAnahtari(ACTIVE_BASE)) || ""; } catch {}
  const aktif = chats.find((c) => c.id === activeChatId);
  if (aktif && Array.isArray(aktif.messages)) {
    bulutGecmisi = aktif.messages.slice();
  } else {
    activeChatId = "";
    bulutGecmisi = [];
  }
}

function depoyuKaydet() {
  try {
    localStorage.setItem(depoAnahtari(CHATS_BASE), JSON.stringify(chats));
    if (activeChatId) localStorage.setItem(depoAnahtari(ACTIVE_BASE), activeChatId);
    else localStorage.removeItem(depoAnahtari(ACTIVE_BASE));
  } catch {}
}

function aktifSohbetiKaydet() {
  if (!bulutGecmisi.length) return;

  if (!activeChatId) activeChatId = sohbetId();
  const simdi = Date.now();
  const kayit = {
    id: activeChatId,
    title: sohbetBasligi(bulutGecmisi),
    messages: bulutGecmisi.slice(),
    updatedAt: simdi,
  };

  const i = chats.findIndex((c) => c.id === activeChatId);
  if (i >= 0) chats[i] = kayit;
  else chats.unshift(kayit);

  chats.sort((a, b) => Number(b.updatedAt || 0) - Number(a.updatedAt || 0));
  depoyuKaydet();
  gecmisCiz();
}

function gecmisCiz() {
  if (!historyListEl) return;
  historyListEl.textContent = "";

  for (const chat of chats) {
    if (!Array.isArray(chat.messages) || !chat.messages.length) continue;
    const b = document.createElement("button");
    b.type = "button";
    b.className = "history-item" + (chat.id === activeChatId ? " active" : "");
    b.textContent = chat.title || sohbetBasligi(chat.messages);
    b.title = b.textContent;
    b.addEventListener("click", () => sohbetiAc(chat.id));
    historyListEl.appendChild(b);
  }

  if (historyEmptyEl) historyEmptyEl.hidden = !!historyListEl.children.length;
}

function kacis(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function bicimle(metin) {
  let h = kacis(metin);
  h = h.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  h = h.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  return h.replace(/\n/g, "<br>");
}

function icerikYaz(b, metin) {
  b.dataset.ham = String(metin || "");
  let ic = b.querySelector(".icerik");
  if (!ic) {
    ic = document.createElement("div");
    ic.className = "icerik";
    b.appendChild(ic);
  }
  ic.innerHTML = bicimle(metin || "");
}

function sohbetAlta() {
  if (chatScrollEl) chatScrollEl.scrollTop = chatScrollEl.scrollHeight;
}

function bubble(role, text) {
  if (heroEl) heroEl.hidden = true;

  const row = document.createElement("div");
  row.className = "message-row " + role;

  const b = document.createElement("div");
  b.className = "bubble";

  if (role === "assistant") {
    const head = document.createElement("div");
    head.className = "assistant-head";
    const mark = document.createElement("span");
    mark.className = "assistant-mark";
    mark.textContent = "B";
    const name = document.createElement("span");
    name.textContent = "Başak";
    head.appendChild(mark);
    head.appendChild(name);
    b.appendChild(head);
  }

  icerikYaz(b, text);
  row.appendChild(b);
  chatEl.appendChild(row);
  sohbetAlta();
  return b;
}

function gorselBalonaEkle(b, file) {
  if (!b || !file) return;
  const url = URL.createObjectURL(file);
  const img = document.createElement("img");
  img.className = "sent-image";
  img.alt = "Gönderilen fotoğraf";
  img.src = url;
  img.onload = () => URL.revokeObjectURL(url);
  b.appendChild(img);
}

function sohbetiCiz() {
  chatEl.textContent = "";
  balonlar.clear();

  if (!bulutGecmisi.length) {
    if (heroEl) heroEl.hidden = false;
    return;
  }

  if (heroEl) heroEl.hidden = true;
  for (const m of bulutGecmisi) {
    if (m.role === "user") bubble("user", m.content || "");
    else if (m.role === "assistant") bubble("assistant", m.content || "");
  }
  sohbetAlta();
}

function sohbetiAc(id) {
  const secilen = chats.find((c) => c.id === id);
  if (!secilen) return;
  activeChatId = secilen.id;
  bulutGecmisi = Array.isArray(secilen.messages) ? secilen.messages.slice() : [];
  depoyuKaydet();
  gecmisCiz();
  sohbetiCiz();
  sidebarKapat();
  msgEl.focus();
}

function durumSatiri(b, metin) {
  if (!b) return;
  let s = b.querySelector(".status-line");
  if (!s) {
    s = document.createElement("span");
    s.className = "status-line";
    b.appendChild(s);
  }
  s.textContent = metin || "";
}

function durumuKapat(b) {
  if (!b) return;
  b.querySelector(".status-line")?.remove();
}

function autoResize() {
  msgEl.style.height = "auto";
  msgEl.style.height = Math.min(msgEl.scrollHeight, 160) + "px";
}

function gonderimDurumu() {
  const dolu = !!msgEl.value.trim() || !!seciliGorsel;
  sendEl.disabled = gonderiliyor || !dolu;
}

function notYaz(metin) {
  if (composerNoteEl?.firstChild) composerNoteEl.firstChild.textContent = metin;
}

function onizlemeTemizle() {
  seciliGorsel = null;
  if (imageEl) imageEl.value = "";
  if (imageNameEl) imageNameEl.textContent = "";
  if (onizlemeUrl) {
    URL.revokeObjectURL(onizlemeUrl);
    onizlemeUrl = "";
  }
  if (previewThumbEl) previewThumbEl.removeAttribute("src");
  if (previewEl) previewEl.hidden = true;
  gonderimDurumu();
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
    const file = imageEl.files && imageEl.files[0] ? imageEl.files[0] : null;
    if (!file) {
      onizlemeTemizle();
      return;
    }
    if (!String(file.type || "").startsWith("image/")) {
      onizlemeTemizle();
      notYaz("Yalnız fotoğraf eklenebilir.");
      return;
    }

    seciliGorsel = file;
    if (onizlemeUrl) URL.revokeObjectURL(onizlemeUrl);
    onizlemeUrl = URL.createObjectURL(file);
    if (previewThumbEl) previewThumbEl.src = onizlemeUrl;
    if (imageNameEl) imageNameEl.textContent = file.name;
    if (previewEl) previewEl.hidden = false;
    notYaz("Fotoğraf mesajla birlikte gönderilecek.");
    gonderimDurumu();
  });
}

if (removeImageEl) removeImageEl.addEventListener("click", onizlemeTemizle);

msgEl.addEventListener("input", () => {
  autoResize();
  gonderimDurumu();
});

const balonlar = new Map();
const uyu = (ms) => new Promise((coz) => setTimeout(coz, ms));

function olayiIsle(o) {
  const no = o.istek;

  if (o.tur === "thinking") {
    if (!balonlar.has(no)) balonlar.set(no, bubble("assistant", "Düşünüyorum…"));
    return false;
  }

  if (o.tur === "toolStatus") {
    let b = balonlar.get(no);
    if (!b) {
      b = bubble("assistant", "");
      balonlar.set(no, b);
    }
    durumSatiri(b, o.metin || "İşleniyor…");
    return false;
  }

  if (o.tur === "parca") {
    let b = balonlar.get(no);
    if (!b) {
      b = bubble("assistant", "");
      balonlar.set(no, b);
    }
    durumuKapat(b);
    const ham = b.dataset.ham || "";
    const ilk = !ham || ham === "Düşünüyorum…";
    icerikYaz(b, ilk ? (o.metin || "") : ham + (o.metin || ""));
    sohbetAlta();
    return false;
  }

  if (o.tur === "bitir") {
    let b = balonlar.get(no);
    if (!b) b = bubble("assistant", o.cevap || "…");
    else {
      durumuKapat(b);
      const ham = b.dataset.ham || "";
      if (!ham || ham === "Düşünüyorum…" || ham === "…") icerikYaz(b, o.cevap || "…");
    }
    balonlar.delete(no);
    sohbetAlta();
    return true;
  }

  if (o.tur === "error") {
    const b = balonlar.get(no);
    if (b) {
      const row = b.closest(".message-row");
      if (row) row.remove(); else b.remove();
    }
    bubble("assistant", "Bir sorun oluştu: " + (o.metin || "Yanıt alınamadı."));
    balonlar.delete(no);
    return true;
  }

  return false;
}

async function jsonOku(r) {
  const raw = await r.text();
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error("Sunucu geçerli bir yanıt vermedi.");
  }
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
    const d = await jsonOku(r);
    for (const o of (d.olaylar || [])) {
      if (olayiIsle(o)) return;
    }
    son = Number.isInteger(d.son) ? d.son : son;
    if (d.bitti) return;
    await uyu(350);
  }

  throw new Error("Başak yanıtı zaman aşımına uğradı.");
}

const MISAFIR = new URLSearchParams(location.search).get("misafir") === "1";

async function yeniSohbet() {
  try {
    await window.basakFetch("/api/yeni", { method: "POST" });
  } catch {}

  activeChatId = "";
  bulutGecmisi = [];
  depoyuKaydet();
  gecmisCiz();
  sohbetiCiz();
  onizlemeTemizle();
  msgEl.value = "";
  msgEl.style.height = "auto";
  notYaz(UYARI_NOTU);
  gonderimDurumu();
  sidebarKapat();
  msgEl.focus();
}

for (const id of ["yeni", "yeniSide"]) {
  const el = document.getElementById(id);
  if (el) el.addEventListener("click", yeniSohbet);
}

async function send() {
  const text = msgEl.value.trim();
  const gorsel = seciliGorsel;
  if ((!text && !gorsel) || gonderiliyor) return;

  const gonderilecekMetin = text || "Bu görüntüyü açıkla.";
  const userBubble = bubble("user", text || "Fotoğraf gönderildi");
  if (gorsel) gorselBalonaEkle(userBubble, gorsel);

  msgEl.value = "";
  msgEl.style.height = "auto";
  gonderiliyor = true;
  gonderimDurumu();
  notYaz("Başak yanıtlıyor…");

  try {
    let ek = null;
    if (gorsel && window.basakRuntime === "vercel") {
      ek = {ad:gorsel.name,tur:"image",data_url:await gorseliDataUrl(gorsel)};
    }

    const r = await window.basakFetch("/api/sohbet", {
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({
        metin:gonderilecekMetin,
        misafir:MISAFIR,
        gecmis:bulutGecmisi,
        ek,
      }),
    });

    const d = await jsonOku(r);

    if (Array.isArray(d.olaylar)) {
      for (const o of d.olaylar) olayiIsle(o);
      if (!r.ok || !d.ok) throw new Error(d.error || "Sohbet isteği başarısız");

      if (d.cevap) {
        bulutGecmisi.push({role:"user",content:gonderilecekMetin});
        bulutGecmisi.push({role:"assistant",content:d.cevap});
        aktifSohbetiKaydet();
      }
      onizlemeTemizle();
      return;
    }

    if (!r.ok || !d.ok || !d.istek) throw new Error(d.error || "Sohbet isteği başarısız");
    if (!balonlar.has(d.istek)) balonlar.set(d.istek,bubble("assistant","Düşünüyorum…"));
    await olaylariTakipEt(d.istek);

    const sonBalon = chatEl.querySelector(".message-row.assistant:last-child .icerik");
    const cevap = sonBalon ? sonBalon.textContent || "" : "";
    if (cevap) {
      bulutGecmisi.push({role:"user",content:gonderilecekMetin});
      bulutGecmisi.push({role:"assistant",content:cevap});
      aktifSohbetiKaydet();
    }
    onizlemeTemizle();
  } catch (err) {
    bubble("assistant", "Bir sorun oluştu: " + (err.message || err));
  } finally {
    gonderiliyor = false;
    notYaz(UYARI_NOTU);
    gonderimDurumu();
    msgEl.focus();
  }
}

sendEl.addEventListener("click", send);

document.querySelectorAll(".ornek").forEach((d) => {
  d.addEventListener("click", () => {
    msgEl.value = d.textContent.trim();
    autoResize();
    gonderimDurumu();
    msgEl.focus();
  });
});

msgEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    send();
  }
});

function sesleYaz() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    notYaz("Bu tarayıcı sesle yazmayı desteklemiyor.");
    return;
  }

  const r = new SpeechRecognition();
  r.lang = "tr-TR";
  r.interimResults = false;
  r.maxAlternatives = 1;

  r.onstart = () => {
    micEl.classList.add("listening");
    notYaz("Dinliyorum…");
  };
  r.onresult = (e) => {
    const metin = e.results?.[0]?.[0]?.transcript || "";
    msgEl.value = [msgEl.value.trim(), metin.trim()].filter(Boolean).join(" ");
    autoResize();
    gonderimDurumu();
  };
  r.onerror = () => notYaz("Ses algılanamadı. Tekrar deneyebilirsin.");
  r.onend = () => {
    micEl.classList.remove("listening");
    if (composerNoteEl?.firstChild?.textContent === "Dinliyorum…") {
      notYaz(UYARI_NOTU);
    }
    msgEl.focus();
  };

  try { r.start(); }
  catch { notYaz("Mikrofon başlatılamadı."); }
}

if (micEl) micEl.addEventListener("click", sesleYaz);

function sidebarAc() {
  if (!sidebarEl) return;
  sidebarEl.classList.add("open");
  if (sidebarBackdropEl) sidebarBackdropEl.hidden = false;
}
function sidebarKapat() {
  if (!sidebarEl) return;
  sidebarEl.classList.remove("open");
  if (sidebarBackdropEl) sidebarBackdropEl.hidden = true;
}
if (sidebarToggleEl) sidebarToggleEl.addEventListener("click", sidebarAc);
if (sidebarBackdropEl) sidebarBackdropEl.addEventListener("click", sidebarKapat);

function kimligiCiz() {
  const d = window.basakKimlik;
  if (!d || !kimlikSatirEl || !kullaniciAdEl) return;
  kullaniciAdEl.textContent = "Başak ID · " + (d.basak_id || d.kullanici);
  kimlikSatirEl.hidden = false;
}

function eskiTarayiciVerisiniTemizle() {
  try {
    if (localStorage.getItem("basak_clean_start_v2") === "1") return;
    for (const ad of [
      "basak_cloud_chats_v1",
      "basak_cloud_active_chat",
      "basak_cloud_history",
      "basak_kullanici",
    ]) localStorage.removeItem(ad);
    localStorage.setItem("basak_clean_start_v2", "1");
  } catch {}
}

async function baslat() {
  try {
    await window.basakKimlikHazir;
    eskiTarayiciVerisiniTemizle();
    depoyuYukle();
    gecmisCiz();
    sohbetiCiz();
    autoResize();
    gonderimDurumu();
    kimligiCiz();
    notYaz(UYARI_NOTU);
    msgEl.focus();
  } catch (e) {
    notYaz("Başak kimliği oluşturulamadı. Sayfayı yenileyin.");
    sendEl.disabled = true;
  }
}
baslat();
