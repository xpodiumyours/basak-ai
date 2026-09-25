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

// Satir ici bicim. Girdi ONCEDEN kacis()'tan gecmistir; burada uretilen
// etiketler disinda HTML olusmaz. Baglanti yalniz http(s) adresine verilir.
function satirIci(s) {
  s = s.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?![*\w])/g, "$1<em>$2</em>");
  s = s.replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  return s;
}

function basitBicimle(metin) {
  let h = kacis(metin);
  h = h.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  h = h.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  return h.replace(/\n/g, "<br>");
}

const TABLO_SATIRI = /^\s*\|.*\|\s*$/;
const TABLO_AYRACI = /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/;

function tabloHucreleri(satir) {
  return satir.trim().replace(/^\|/, "").replace(/\|$/, "").split("|")
    .map((h) => satirIci(h.trim()));
}

// Model cevabindaki markdown'i gorunume cevirir: baslik, madde/numarali
// liste (girintiyle ic ice), ayirici cizgi, kod blogu, tablo, baglanti.
// Metnin kendisine dokunmaz; yalniz nasil gosterilecegini belirler.
function bicimle(metin) {
  const satirlar = kacis(metin).split(/\r?\n/);
  const cikti = [];
  const listeler = [];
  let paragraf = [];
  let kod = null;

  const paragrafKapat = () => {
    if (!paragraf.length) return;
    cikti.push("<p>" + paragraf.map(satirIci).join("<br>") + "</p>");
    paragraf = [];
  };
  const listeKapat = () => {
    const ust = listeler.pop();
    cikti.push("</li></" + ust.tip + ">");
  };
  const listeleriKapat = () => { while (listeler.length) listeKapat(); };

  for (let i = 0; i < satirlar.length; i++) {
    const satir = satirlar[i];

    if (kod !== null) {
      if (/^\s*```/.test(satir)) {
        cikti.push("<pre><code>" + kod.join("\n") + "</code></pre>");
        kod = null;
      } else {
        kod.push(satir);
      }
      continue;
    }
    if (/^\s*```/.test(satir)) {
      paragrafKapat(); listeleriKapat();
      kod = [];
      continue;
    }

    if (TABLO_SATIRI.test(satir) && i + 1 < satirlar.length &&
        TABLO_AYRACI.test(satirlar[i + 1])) {
      paragrafKapat(); listeleriKapat();
      const basliklar = tabloHucreleri(satir);
      const govde = [];
      i += 2;
      while (i < satirlar.length && TABLO_SATIRI.test(satirlar[i])) {
        govde.push(tabloHucreleri(satirlar[i]));
        i++;
      }
      i--;
      cikti.push('<div class="tablo-kap"><table><thead><tr>' +
        basliklar.map((h) => "<th>" + h + "</th>").join("") +
        "</tr></thead><tbody>" +
        govde.map((s) => "<tr>" + s.map((h) => "<td>" + h + "</td>")
          .join("") + "</tr>").join("") +
        "</tbody></table></div>");
      continue;
    }

    if (/^\s{0,3}([-*_])(\s*\1){2,}\s*$/.test(satir)) {
      paragrafKapat(); listeleriKapat();
      cikti.push("<hr>");
      continue;
    }

    const baslik = satir.match(/^\s{0,3}(#{1,6})\s+(.+?)(?:\s+#+)?\s*$/);
    if (baslik) {
      paragrafKapat(); listeleriKapat();
      const seviye = Math.min(6, baslik[1].length + 2);
      cikti.push("<h" + seviye + ' class="md-baslik md-b' +
        baslik[1].length + '">' + satirIci(baslik[2]) + "</h" + seviye + ">");
      continue;
    }

    const madde = satir.match(/^(\s*)(?:([*+-])|(\d{1,9})[.)])\s+(.*)$/);
    if (madde) {
      paragrafKapat();
      const girinti = madde[1].replace(/\t/g, "    ").length;
      const tip = madde[3] !== undefined ? "ol" : "ul";
      while (listeler.length &&
             girinti < listeler[listeler.length - 1].girinti) {
        listeKapat();
      }
      const ust = listeler[listeler.length - 1];
      if (ust && girinti < ust.girinti + 2 && ust.tip === tip) {
        cikti.push("</li><li>");
      } else {
        if (ust && girinti < ust.girinti + 2) listeKapat();
        const baslangic = tip === "ol" && madde[3] !== "1"
          ? ' start="' + Number(madde[3]) + '"' : "";
        cikti.push("<" + tip + baslangic + "><li>");
        listeler.push({ tip, girinti });
      }
      cikti.push(satirIci(madde[4]));
      continue;
    }

    if (!satir.trim()) {
      paragrafKapat();
      continue;
    }

    if (listeler.length && /^\s+\S/.test(satir)) {
      cikti.push("<br>" + satirIci(satir.trim()));
      continue;
    }

    listeleriKapat();
    paragraf.push(satir);
  }

  if (kod !== null) {
    cikti.push("<pre><code>" + kod.join("\n") + "</code></pre>");
  }
  paragrafKapat();
  listeleriKapat();
  return cikti.join("");
}

function icerikYaz(b, metin) {
  b.dataset.ham = String(metin || "");
  let ic = b.querySelector(".icerik");
  if (!ic) {
    ic = document.createElement("div");
    ic.className = "icerik";
    b.appendChild(ic);
  }
  ic.innerHTML = b.dataset.rol === "user"
    ? basitBicimle(metin || "")
    : bicimle(metin || "");
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
  b.dataset.rol = role;

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
  yonlendir.disabled = true;

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
    handoffToken: "", toolPolicy: "auto",
    kesik: false, kesikNedeni: "",
    mola: false,
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

  // Mola özeti kullanıcının kararını bekler; adım çizimi onu silmez.
  if (!kayit.bitti && !kayit.mola) {
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

function yonlendirmeBaglamiOlustur(b) {
  const kayit = calismaKaydi(b);
  return {
    schema: "p2-handoff-v1",
    token: String(kayit.handoffToken || ""),
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
  kayit.baslik.textContent = kayit.kesik
    ? "Yanıt tamamlanmadan durdu"
    : (sayi ? sayi + " adım tamamlandı" : "Yanıt tamamlandı");
  kayit.sure.textContent = toplamSure;
  kayit.mevcut.hidden = true;
  kayit.ozet.hidden = !kayit.kesik;
  kayit.ozet.textContent = kayit.kesik
    ? "Sağlayıcı çıktı sınırında durdu; cevap metni değiştirilmedi."
    : "";
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

// Sunucu süresi dolmadan Başak mola verir; iş kendiliğinden sürmez, karar
// kullanıcıdadır. Yapılan adımların sonuçları imzalı devam kaydında kalır.
function calismaMolaVer(b) {
  const kayit = durumSaatleri.get(b);
  if (!kayit || kayit.bitti || kayit.mola) return;
  aktifAdimiTamamla(kayit);
  kayit.mola = true;
  if (kayit.zamanlayici) clearInterval(kayit.zamanlayici);
  kayit.zamanlayici = null;
  kayit.kart.classList.add("paused");
  const sure = sureMetni(Date.now() - kayit.baslangic);
  const sayi = kayit.adimlar.length;
  kayit.baslik.textContent = "Mola · " + sayi + " adım tamamlandı";
  kayit.sure.textContent = sure;
  kayit.mevcut.hidden = true;
  kayit.ozet.hidden = false;
  kayit.ozet.textContent =
    "Çalışma süresi " + sure + ". Bulunanlar saklandı; nasıl devam edelim?";
  if (kayit.durdur?.isConnected) kayit.durdur.remove();

  const devam = document.createElement("button");
  devam.type = "button";
  devam.className = "work-action work-continue";
  devam.textContent = "Devam et";

  const cevapla = document.createElement("button");
  cevapla.type = "button";
  cevapla.className = "work-action work-answer";
  cevapla.textContent = "Bulduklarınla cevap ver";

  kayit.yonlendir.parentNode.insertBefore(devam, kayit.yonlendir);
  kayit.yonlendir.parentNode.insertBefore(cevapla, kayit.yonlendir);
  kayit.yonlendir.disabled = false;
  kayit.yonlendir.hidden = false;

  const sec = (secenek) => {
    if (kayit.bitti) return;
    kayit.bitti = true;
    devam.remove();
    cevapla.remove();
    if (kayit.yonlendir?.isConnected) kayit.yonlendir.remove();
    if (kayit.yonForm?.isConnected) kayit.yonForm.remove();
    kayit.ozet.textContent = sayi + " adım tamamlandı · seçiminle sürüyor.";
    // Devam kaydı tıklama anında okunur: en son imzalı durum taşınır.
    molaSonrasiGonder({ ...secenek, yonlendirmeBaglami: yonlendirmeBaglamiOlustur(b) });
  };

  devam.addEventListener("click", () => sec({
    text: "Kaldığın yerden devam et.",
    gorunenMetin: "Devam et",
  }));
  cevapla.addEventListener("click", () => sec({
    text: "Şimdiye kadar bulduklarınla cevap ver.",
    gorunenMetin: "Bulduklarınla cevap ver",
  }));
  kayit.yonlendirIstegi = (yon) => sec({
    text: yon,
    gorunenMetin: "Yönlendirme: " + yon,
  });

  kayit.canli.textContent = kayit.ozet.textContent;
  adimlariCiz(kayit);
}

function molaSonrasiGonder(secenek) {
  // Mola olayını getiren istek kapanana kadar bekle; sonra yeni istek aç.
  const dene = () => {
    if (gonderiliyor) { setTimeout(dene, 150); return; }
    send(secenek);
  };
  dene();
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

  if (typeof o.handoff_token === "string" && o.handoff_token) {
    let handoffBalonu = balonlar.get(no);
    if (!handoffBalonu) {
      handoffBalonu = bubble("assistant", "");
      balonlar.set(no, handoffBalonu);
    }
    const handoffKaydi = calismaKaydi(handoffBalonu);
    handoffKaydi.handoffToken = o.handoff_token;
    handoffKaydi.yonlendir.disabled = false;
  }

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

  if (o.tur === "checkpoint") {
    const b = balonlar.get(no);
    if (b) calismaMolaVer(b);
    return false;
  }

  if (o.tur === "truncated") {
    const b = balonlar.get(no);
    if (b) {
      const kayit = calismaKaydi(b);
      kayit.kesik = true;
      kayit.kesikNedeni = String(o.reason || "limit");
      kayit.canli.textContent = "Yanıt tamamlanmadan durdu";
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

const KESILME_SURE_ESIGI_MS = 290 * 1000;

async function canliYanitiOku(r, baslangicBalonu) {
  if (!r.body || typeof r.body.getReader !== "function") {
    throw new Error("Tarayıcı canlı yanıt akışını desteklemiyor.");
  }

  const okuyucu = r.body.getReader();
  const cozumleyici = new TextDecoder();
  const baslangic = Date.now();
  let tampon = "";
  let sonuc = { ok: false, cevap: "", kaynak: "", hata: "" };

  // Sunucu (vercel.json maxDuration: 300 sn) isi yarida durdurunca akis
  // bitir/error gelmeden kapanir. Kullaniciya gercek sebebi soyle.
  const kesilmeHatasi = () => new Error(
    Date.now() - baslangic >= KESILME_SURE_ESIGI_MS
      ? "Başak 5 dakikalık çalışma süresini doldurdu; sunucu işi durdurdu, cevap tamamlanamadı."
      : "Başak yanıtı tamamlanmadan bağlantı kapandı."
  );

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
    } else if (o.tur === "checkpoint") {
      sonuc = { ok: false, mola: true, cevap: "", kaynak: "", hata: "" };
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
      if (sonuc.ok || sonuc.hata || sonuc.mola) break;
      // Durdur/Yönlendir kasıtlı keser; o yol kendi davranışını korur.
      if (e && e.name === "AbortError") throw e;
      throw kesilmeHatasi();
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
  if (tampon.trim()) {
    // Satir sonu gelmeden kapanan son parca yarim kalmis olabilir; bu
    // "gecersiz veri" degil, kesilmedir. Tam satirsa normal islenir.
    let tamSatir = true;
    try { JSON.parse(tampon); } catch { tamSatir = false; }
    if (tamSatir) await satiriIsle(tampon);
  }

  if (!sonuc.ok && !sonuc.hata && !sonuc.mola) {
    throw kesilmeHatasi();
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
  const toolPolicy = ["auto", "required", "none"].includes(secenek.toolPolicy)
    ? secenek.toolPolicy
    : "auto";
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
  calisma.toolPolicy = toolPolicy;
  calisma.yonlendir.hidden = !!gorsel;
  calisma.yonlendirIstegi = (yon) => {
    if (!gonderiliyor || calisma.bitti) return;
    yonlendirmeBekliyor = {
      yon,
      anaMetin: gonderilecekMetin,
      baglam: yonlendirmeBaglamiOlustur(bekleyenBalon),
      toolPolicy,
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
        tool_policy:toolPolicy,
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
      if (d.olaylar.some((o) => o && o.tur === "checkpoint")) {
        onizlemeTemizle();
        return;
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
          toolPolicy: devam.toolPolicy || "auto",
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
