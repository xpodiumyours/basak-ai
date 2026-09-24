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
let yonlendirmeBekliyor = null;
let yonlendirmeIcinDurduruldu = false;

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

function sohbetAlta(zorla = true) {
  if (!chatScrollEl) return;
  const altaMesafe = chatScrollEl.scrollHeight -
    chatScrollEl.scrollTop - chatScrollEl.clientHeight;
  if (zorla || altaMesafe < 150) {
    chatScrollEl.scrollTop = chatScrollEl.scrollHeight;
  }
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

  const planEl = document.createElement("div");
  planEl.className = "work-plan";
  planEl.hidden = true;

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

  const yonlendir = document.createElement("button");
  yonlendir.type = "button";
  yonlendir.className = "work-action work-redirect";
  yonlendir.textContent = "Yönlendir";

  const durdur = document.createElement("button");
  durdur.type = "button";
  durdur.className = "work-action work-stop";
  durdur.textContent = "Durdur";

  eylemler.append(detaylar, yonlendir, durdur);

  const yonForm = document.createElement("form");
  yonForm.className = "work-redirect-form";
  yonForm.hidden = true;

  const yonInput = document.createElement("input");
  yonInput.type = "text";
  yonInput.className = "work-redirect-input";
  yonInput.placeholder = "Yeni yön ver…";
  yonInput.maxLength = 500;

  const yonUygula = document.createElement("button");
  yonUygula.type = "submit";
  yonUygula.className = "work-redirect-apply";
  yonUygula.textContent = "Uygula";

  yonForm.append(yonInput, yonUygula);

  const panel = document.createElement("div");
  panel.className = "work-details";

  const liste = document.createElement("ol");
  liste.className = "work-steps";
  panel.appendChild(liste);

  const canli = document.createElement("span");
  canli.className = "sr-only";
  canli.setAttribute("role", "status");
  canli.setAttribute("aria-live", "polite");
  canli.setAttribute("aria-atomic", "true");

  kart.append(ust, planEl, panel, mevcut, ozet, eylemler, yonForm);

  const kaynakBolumu = document.createElement("section");
  kaynakBolumu.className = "answer-sources";
  kaynakBolumu.hidden = true;

  const kaynakBaslik = document.createElement("strong");
  kaynakBaslik.className = "answer-sources-title";
  kaynakBaslik.textContent = "Kaynaklar";

  const kaynakListe = document.createElement("div");
  kaynakListe.className = "answer-sources-list";
  kaynakBolumu.append(kaynakBaslik, kaynakListe);

  const icerik = b.querySelector(".icerik");
  if (icerik) {
    b.insertBefore(kart, icerik);
    b.appendChild(kaynakBolumu);
  } else {
    b.append(kart, kaynakBolumu);
  }
  b.appendChild(canli);

  kayit = {
    baslangic: Date.now(),
    metin: "",
    aktif: null,
    adimlar: [],
    zamanlayici: null,
    kart, baslik, sure, mevcut, mevcutBaslik, mevcutDetay,
    ozet, detaylar, yonlendir, durdur, yonForm, yonInput,
    panel, liste, canli, planEl, kaynakBolumu, kaynakListe,
    plan: [], kaynaklar: [], yonlendirIstegi: null,
    bitti: false,
  };

  detaylar.addEventListener("click", () => {
    const ac = !kart.classList.contains("details-open");
    kart.classList.toggle("details-open", ac);
    detaylar.setAttribute("aria-expanded", ac ? "true" : "false");
    detaylar.textContent = ac ? "Gizle" : "Detaylar";
  });

  yonlendir.addEventListener("click", () => {
    if (kayit.bitti) return;
    yonForm.hidden = !yonForm.hidden;
    if (!yonForm.hidden) yonInput.focus();
  });

  yonForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const yon = yonInput.value.trim();
    if (!yon || kayit.bitti) return;
    if (typeof kayit.yonlendirIstegi === "function") {
      kayit.yonlendirIstegi(yon);
    }
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
    li.className = "work-step done" + (adim.ok === false ? " error" : "");

    const ikon = document.createElement("span");
    ikon.className = "work-step-mark";
    ikon.setAttribute("aria-hidden", "true");

    const govde = document.createElement("span");
    govde.className = "work-step-body";

    const baslik = document.createElement("span");
    baslik.className = "work-step-title";
    baslik.textContent = adim.baslik;

    const detay = document.createElement("span");
    detay.className = "work-step-detail";
    detay.textContent = adim.detay || "";
    detay.hidden = !adim.detay;

    govde.append(baslik, detay);
    li.append(ikon, govde);
    kayit.liste.appendChild(li);
  }

  const detayVar = kayit.adimlar.some((adim) => !!adim.detay) ||
    !!(kayit.aktif && kayit.aktif.detay);
  kayit.detaylar.hidden = !detayVar && kayit.adimlar.length === 0;

  if (!kayit.bitti) {
    kayit.ozet.hidden = true;
    kayit.ozet.textContent = "";
  }
}

