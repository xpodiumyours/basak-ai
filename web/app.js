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
let aktifIstekDenetleyici = null;
let kullaniciDurdurdu = false;

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
    const kayitli = JSON.parse(
      localStorage.getItem(depoAnahtari(CHATS_BASE)) || "[]"
    );
    if (Array.isArray(kayitli)) chats = kayitli;
  } catch {}
  try {
    activeChatId = localStorage.getItem(depoAnahtari(ACTIVE_BASE)) || "";
  } catch {}

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
    if (activeChatId) {
      localStorage.setItem(depoAnahtari(ACTIVE_BASE), activeChatId);
    } else {
      localStorage.removeItem(depoAnahtari(ACTIVE_BASE));
    }
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
  if (gonderiliyor) {
    notYaz("Başak yanıtlıyor…");
    return;
  }
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

const durumSaatleri = new Map();

function sureMetni(ms) {
  const sn = Math.max(0, Math.floor(ms / 1000));
  return String(Math.floor(sn / 60)).padStart(2, "0") + ":" +
    String(sn % 60).padStart(2, "0");
}

function guvenliDurumBilgisi(metin) {
  const ham = String(metin || "").trim();
  if (!ham) return { baslik: "İşleniyor", detay: "" };

  const i = ham.indexOf(": ");
  const baslik = (i > 0 ? ham.slice(0, i) : ham)
    .replace(/[.…]+$/, "").trim() || "İşleniyor";
  if (i <= 0) return { baslik, detay: "" };

  let detay = ham.slice(i + 2).trim();
  if (!detay) return { baslik, detay: "" };

  detay = detay
    .replace(/\b(Bearer)\s+[A-Za-z0-9._~+/=-]+/gi, "$1 [gizli]")
    .replace(/\b(sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,})\b/g, "[gizli]")
    .replace(/([?&](?:token|api[_-]?key|key|secret|password|auth|authorization)=)[^&#\s]+/gi, "$1[gizli]")
    .replace(/\b(?:token|api[_-]?key|secret|password|authorization)\s*[:=]\s*\S+/gi, "[gizli]");

  if (/^https?:\/\//i.test(detay)) {
    try {
      const u = new URL(detay);
      detay = u.host + u.pathname;
    } catch {}
  } else if (/^[A-Za-z]:\\|^\/Users\/|^\/home\//.test(detay)) {
    const parcalar = detay.replace(/\\/g, "/").split("/").filter(Boolean);
    detay = "…/" + parcalar.slice(-2).join("/");
  }

  detay = detay.replace(/\s+/g, " ").trim();
  if (detay.length > 120) detay = detay.slice(0, 117) + "…";
  return { baslik, detay };
}

function guvenliDurum(metin) {
  const d = guvenliDurumBilgisi(metin);
  return d.detay ? d.baslik + " — " + d.detay : d.baslik + "…";
}

function calismaKaydi(b) {
  let kayit = durumSaatleri.get(b);
  if (kayit) return kayit;

  const kart = document.createElement("section");
  kart.className = "work-card";
  kart.setAttribute("aria-live", "off");

  const ust = document.createElement("div");
  ust.className = "work-head";

  const nokta = document.createElement("span");
  nokta.className = "work-pulse";
  nokta.setAttribute("aria-hidden", "true");

  const baslik = document.createElement("strong");
  baslik.className = "work-title";
  baslik.textContent = "Başak çalışıyor";

  const sure = document.createElement("span");
  sure.className = "work-time";
  sure.textContent = "00:00";

  ust.append(nokta, baslik, sure);

  const mevcut = document.createElement("div");
  mevcut.className = "work-current";

  const mevcutBaslik = document.createElement("strong");
  mevcutBaslik.className = "work-current-title";

  const mevcutDetay = document.createElement("span");
  mevcutDetay.className = "work-current-detail";

  mevcut.append(mevcutBaslik, mevcutDetay);

  const ozet = document.createElement("div");
  ozet.className = "work-summary";
  ozet.hidden = true;

  const eylemler = document.createElement("div");
  eylemler.className = "work-actions";

  const detaylar = document.createElement("button");
  detaylar.type = "button";
  detaylar.className = "work-action";
  detaylar.textContent = "Detaylar";
  detaylar.hidden = true;
  detaylar.setAttribute("aria-expanded", "false");

  const durdur = document.createElement("button");
  durdur.type = "button";
  durdur.className = "work-action work-stop";
  durdur.textContent = "Durdur";

  eylemler.append(detaylar, durdur);

  const panel = document.createElement("div");
  panel.className = "work-details";
  panel.hidden = true;

  const liste = document.createElement("ol");
  liste.className = "work-steps";
  panel.appendChild(liste);

  const canli = document.createElement("span");
  canli.className = "sr-only";
  canli.setAttribute("role", "status");
  canli.setAttribute("aria-live", "polite");
  canli.setAttribute("aria-atomic", "true");

  kart.append(ust, mevcut, ozet, eylemler, panel);

  const icerik = b.querySelector(".icerik");
  if (icerik) b.insertBefore(kart, icerik);
  else b.appendChild(kart);
  b.appendChild(canli);

  kayit = {
    baslangic: Date.now(),
    metin: "",
    aktif: null,
    adimlar: [],
    zamanlayici: null,
    kart, baslik, sure, mevcut, mevcutBaslik, mevcutDetay,
    ozet, detaylar, durdur, panel, liste, canli,
    bitti: false,
  };

  detaylar.addEventListener("click", () => {
    const ac = panel.hidden;
    panel.hidden = !ac;
    detaylar.setAttribute("aria-expanded", ac ? "true" : "false");
    detaylar.textContent = ac ? "Gizle" : "Detaylar";
  });

  durdur.addEventListener("click", () => {
    if (kayit.bitti) return;
    kullaniciDurdurdu = true;
    if (aktifIstekDenetleyici) aktifIstekDenetleyici.abort();
    calismaDurdur(b);
  });

  durumSaatleri.set(b, kayit);
  return kayit;
}

function adimlariCiz(kayit) {
  kayit.liste.textContent = "";
  for (const adim of kayit.adimlar) {
    const li = document.createElement("li");
    li.className = "work-step done";
    const ikon = document.createElement("span");
    ikon.className = "work-step-mark";
    ikon.textContent = "✓";
    const metin = document.createElement("span");
    metin.className = "work-step-copy";
    metin.textContent = adim.detay
      ? adim.baslik + " — " + adim.detay
      : adim.baslik;
    li.append(ikon, metin);
    kayit.liste.appendChild(li);
  }

  if (!kayit.bitti && kayit.aktif && kayit.aktif.tur === "tool") {
    const li = document.createElement("li");
    li.className = "work-step active";
    const ikon = document.createElement("span");
    ikon.className = "work-step-mark";
    ikon.textContent = "•";
    const metin = document.createElement("span");
    metin.className = "work-step-copy";
    metin.textContent = kayit.aktif.detay
      ? kayit.aktif.baslik + " — " + kayit.aktif.detay
      : kayit.aktif.baslik;
    li.append(ikon, metin);
    kayit.liste.appendChild(li);
  }

  const detayVar = kayit.adimlar.length > 0 ||
    (!kayit.bitti && kayit.aktif && kayit.aktif.tur === "tool");
  kayit.detaylar.hidden = !detayVar;

  if (!kayit.bitti) {
    const sayi = kayit.adimlar.length;
    kayit.ozet.hidden = sayi === 0;
    kayit.ozet.textContent = sayi ? sayi + " adım tamamlandı" : "";
  }
}

function aktifAdimiTamamla(kayit) {
  if (!kayit?.aktif || kayit.aktif.tur !== "tool") return;
  kayit.adimlar.push({
    baslik: kayit.aktif.baslik,
    detay: kayit.aktif.detay || "",
  });
  kayit.aktif = null;
  adimlariCiz(kayit);
}

function durumSatiri(b, metin, tur = "thinking") {
  if (!b) return;
  const kayit = calismaKaydi(b);
  const bilgi = guvenliDurumBilgisi(metin);

  if (tur === "toolStatus") aktifAdimiTamamla(kayit);

  kayit.aktif = {
    baslik: bilgi.baslik,
    detay: bilgi.detay,
    tur: tur === "toolStatus" ? "tool" : tur,
  };
  kayit.metin = guvenliDurum(metin);
  kayit.mevcutBaslik.textContent = bilgi.baslik;
  kayit.mevcutDetay.textContent = bilgi.detay;
  kayit.mevcutDetay.hidden = !bilgi.detay;
  kayit.canli.textContent = kayit.metin;
  adimlariCiz(kayit);

  const yaz = () => {
    kayit.sure.textContent = sureMetni(Date.now() - kayit.baslangic);
  };
  yaz();
  if (!kayit.zamanlayici) kayit.zamanlayici = setInterval(yaz, 1000);
}

function calismaYanitaGecti(b) {
  const kayit = durumSaatleri.get(b);
  if (!kayit || kayit.bitti) return;
  aktifAdimiTamamla(kayit);
  kayit.aktif = { baslik: "Yanıt yazılıyor", detay: "", tur: "yanit" };
  kayit.mevcutBaslik.textContent = "Yanıt yazılıyor";
  kayit.mevcutDetay.hidden = true;
  kayit.canli.textContent = "Yanıt yazılıyor";
  adimlariCiz(kayit);
}

function calismaBitir(b) {
  const kayit = durumSaatleri.get(b);
  if (!kayit || kayit.bitti) return;
  aktifAdimiTamamla(kayit);
  kayit.bitti = true;
  if (kayit.zamanlayici) clearInterval(kayit.zamanlayici);
  kayit.zamanlayici = null;
  const toplamSure = sureMetni(Date.now() - kayit.baslangic);
  const sayi = kayit.adimlar.length;
  kayit.kart.classList.add("done");
  kayit.baslik.textContent = sayi
    ? sayi + " adım tamamlandı"
    : "Yanıt tamamlandı";
  kayit.sure.textContent = toplamSure;
  kayit.mevcut.hidden = true;
  kayit.ozet.hidden = true;
  kayit.ozet.textContent = "";
  kayit.durdur.remove();
  kayit.detaylar.hidden = sayi === 0;
  kayit.panel.hidden = true;
  kayit.detaylar.setAttribute("aria-expanded", "false");
  kayit.detaylar.textContent = "Detaylar";
  kayit.canli.textContent = kayit.baslik.textContent;
  adimlariCiz(kayit);
}

function calismaDurdur(b) {
  const kayit = durumSaatleri.get(b);
  if (!kayit || kayit.bitti) return;
  kayit.bitti = true;
  if (kayit.zamanlayici) clearInterval(kayit.zamanlayici);
  kayit.zamanlayici = null;
  kayit.kart.classList.add("stopped");
  kayit.baslik.textContent = "Durduruldu";
  kayit.sure.textContent = sureMetni(Date.now() - kayit.baslangic);
  kayit.mevcut.hidden = true;
  kayit.ozet.hidden = false;
  kayit.ozet.textContent = kayit.adimlar.length
    ? kayit.adimlar.length + " adım tamamlandı · Yeni adım başlatılmayacak."
    : "Yeni adım başlatılmayacak.";
  kayit.durdur.remove();
  kayit.detaylar.hidden = kayit.adimlar.length === 0;
  kayit.panel.hidden = true;
  kayit.detaylar.setAttribute("aria-expanded", "false");
  kayit.detaylar.textContent = "Detaylar";
  kayit.canli.textContent = "Başak durduruldu";
  adimlariCiz(kayit);
}

function durumuKapat(b) {
  const kayit = durumSaatleri.get(b);
  if (!kayit) return;
  if (kayit.zamanlayici) clearInterval(kayit.zamanlayici);
  kayit.zamanlayici = null;
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
  if (composerNoteEl) composerNoteEl.textContent = metin;
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

  if (o.tur === "ping") return false;

  if (o.tur === "thinking") {
    let b = balonlar.get(no);
    if (!b) {
      b = bubble("assistant", "");
      balonlar.set(no, b);
    }
    durumSatiri(b, "Düşünüyorum…", "thinking");
    return false;
  }

  if (o.tur === "toolStatus") {
    let b = balonlar.get(no);
    if (!b) {
      b = bubble("assistant", "");
      balonlar.set(no, b);
    }
    durumSatiri(b, o.metin, "toolStatus");
    return false;
  }

  if (o.tur === "parca") {
    let b = balonlar.get(no);
    if (!b) {
      b = bubble("assistant", "");
      balonlar.set(no, b);
    }
    calismaYanitaGecti(b);
    const ham = b.dataset.ham || "";
    icerikYaz(b, ham + (o.metin || ""));
    sohbetAlta();
    return false;
  }

  if (o.tur === "bitir") {
    let b = balonlar.get(no);
    if (!b) b = bubble("assistant", o.cevap || "…");
    else {
      calismaBitir(b);
      const ham = b.dataset.ham || "";
      if (!ham || ham === "Düşünüyorum…" || ham === "…") {
        icerikYaz(b, o.cevap || "…");
      }
    }
    balonlar.delete(no);
    sohbetAlta();
    return true;
  }

  if (o.tur === "error") {
    const b = balonlar.get(no);
    if (b) {
      durumuKapat(b);
      const row = b.closest(".message-row");
      if (row) row.remove(); else b.remove();
    }
    bubble("assistant", "Bir sorun oluştu: " + (o.metin || "Yanıt alınamadı."));
    balonlar.delete(no);
    return true;
  }

  return false;
}

function olayiBaslangicBalonunaBagla(o, b) {
  if (b && o && o.istek && !balonlar.has(o.istek)) {
    balonlar.set(o.istek, b);
  }
}

async function canliYanitiOku(r, baslangicBalonu) {
  if (!r.body || typeof r.body.getReader !== "function") {
    throw new Error("Tarayıcı canlı yanıt akışını desteklemiyor.");
  }

  const okuyucu = r.body.getReader();
  const cozumleyici = new TextDecoder();
  let tampon = "";
  let sonuc = { ok: false, cevap: "", kaynak: "", hata: "" };

  const satiriIsle = (satir) => {
    if (!satir.trim()) return;
    let o;
    try {
      o = JSON.parse(satir);
    } catch {
      throw new Error("Başak canlı akışında geçersiz veri alındı.");
    }
    if (o.tur === "ping") return;
    olayiBaslangicBalonunaBagla(o, baslangicBalonu);
    olayiIsle(o);
    if (o.tur === "bitir") {
      sonuc = {
        ok: true,
        cevap: String(o.cevap || ""),
        kaynak: String(o.kaynak || ""),
        hata: "",
      };
    } else if (o.tur === "error") {
      sonuc = {
        ok: false,
        cevap: "",
        kaynak: "",
        hata: String(o.metin || "Yanıt alınamadı."),
      };
    }
  };

  while (true) {
    let okuma;
    try {
      okuma = await okuyucu.read();
    } catch (e) {
      // bitir/error zaten geldiyse kullanıcıya gösterilmiş terminal sonucu
      // sonradan olan bağlantı kapanması yüzünden silme.
      if (sonuc.ok || sonuc.hata) break;
      throw e;
    }
    const { value, done } = okuma;
    if (value) tampon += cozumleyici.decode(value, { stream: true });

    let yeniSatir;
    while ((yeniSatir = tampon.indexOf("\n")) >= 0) {
      const satir = tampon.slice(0, yeniSatir);
      tampon = tampon.slice(yeniSatir + 1);
      satiriIsle(satir);
    }

    if (done) break;
  }

  tampon += cozumleyici.decode();
  if (tampon.trim()) satiriIsle(tampon);

  if (!sonuc.ok && !sonuc.hata) {
    throw new Error("Başak yanıtı tamamlanmadan bağlantı kapandı.");
  }
  return sonuc;
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
  if (gonderiliyor) {
    notYaz("Başak yanıtlıyor…");
    return;
  }
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

  const bekleyenBalon = bubble("assistant", "");
  aktifIstekDenetleyici = new AbortController();
  kullaniciDurdurdu = false;
  durumSatiri(bekleyenBalon, "Mesaj Başak’a iletiliyor…", "thinking");

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
      headers:{
        "content-type":"application/json",
        "accept":"application/x-ndjson",
      },
      body:JSON.stringify({
        metin:gonderilecekMetin,
        misafir:MISAFIR,
        gecmis:bulutGecmisi,
        ek,
      }),
      signal:aktifIstekDenetleyici.signal,
    });

    const tur = String(r.headers.get("content-type") || "").toLowerCase();
    if (tur.includes("application/x-ndjson")) {
      if (!r.ok) throw new Error("Sohbet isteği başarısız (" + r.status + ")");
      const sonuc = await canliYanitiOku(r, bekleyenBalon);
      if (!sonuc.ok) {
        onizlemeTemizle();
        return;
      }
      if (sonuc.cevap) {
        bulutGecmisi.push({role:"user",content:gonderilecekMetin});
        bulutGecmisi.push({role:"assistant",content:sonuc.cevap});
        aktifSohbetiKaydet();
      }
      onizlemeTemizle();
      return;
    }

    const d = await jsonOku(r);

    if (Array.isArray(d.olaylar)) {
      for (const o of d.olaylar) {
        olayiBaslangicBalonunaBagla(o, bekleyenBalon);
        olayiIsle(o);
      }
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
    if (!balonlar.has(d.istek)) balonlar.set(d.istek,bekleyenBalon);
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
    if (kullaniciDurdurdu && err && err.name === "AbortError") {
      calismaDurdur(bekleyenBalon);
    } else {
      durumuKapat(bekleyenBalon);
      const row = bekleyenBalon.closest(".message-row");
      if (row) row.remove();
      bubble("assistant", "Bir sorun oluştu: " + (err.message || err));
    }
  } finally {
    aktifIstekDenetleyici = null;
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
    if (composerNoteEl?.textContent === "Dinliyorum…") {
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

async function baslat() {
  try {
    await window.basakKimlikHazir;
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