function aktifAdimiTamamla(kayit, ok = true) {
  if (!kayit?.aktif || kayit.aktif.tur !== "tool") return;
  kayit.adimlar.push({
    baslik: kayit.aktif.baslik,
    detay: kayit.aktif.detay || "",
    ok,
  });
  kayit.aktif = null;
  adimlariCiz(kayit);
}

function planiGuncelle(b, adimlar) {
  const kayit = calismaKaydi(b);
  for (const adim of (Array.isArray(adimlar) ? adimlar : [])) {
    if (!adim || !adim.baslik) continue;
    const anahtar = String(adim.id || (adim.baslik + "|" + (adim.detay || "")));
    if (kayit.plan.some((x) => x.anahtar === anahtar)) continue;
    kayit.plan.push({
      anahtar,
      baslik: String(adim.baslik),
      detay: String(adim.detay || ""),
    });
  }
  if (!kayit.plan.length) return;
  const adlar = kayit.plan.map((x) => x.baslik.replace(/[.…]+$/, ""));
  const gorunen = adlar.slice(0, 4).join(" → ");
  const kalan = adlar.length > 4 ? " +" + (adlar.length - 4) : "";
  kayit.planEl.textContent = "Plan · " + gorunen + kalan;
  kayit.planEl.hidden = false;
}

function kaynakEkle(b, olay) {
  const kayit = calismaKaydi(b);
  let url;
  try {
    url = new URL(String(olay?.url || ""));
  } catch {
    return;
  }
  if (!["http:", "https:"].includes(url.protocol)) return;
  const temiz = url.origin + url.pathname;
  if (kayit.kaynaklar.some((x) => x.url === temiz)) return;
  kayit.kaynaklar.push({
    url: temiz,
    baslik: String(olay?.baslik || url.hostname || temiz),
  });

  kayit.kaynakListe.textContent = "";
  kayit.kaynaklar.forEach((k, i) => {
    const a = document.createElement("a");
    a.className = "answer-source";
    a.href = k.url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = (i + 1) + " · " + k.baslik;
    kayit.kaynakListe.appendChild(a);
  });
}

function araciTamamla(b, olay) {
  const kayit = calismaKaydi(b);
  aktifAdimiTamamla(kayit, olay?.ok !== false);
  if (!kayit.bitti) {
    kayit.aktif = { baslik: "Sonuç değerlendiriliyor", detay: "", tur: "thinking" };
    kayit.mevcutBaslik.textContent = "Sonuç değerlendiriliyor";
    kayit.mevcutDetay.hidden = true;
    kayit.canli.textContent = "Sonuç değerlendiriliyor";
    adimlariCiz(kayit);
  }
}

function yonlendirmeBaglamiOlustur(b, anaMetin) {
  const kayit = calismaKaydi(b);
  return {
    onceki_istek: String(anaMetin || "").slice(0, 2000),
    tamamlanan_adimlar: (kayit.adimlar || []).slice(-16).map((a) => ({
      baslik: String(a.baslik || "").slice(0, 160),
      detay: String(a.detay || "").slice(0, 240),
      ok: a.ok !== false,
    })),
    kullanilan_kaynaklar: (kayit.kaynaklar || []).slice(-16).map(
      (k) => String(k.url || "").slice(0, 500)
    ),
    kismi_cevap: String(b.dataset.ham || "").slice(-5000),
  };
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
  kayit.yonlendir.remove();
  kayit.yonForm.remove();
  kayit.kaynakBolumu.hidden = kayit.kaynaklar.length === 0;
  kayit.kart.classList.remove("details-open");
  kayit.detaylar.hidden = sayi === 0;
  kayit.detaylar.setAttribute("aria-expanded", "false");
  kayit.detaylar.textContent = "Detaylar";
  kayit.canli.textContent = kayit.baslik.textContent;
  adimlariCiz(kayit);
}

function calismaDurdur(b, neden = "durdur") {
  const kayit = durumSaatleri.get(b);
  if (!kayit || kayit.bitti) return;
  akiciMetniDurdur(b);
  kayit.bitti = true;
  if (kayit.zamanlayici) clearInterval(kayit.zamanlayici);
  kayit.zamanlayici = null;
  kayit.kart.classList.add("stopped");
  kayit.baslik.textContent = neden === "yonlendir"
    ? "Yeni yönle yeniden başlatılıyor"
    : "Durduruldu";
  kayit.sure.textContent = sureMetni(Date.now() - kayit.baslangic);
  kayit.mevcut.hidden = true;
  kayit.ozet.hidden = false;
  kayit.ozet.textContent = neden === "yonlendir"
    ? "Mevcut çalışma durduruldu · yeni yönle yeniden başlatılıyor."
    : (kayit.adimlar.length
      ? kayit.adimlar.length + " adım tamamlandı · Yeni adım başlatılmayacak."
      : "Yeni adım başlatılmayacak.");
  kayit.durdur.remove();
  if (kayit.yonlendir?.isConnected) kayit.yonlendir.remove();
  if (kayit.yonForm?.isConnected) kayit.yonForm.remove();
  kayit.kart.classList.remove("details-open");
  kayit.detaylar.hidden = kayit.adimlar.length === 0;
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
const metinAkislari = new Map();
const uyu = (ms) => new Promise((coz) => setTimeout(coz, ms));

function akisBirimleri(metin) {
  return String(metin || "").match(/\S+\s*|\s+/g) || [];
}

function akiciMetinKaydi(b) {
  let kayit = metinAkislari.get(b);
  if (kayit) return kayit;
  kayit = {
    hedef: "",
    gosterilen: "",
    kuyruk: [],
    zamanlayici: null,
    bekleyenler: [],
    gercekParcaGeldi: false,
  };
  metinAkislari.set(b, kayit);
  return kayit;
}

function akiciBekleyenleriCoz(kayit) {
  if (kayit.kuyruk.length || kayit.zamanlayici) return;
  const liste = kayit.bekleyenler.splice(0);
  for (const coz of liste) coz();
}

function akiciPompayiBaslat(b, kayit) {
  if (kayit.zamanlayici || !kayit.kuyruk.length) return;

  const azalt = typeof window !== "undefined" &&
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const adim = () => {
    kayit.zamanlayici = null;
    if (!kayit.kuyruk.length) {
      akiciBekleyenleriCoz(kayit);
      return;
    }

    const kalan = kayit.kuyruk.length;
    const adet = azalt ? kalan : (kalan > 100 ? 5 : kalan > 45 ? 3 : kalan > 18 ? 2 : 1);
    let ek = "";
    for (let i = 0; i < adet && kayit.kuyruk.length; i += 1) {
      ek += kayit.kuyruk.shift();
    }

    kayit.gosterilen += ek;
    icerikYaz(b, kayit.gosterilen);
    sohbetAlta(false);

    if (kayit.kuyruk.length) {
      kayit.zamanlayici = setTimeout(adim, azalt ? 0 : (kalan > 80 ? 16 : 30));
    } else {
      akiciBekleyenleriCoz(kayit);
    }
  };

  kayit.zamanlayici = setTimeout(adim, azalt ? 0 : 18);
}

function akiciMetinEkle(b, parca, gercekParca = false) {
  const metin = String(parca || "");
  if (!metin) return;
  const kayit = akiciMetinKaydi(b);
  kayit.hedef += metin;

  if (gercekParca) {
    kayit.gercekParcaGeldi = true;
    kayit.gosterilen += metin;
    icerikYaz(b, kayit.gosterilen);
    sohbetAlta(false);
    return;
  }

  kayit.kuyruk.push(...akisBirimleri(metin));
  akiciPompayiBaslat(b, kayit);
}

function akiciMetniBekle(b) {
  const kayit = akiciMetinKaydi(b);
  if (!kayit.kuyruk.length && !kayit.zamanlayici) return Promise.resolve();
  return new Promise((coz) => kayit.bekleyenler.push(coz));
}

function akiciMetniFinaleTamamla(b, finalMetin) {
  const final = String(finalMetin || "");
  const kayit = akiciMetinKaydi(b);

  if (final) {
    if (!kayit.hedef) {
      akiciMetinEkle(b, final);
    } else if (final.startsWith(kayit.hedef)) {
      akiciMetinEkle(b, final.slice(kayit.hedef.length));
    } else if (final !== kayit.hedef) {
      // Sağlayıcı final metni parçalardan farklı normalize ettiyse
      // tekrar yazmak yerine yalnız henüz görünmeyen kısmı güvenli tamamla.
      if (final.startsWith(kayit.gosterilen)) {
        kayit.hedef = final;
        kayit.kuyruk = akisBirimleri(final.slice(kayit.gosterilen.length));
        akiciPompayiBaslat(b, kayit);
      } else {
        kayit.hedef = final;
        kayit.gosterilen = final;
        kayit.kuyruk = [];
        if (kayit.zamanlayici) clearTimeout(kayit.zamanlayici);
        kayit.zamanlayici = null;
        icerikYaz(b, final);
      }
    }
  }

  return akiciMetniBekle(b);
}

function akiciMetniDurdur(b) {
  const kayit = metinAkislari.get(b);
  if (!kayit) return;
  if (kayit.zamanlayici) clearTimeout(kayit.zamanlayici);
  kayit.zamanlayici = null;
  kayit.kuyruk = [];
  akiciBekleyenleriCoz(kayit);
}

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

  if (o.tur === "plan") {
    let b = balonlar.get(no);
    if (!b) {
      b = bubble("assistant", "");
      balonlar.set(no, b);
    }
    planiGuncelle(b, o.adimlar);
    return false;
  }

  if (o.tur === "source") {
    let b = balonlar.get(no);
    if (!b) {
      b = bubble("assistant", "");
      balonlar.set(no, b);
    }
    kaynakEkle(b, o);
    return false;
  }

  if (o.tur === "toolDone") {
    const b = balonlar.get(no);
    if (b) araciTamamla(b, o);
    return false;
  }

  if (o.tur === "contextStatus") {
    let b = balonlar.get(no);
    if (!b) {
      b = bubble("assistant", "");
      balonlar.set(no, b);
    }
    const n = Number(o.atlanan || 0);
    durumSatiri(
      b,
      n > 0
        ? "Bağlam düzenlendi — " + n + " eski mesaj kalıcı geçmişte korundu"
        : "Bağlam ölçüldü",
      "thinking",
    );
    return false;
  }

  if (o.tur === "providerSwitch") {
    const b = balonlar.get(no);
    if (b) {
      const kayit = calismaKaydi(b);
      kayit.canli.textContent =
        "Sağlayıcı değişti: " + String(o.onceki || "") +
        " → " + String(o.yeni || "");
    }
    return false;
  }

  if (o.tur === "loopGuard") {
    const b = balonlar.get(no);
    if (b) {
      durumSatiri(
        b,
        "Tekrarlanan araç döngüsü durduruldu — " + String(o.tool || ""),
        "thinking",
      );
    }
    return false;
  }

  if (o.tur === "truncated") {
    const b = balonlar.get(no);
    if (b) {
      const kayit = calismaKaydi(b);
      kayit.canli.textContent = "Yanıt teknik çıktı sınırına ulaştı";
    }
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
    akiciMetinEkle(b, o.metin || "", true);
    return false;
  }

  if (o.tur === "bitir") {
    let b = balonlar.get(no);
    if (!b) {
      b = bubble("assistant", "");
      balonlar.set(no, b);
    }

    calismaYanitaGecti(b);
    const gorunurBitis = akiciMetniFinaleTamamla(b, o.cevap || "…")
      .then(() => {
        calismaBitir(b);
        sohbetAlta(false);
        return true;
      });

    balonlar.delete(no);
    return gorunurBitis;
  }

  if (o.tur === "error") {
    const b = balonlar.get(no);
    if (b) {
      akiciMetniDurdur(b);
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

  const satiriIsle = async (satir) => {
    if (!satir.trim()) return;
    let o;
    try {
      o = JSON.parse(satir);
    } catch {
      throw new Error("Başak canlı akışında geçersiz veri alındı.");
    }
    if (o.tur === "ping") return;
    olayiBaslangicBalonunaBagla(o, baslangicBalonu);
    const uiSonuc = olayiIsle(o);
    if (uiSonuc && typeof uiSonuc.then === "function") {
      await uiSonuc;
    }
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
      await satiriIsle(satir);
    }

    if (done) break;
  }

  tampon += cozumleyici.decode();
  if (tampon.trim()) await satiriIsle(tampon);

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
      if (await olayiIsle(o)) return;
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

async function send(secenek = {}) {
  if (secenek && typeof secenek.preventDefault === "function") secenek = {};
  const text = typeof secenek.text === "string"
    ? secenek.text.trim()
    : msgEl.value.trim();
  const gorsel = secenek.gorsel || seciliGorsel;
  if ((!text && !gorsel) || gonderiliyor) return;

  const gonderilecekMetin = text || "Bu görüntüyü açıkla.";
  const gorunenMetin = secenek.gorunenMetin || text || "Fotoğraf gönderildi";
  const userBubble = bubble("user", gorunenMetin);
  if (gorsel) gorselBalonaEkle(userBubble, gorsel);

  const bekleyenBalon = bubble("assistant", "");
  aktifIstekDenetleyici = new AbortController();
  kullaniciDurdurdu = false;
  durumSatiri(bekleyenBalon, "Mesaj Başak’a iletiliyor…", "thinking");
  const calisma = calismaKaydi(bekleyenBalon);
  calisma.yonlendir.hidden = !!gorsel;
  calisma.yonlendirIstegi = (yon) => {
    if (!gonderiliyor || calisma.bitti) return;
    yonlendirmeBekliyor = {
      yon,
      anaMetin: gonderilecekMetin,
      baglam: yonlendirmeBaglamiOlustur(
        bekleyenBalon, gonderilecekMetin
      ),
    };
    yonlendirmeIcinDurduruldu = true;
    kullaniciDurdurdu = true;
    if (aktifIstekDenetleyici) aktifIstekDenetleyici.abort();
    calismaDurdur(bekleyenBalon, "yonlendir");
  };

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
        yonlendirme_baglami:secenek.yonlendirmeBaglami || null,
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
      if (!yonlendirmeIcinDurduruldu) calismaDurdur(bekleyenBalon);
    } else {
      durumuKapat(bekleyenBalon);
      const row = bekleyenBalon.closest(".message-row");
      if (row) row.remove();
      bubble("assistant", "Bir sorun oluştu: " + (err.message || err));
    }
  } finally {
    const devam = yonlendirmeIcinDurduruldu ? yonlendirmeBekliyor : null;
    yonlendirmeBekliyor = null;
    yonlendirmeIcinDurduruldu = false;
    aktifIstekDenetleyici = null;
    gonderiliyor = false;
    notYaz(UYARI_NOTU);
    gonderimDurumu();

    if (devam) {
      // İlk kullanıcı görevi final almadı; yeni yönün bağlamında yine de
      // görünür kalsın. Yeni talimat normal kullanıcı mesajı olarak devam eder.
      bulutGecmisi.push({role:"user", content:gonderilecekMetin});
      aktifSohbetiKaydet();
      setTimeout(() => {
        send({
          text: devam.yon,
          gorunenMetin: "Yönlendirme: " + devam.yon,
          yonlendirmeBaglami: devam.baglam || null,
        });
      }, 0);
    } else {
      msgEl.focus();
    }
  }
}


sendEl.addEventListener("click", () => send());

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
