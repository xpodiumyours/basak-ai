/* ============ Başak — ön yüz mantığı (js_api köprüsü) ============ */

const $ = (id) => document.getElementById(id);
let sesZamanlayici = null;
const state = { busy: false, ready: false, model: null, dinliyor: false, ttsOn: false };
/* Son gonderilen mesaj. Hata/zaman asimi sonrasi "tekrar dene" bunu
   kullanir — eskiden metin input'tan silindigi icin elle yeniden
   yazmaktan baska yol yoktu. */
let sonGonderilen = "";

window.addEventListener("error", function (ev) {
  const ds = document.getElementById("durumSatiri");
  if (ds && ds.textContent.indexOf("hatası") === -1) {
    ds.textContent = "js hatası: " + ev.message;
  }
});

/* Son cevabin kaynagini Ayarlar'daki durum satirina yazar.
   P3: secim motorunun gerekcesi de gorunur ("Nemotron · kod işi" gibi). */
function brainKaynakEtiketi(kaynak) {
  const el = $("brainSource");
  if (!el) return;
  const s = String(kaynak || "");
  let ad = null;
  if (s.startsWith("groq")) ad = "GROQ";
  else if (s.startsWith("gemini")) ad = "GEMINI";
  else if (s.startsWith("glm")) ad = "GLM";
  else if (s.startsWith("deepseek")) ad = "DEEPSEEK";
  else if (s.startsWith("qwen")) ad = "QWEN";
  else if (s.startsWith("nvidia")) ad = "NEMOTRON";
  else if (s.startsWith("openrouter")) ad = "OPENROUTER";
  else if (s.startsWith("genel")) ad = "ÖZEL";
  else if (s.startsWith("yerel")) ad = "YEREL";

  const parcalar = s.split("·");
  if (ad && parcalar.length > 1 && parcalar[1].trim()) {
    ad += " · " + parcalar[1].trim();
  }
  el.textContent = ad || "—";
}

/* ---------------- API köprüsü ---------------- */
const api = () => window.pywebview.api;

/* 3D Orb: head.js'deki Jarvis tarzı hologram */
const Orb = window.BasakHead || { init() {}, setState() {}, durum() {}, ses() {} };

/* ---------------- Metin bicimleme ---------------- */
/* Kucuk markdown: kod blogu, satir ici kod, kalin. Disaridan kutuphane
   yuklenmiyor — uygulama cevrimdisi de acilmali, CDN'e bagimli olamaz.
   Model ciktisi guvenilmez metindir: once HTML kacisi yapilir, bicimleme
   ANCAK ondan sonra uygulanir. */
function mdKacis(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
/* Olcu rozetleri: badge::B:: → <span class="olcu-rozet bilmiyorum">B</span> */
function badge_cevir(s) {
  var h = { O: 'olcum', A: 'alinti', C: 'cikarim', B: 'bilmiyorum',
            Y: 'yanit' };
  var l = { O: 'Ö', A: 'A', C: 'Ç', B: 'B', Y: 'Y' };
  return s.replace(/badge::([OACBY])::/g, function(_, t) {
    return '<span class="olcu-rozet ' + (h[t] || '') + '">' + (l[t] || t) + '</span>';
  });
}

function mdRender(metin) {
  const parcalar = String(metin == null ? "" : metin).split("```");
  let html = "";
  for (let i = 0; i < parcalar.length; i++) {
    if (i % 2 === 1) {
      const satirlar = parcalar[i].split("\n");
      const bas = (satirlar[0] || "").trim();
      const dil = /^[a-z0-9+#._-]{1,15}$/i.test(bas) ? satirlar.shift().trim() : "";
      const kod = satirlar.join("\n").replace(/^\n+|\n+$/g, "");
      html += '<div class="kod-blok"><div class="kod-bas">'
        + '<span class="kod-dil">' + mdKacis(dil || "kod") + "</span>"
        + '<button class="kod-kopya" type="button">kopyala</button></div>'
        + "<pre><code>" + mdKacis(kod) + "</code></pre></div>";
    } else {
      html += mdBloklaraAyr(parcalar[i]);
    }
  }
  return html;
}

function mdBloklaraAyr(metin) {
  var satirlar = metin.split("\n");
  var html = "";
  var i = 0;
  while (i < satirlar.length) {
    var satir = satirlar[i];
    var bos = satir.trim();

    // Bos satir
    if (bos === "") { i++; continue; }

    // Tablo tespiti
    if (bos.indexOf("|") !== -1 && i + 1 < satirlar.length &&
        /^\s*\|?\s*[-:]+[-| :]*$/.test(satirlar[i + 1])) {
      var tabloSatirlari = [];
      while (i < satirlar.length && satirlar[i].trim().indexOf("|") !== -1) {
        tabloSatirlari.push(satirlar[i]); i++;
      }
      html += mdTabloCevir(tabloSatirlari);
      continue;
    }

    // Baslik
    if (/^#{1,6}\s+/.test(bos)) {
      var seviye = bos.match(/^(#{1,6})/)[1].length;
      var baslikMetni = bos.replace(/^#{1,6}\s+/, "");
      var cls = seviye <= 3 ? "md-h3" : "md-h4";
      html += "<div class=" + cls + ">" + mdSatirIci(baslikMetni) + "</div>";
      i++; continue;
    }

    // Ayraç
    if (/^\s*---+\s*$/.test(bos)) {
      html += "<hr>"; i++; continue;
    }

    // Madde listesi
    if (/^\s*[-*]\s+/.test(bos)) {
      html += "<ul>";
      while (i < satirlar.length && /^\s*[-*]\s+/.test(satirlar[i])) {
        html += "<li>" + mdSatirIci(satirlar[i].replace(/^\s*[-*]\s+/, "")) + "</li>";
        i++;
      }
      html += "</ul>"; continue;
    }

    // Numarali liste
    if (/^\s*\d+\.\s+/.test(bos)) {
      html += "<ol>";
      while (i < satirlar.length && /^\s*\d+\.\s+/.test(satirlar[i])) {
        html += "<li>" + mdSatirIci(satirlar[i].replace(/^\s*\d+\.\s+/, "")) + "</li>";
        i++;
      }
      html += "</ol>"; continue;
    }

    // Normal paragraf
    html += "<p>" + mdSatirIci(bos) + "</p>";
    i++;
  }
  return html;
}

function mdTabloCevir(satirlar) {
  var baslik = satirlar[0].split("|").map(function(c) { return c.trim(); }).filter(Boolean);
  var html = "<table><thead><tr>";
  baslik.forEach(function(h) { html += "<th>" + mdSatirIci(h) + "</th>"; });
  html += "</tr></thead><tbody>";
  for (var r = 2; r < satirlar.length; r++) {
    var hucreler = satirlar[r].split("|").map(function(c) { return c.trim(); }).filter(Boolean);
    html += "<tr>";
    hucreler.forEach(function(h) { html += "<td>" + mdSatirIci(h) + "</td>"; });
    html += "</tr>";
  }
  html += "</tbody></table>";
  return html;
}

function mdSatirIci(metin) {
  var s = mdKacis(metin);
  s = s.replace(/`([^`\n]+)`/g, '<code class="satir-kod">$1</code>');
  s = s.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  s = badge_cevir(s);
  // Durum isaretleri
  s = s.replace(/\[OK\]/g, '<span class="durum-ok">[OK]</span>');
  s = s.replace(/\[HATA\]/g, '<span class="durum-hata">[HATA]</span>');
  s = s.replace(/\[UYARI\]/g, '<span class="durum-uyari">[UYARI]</span>');
  return s;
}

/* Panoya kopyalama. pywebview'da Clipboard API her zaman acik degil —
   basarisiz olursa gizli textarea + execCommand'a duser. */
function kopyalaGeriBildirim(btn) {
  const eski = btn.textContent;
  btn.textContent = "kopyalandı";
  btn.classList.add("ok");
  setTimeout(() => { btn.textContent = eski; btn.classList.remove("ok"); }, 1400);
}
function kopyala(metin, btn) {
  const bitti = () => kopyalaGeriBildirim(btn);
  const yedek = () => {
    const ta = document.createElement("textarea");
    ta.value = metin;
    ta.style.position = "fixed"; ta.style.opacity = "0"; ta.style.pointerEvents = "none";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); bitti(); } catch (e) {}
    ta.remove();
  };
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(metin).then(bitti, yedek);
    } else { yedek(); }
  } catch (e) { yedek(); }
}

/* ---------------- Sohbet ---------------- */
const Chat = (function () {
  const scroll = $("chatScroll"), list = $("messages"), empty = $("chatEmpty");

  /* Kullanici yukari cikip eski mesaj okuyorsa yeni mesaj onu asagi
     ZORLAMAMALI. Olcum mesaj eklenmeden ONCE yapilir; sonra olculurse
     scrollHeight zaten buyumus olur ve hep "dipte degil" cikar. */
  function dipteMi() {
    return scroll.scrollHeight - scroll.scrollTop - scroll.clientHeight < 80;
  }
  function dibeKaydir() { scroll.scrollTop = scroll.scrollHeight; }

  function saatEtiketi() {
    return new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
  }

  function add(role, text) {
    empty.style.display = "none";
    document.body.classList.add("goster-mesajlar");
    const dipte = dipteMi();
    const div = document.createElement("div");
    div.className = "msg " + role;
    div.innerHTML = '<div class="msg-avatar">' + (role === "basak" ? "B" : "S")
      + '</div><div class="msg-body"><div class="msg-name">'
    div.innerHTML = '<div class="msg-avatar">' + (role === "basak" ? "BAŞAK" : "SEN")
      + '<span class="msg-saat">' + saatEtiketi() + "</span>"
      + '<button class="msg-kopya" type="button" title="Mesajı kopyala">kopyala</button>'
      + '</div><div class="msg-bubble"></div></div>';
    div.querySelector(".msg-bubble").innerHTML = mdRender(text);
    // Kopyalama bicimlenmis HTML'i degil ham metni vermeli.
    div._ham = String(text == null ? "" : text);
    list.appendChild(div);
    if (dipte) dibeKaydir();
    return div;
  }

  /* Sistem satiri: baglanti hatasi, zaman asimi gibi UYGULAMA olaylari.
     Basak'in soyledigi bir cumle degil — sohbet balonu gibi gorunmemeli,
     yoksa "beyin bunu mu dedi" karisikligi olur. */
  function sistem(metin, tekrarVar) {
    empty.style.display = "none";
    document.body.classList.add("goster-mesajlar");
    const dipte = dipteMi();
    const div = document.createElement("div");
    div.className = "msg sistem";
    div.innerHTML = '<div class="sistem-govde"><span class="sistem-ikon">!</span>'
      + '<span class="sistem-metin"></span></div>';
    div.querySelector(".sistem-metin").textContent = metin;
    if (tekrarVar && sonGonderilen) {
      const b = document.createElement("button");
      b.className = "sistem-tekrar";
      b.type = "button";
      b.textContent = "tekrar dene";
      b.addEventListener("click", () => { div.remove(); tekrarGonder(); });
      div.querySelector(".sistem-govde").appendChild(b);
    }
    list.appendChild(div);
    if (dipte) dibeKaydir();
    return div;
  }

  // Kopyala dugmeleri tek dinleyiciyle: mesajlar sonradan eklendigi icin
  // her birine ayri dinleyici baglamak sizinti kaynagi olurdu.
  list.addEventListener("click", (e) => {
    const mesajBtn = e.target.closest(".msg-kopya");
    if (mesajBtn) {
      const msg = mesajBtn.closest(".msg");
      kopyala(msg._ham || msg.querySelector(".msg-bubble").textContent, mesajBtn);
      return;
    }
    const kodBtn = e.target.closest(".kod-kopya");
    if (kodBtn) {
      const kod = kodBtn.closest(".kod-blok").querySelector("code");
      kopyala(kod.textContent, kodBtn);
    }
  });
  function thinking() {
    empty.style.display = "none";
    document.body.classList.add("goster-mesajlar");
    const div = document.createElement("div");
    div.className = "msg basak thinking";
    // msg-sure: gecen saniye. Cevap tek parca geldigi icin (hicbir
    // saglayicida akis yok) uc nokta disinda hicbir ilerleme isareti
    // yoktu; olculen en yavas model 27.9s (kimi-k3) ve o sure boyunca
    // ekran donmus gibi duruyordu.
    div.innerHTML = '<div class="msg-avatar">B</div><div class="msg-body">'
      + '<div class="msg-name">BAŞAK<span class="msg-sure"></span></div>'
      + '<div class="msg-bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div></div>';
    list.appendChild(div);
    scroll.scrollTop = scroll.scrollHeight;
    // Jarvis hologramı "düşünüyor" moduna geç
    if (Orb && Orb.durum) Orb.durum("dusunuyor");
    return div;
  }
  function remove(el) { el.remove(); }
  return { add, sistem, thinking, remove, dibeKaydir };
})();

/* ---------------- Mesgul kilidi ---------------- */
/* thinking() gonder dugmesini kilitler; aciligi tek yer reply()/error()
   idi. Python tarafi cokup hic donmezse kilit sonsuza kadar kapali
   kaliyordu — tek cikis uygulamayi kapatip acmakti. Artik ust sinir var. */
let busyTimer = null;
const YANIT_UST_SINIR_MS = 90000;   // olculen en yavas model 27.9s (kimi-k3)

/* ---------------- Bekleme sayaci ---------------- */
/* Akis yok: cevap tek parca geliyor, yol boyunca hicbir isaret cikmiyor.
   Tam akis 10 saglayicinin hepsini + arac cagirma mantigini degistirmek
   demek. Sayac o isi yapmaz ama asil sikayeti ("dondu mu?") cozer:
   bekleme gorunur olur. */
let sureTimer = null;
function sureBaslat() {
  const bas = Date.now();
  clearInterval(sureTimer);
  const yaz = () => {
    const el = document.querySelector(".msg.basak.thinking .msg-sure");
    if (!el) return;
    const sn = Math.round((Date.now() - bas) / 1000);
    if (sn < 2) { el.textContent = ""; return; }
    // 20 sn'den sonra: bekleyen kisi "takildi" diye dusunmesin. Bu sure
    // olculen en yavas modelin (27.9s) altinda secildi ki gercekten
    // yavas modelde uyari cevaptan ONCE ciksin.
    el.textContent = sn >= 20 ? sn + " sn · yavaş model, hâlâ bekliyor" : sn + " sn";
    el.classList.toggle("uzun", sn >= 20);
  };
  yaz();
  sureTimer = setInterval(yaz, 1000);
}
function sureDurdur() {
  clearInterval(sureTimer);
  sureTimer = null;
}

function kilidiKapat() {
  state.busy = true;
  $("btnSend").disabled = true;
  sureBaslat();
  clearTimeout(busyTimer);
  busyTimer = setTimeout(() => {
    if (!state.busy) return;
    kilidiAc();
    const el = document.querySelector(".msg.basak.thinking");
    if (el) el.remove();
    Chat.sistem("Yanıt gelmedi (90 sn içinde). Beyin takılmış olabilir.", true);
    setStatus("err", "hata");
    setStatus("err", "yanıt gelmedi");
  }, YANIT_UST_SINIR_MS);
}
function kilidiAc() {
  clearTimeout(busyTimer);
  busyTimer = null;
  sureDurdur();
  state.busy = false;
  $("btnSend").disabled = false;
}

/* ---------------- Durum ---------------- */
function setStatus(kind, label) {
  const dot = $("brainDot");
  if (dot) dot.className = "logo-dot" + (kind === "ok" ? " ok" : kind === "err" ? " err" : kind === "busy" ? " busy" : "");
  const lbl = $("brainLabel");
  if (lbl) lbl.textContent = label;
  // Header status'a da yazar — Jarvis tarzı prefix
  const hs = $("sysStatus");
  if (hs) {
    if (kind === "ok") {
      // Model bilgisini de göster
      hs.textContent = "◆ " + label;
    } else if (kind === "err") hs.textContent = "▲ SİSTEM HATASI";
    else if (kind === "busy") hs.textContent = "◆ İ�?LEM DEVAM EDİYOR";
    else hs.textContent = "◆ " + label;
  }
  // Orb durumunu dagüncelle
  const orbMap = { ok: "bekliyor", err: "hata", busy: "dusunuyor" };
  if (Orb && Orb.durum && orbMap[kind]) Orb.durum(orbMap[kind]);
}
function setOrb(s) {
  const labels = {
    bekliyor: "BAŞAK BEKLEME MODU",
    dusunuyor: "BAŞAK DÜŞÜNÜYOR",
    cevapliyor: "BAŞAK KONUŞUYOR",
    arac: "BAŞAK ARAÇ ÇALIŞTIRIYOR",
    hata: "HATA — BİR SORUN VAR",
    dinliyor: "BAŞAK DİNLİYOR",
    algiliyor: "BA�?AK ALGILIYOR",
    onay: "ONAY BEKLENİYOR"
  };
  // Sadece orbLabel'i=güncelle, durumSatiri'ni bozma
  const orbLabel = $("orbLabel");
  if (orbLabel) orbLabel.textContent = labels[s] || "BAŞAK";
  if (Orb && Orb.durum) Orb.durum(s);
}

/* ---------------- Python'dan gelen geri çağrılar ---------------- */
window.BasakUI = {
  // E-3: tools/zamanlayici.py bu karti SORULMADAN gonderir (2 saatte bir,
  // 10:00-20:00 arasi). Python tarafi hazirdi, ekrana basacak taraf eksikti:
  // evaluate_js tanimsiz fonksiyona dusuyor, hata basak_app'teki try/except'e
  // takiliyor ve kart sessizce kayboluyordu.
  kartGoster(metin, deneme) {
    // Kullanici o an cevap bekliyorsa araya girme. Bir sure bekler, sonra
    // vazgecer — zamanlayici.py'deki "cevaplanmazsa dirdir etmez" kurali
    // burada da gecerli; bekleyen kartlar birikip toplu dokulmemeli.
    const n = deneme || 0;
    if (state.busy) {
      if (n < 6) setTimeout(() => window.BasakUI.kartGoster(metin, n + 1), 5000);
      return;
    }
    const div = Chat.add("basak", metin);
    div.classList.add("kart");
    setStatus("ok", "Başak'tan kart");
    setOrb("cevapliyor");
    setTimeout(() => setOrb("bekliyor"), 2200);
  },
  thinking() {
    Chat.thinking();
    kilidiKapat();
    setStatus("busy", "BAŞAK DÜŞÜNÜYOR...");
    setOrb("dusunuyor");
  },
  toolStatus(text) {
    const el = document.querySelector(".msg.basak.thinking .msg-bubble");
    if (el) el.textContent = text;
    setStatus("busy", text);
    setOrb("arac");
  },
  /* Akan cevap (2026-09-10): parca() ham metni biriktirir, bitir()
     tam metni bicimleyip kilidi acar. Arac isteyen sorular eski
     reply() yolundan gelir — bu ikisi karismaz. */
  _akisEl: null,
  _akisMetin: "",
  parca(parca) {
    let el = window.BasakUI._akisEl;
    if (!el || !document.contains(el)) {
      const _t = document.querySelector(".msg.basak.thinking"); if (_t) _t.remove();
      el = Chat.add("basak", "");
      window.BasakUI._akisEl = el;
      window.BasakUI._akisMetin = "";
      setOrb("cevapliyor");
    }
    window.BasakUI._akisMetin += String(parca == null ? "" : parca);
    el.querySelector(".msg-bubble").textContent = window.BasakUI._akisMetin;
    Chat.dibeKaydir();
  },
  bitir(tamMetin, modelInfo) {
    const el = window.BasakUI._akisEl;
    window.BasakUI._akisEl = null;
    window.BasakUI._akisMetin = "";
    const _t = document.querySelector(".msg.basak.thinking"); if (_t) _t.remove();
    if (el && document.contains(el)) el.remove();
    window.BasakUI.reply(tamMetin, modelInfo);
  },
  reply(text, modelInfo) {
    const _t = document.querySelector(".msg.basak.thinking"); if (_t) _t.remove();
    Chat.add("basak", text);
    brainKaynakEtiketi(modelInfo);
    kilidiAc();
    setOrb("cevapliyor");
    if (!state.ttsOn) setTimeout(() => setOrb("bekliyor"), 2200);
    const ml = modelInfo || state.model || "yerel beyin";
    setStatus("ok", ml + " HAZIR");
    $("input").focus();
    try { oturumlariYukle(); } catch (e) {}
  },
  error(msg) {
    const _t = document.querySelector(".msg.basak.thinking"); if (_t) _t.remove();
    // Hata Basak'in AGZINDAN cikmis gibi gorunmemeli: eskiden sohbet
    // balonuna "Uzgunum, bir sorun var: ..." diye ekleniyordu ve baglanti
    // hatasi ile gercek cevap ayni yerde duruyordu.
    Chat.sistem("▲ BAĞLANTI SORUNU: " + msg, true);
    kilidiAc();
    setStatus("err", "BEYNİN YANIT VERMEDİ");
    setOrb("hata");
  },
  listening(on) {
    state.dinliyor = on;
    $("btnMic").classList.toggle("active", on);
    $("btnMic").disabled = on;
    setOrb(on ? "dinliyor" : "bekliyor");
  },
  sttResult(text, speaker) {
    const input = $("input");
    if (speaker && speaker.isim && speaker.isim !== "Bilinmeyen") {
      input.value = text + " [" + speaker.isim + "]";
    } else {
      input.value = text;
    }
    send();
  },
  ses(seviye) {
    try {
      // Jarvis hologramı ses seviyesine tepki verir
      if (Orb && Orb.ses) Orb.ses(seviye);
      if (seviye > 2) {
        setOrb("cevapliyor");
        clearTimeout(sesZamanlayici);
        sesZamanlayici = setTimeout(() => setOrb("bekliyor"), 1200);
      }
    } catch (e) {}
  },

  // ONAY SİSTEMİ: Hassas araçlar için onay isteği gösterir
  approval(data) {
    const toolNames = {
      'write_file_tool': 'Dosya yazma/oluşturma',
      'deftere_kaydet': 'Deftere kayıt',
      'save_note': 'Not kaydetme',
      'complete_task': 'Görev tamamlama',
      'ac_uygulama': 'Uygulama açma',
    };
    const toolName = toolNames[data.tool] || data.tool;
    const argsStr = JSON.stringify(data.args, null, 2);

    const div = Chat.add('basak',
      `⚠ ONAY GEREKLİ\n\n` +
      `▶ İ�?LEM: ${toolName}\n` +
      `▶ DETAY:\n\`${argsStr}\`\n\n` +
      `Bu işlemi yapmamı istiyor musun?`
    );

    // Onay butonları ekle
    const btnDiv = document.createElement('div');
    btnDiv.className = 'onay-butonlari';
    btnDiv.innerHTML = `
      <button class="onay-btn onay-kabul" onclick="BasakUI.onayGonder('${data.call_id}', true)">✓ EVET, YAP</button>
      <button class="onay-btn onay-red" onclick="BasakUI.onayGonder('${data.call_id}', false)">✗ HAYIR, İPTAL</button>
    `;
    div.appendChild(btnDiv);

    setOrb('onay');
    setStatus('busy', 'ONAY BEKLENİYOR...');
  },

onayGonder(callId, kabul) {
    // Butonları devre bırak
    const btns = document.querySelectorAll('.onay-btn');
    btns.forEach(b => b.disabled = true);

    // Onayı Python'a gönder
    pywebview.api.onay_ver(callId, kabul);

    if (kabul) {
      setStatus('ok', 'ONAY VERİLDİ');
    } else {
      setStatus('ok', 'İ�?LEM İPTAL EDİLDİ');
    }
    setOrb('bekliyor');
  }
}; // 2026-09-09: BasakUI burada kapanir. Alttaki "Görünümler" ve
   // sonraki bölümler normal kod — listenin içinde kalmıştı, bu
   // yüzden tüm ekran kodu çalışmıyordu (açılışta takılma sebebi).

/* ---------------- Görünümler ---------------- */
  document.querySelectorAll(".sys-nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".sys-nav-item").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const view = btn.dataset.view;
      document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
      $("view-" + view).classList.add("active");
      if (view === "kutuphane") loadKnowledge();
    });
  });

async function loadKnowledge() {
  const list = $("fileList");
  if (!list) return;
  const files = await api().knowledge();
  if (!files || !files.length) {
    list.innerHTML = '<li><span class="file-ico">[D]</span> <span class="muted">Henüz dosya yok — Başak\\knowledge klasörüne ekle</span></li>';
    return;
  }
  // Dosya adlari innerHTML'e dogrudan giriyordu: yerel veri oldugu icin
  // risk dusuktu ama "<" iceren bir ad listeyi bozardi.
  list.innerHTML = files
    .map((f) => '<li><span class="file-ico">[D]</span> ' + mdKacis(f) + "</li>")
    .join("");
}

/* ---------------- Gönder ---------------- */
function send() {
  const input = $("input");
  const text = input.value.trim();
  if (!text || state.busy) return;
  if (!state.ready || !window.pywebview || !window.pywebview.api) {
    setStatus("err", "BAŞAK HENÜZ HAZIRLANIYOR, BİRKAÇ SANİYE BEKLE");
    return;
  }
  sonGonderilen = text;
  input.value = "";
  input.style.height = "auto";
  Chat.add("user", text);
  Chat.dibeKaydir();   // kendi mesajina her zaman in
  api().mesaj(text);
}

function tekrarGonder() {
  if (!sonGonderilen || state.busy) return;
  Chat.add("user", sonGonderilen);
  Chat.dibeKaydir();
  api().mesaj(sonGonderilen);
}

/* ---------------- Olaylar ---------------- */
$("btnSend").addEventListener("click", send);
/* Hazir komut cipleri: soruyu kutuya yazip gonderir */
document.querySelectorAll(".chip").forEach((c) => {
  c.addEventListener("click", () => {
    if (state.busy) return;
    $("input").value = c.dataset.soru || c.textContent;
    send();
  });
});

/* ---------------- Eski sohbetler (2026-09-10) ---------------- */
function tarihKisa(ts) {
  try {
    const d = new Date(ts * 1000);
    return d.toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit" })
      + " " + d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
  } catch (e) { return ""; }
}
async function oturumlariYukle() {
  try {
    const liste = await api().oturumlar();
    const kutu = $("oturumListe");
    if (!kutu) return;
    kutu.innerHTML = "";
    (liste || []).forEach((o) => {
      const b = document.createElement("button");
      b.className = "oturum-oge";
      b.type = "button";
      b.textContent = o.baslik || "Sohbet";
      const k = document.createElement("small");
      k.textContent = (o.adet || 0) + " ileti · " + tarihKisa(o.guncellendi);
      b.appendChild(k);
      b.addEventListener("click", () => oturumAc(o.id));
      kutu.appendChild(b);
    });
  } catch (e) {}
}
async function oturumAc(id) {
  if (state.busy) return;
  try {
    const r = await api().oturum_ac(id);
    if (r && r.ok) {
      $("messages").innerHTML = "";
      (r.mesajlar || []).forEach((m) => {
        Chat.add(m.role === "assistant" ? "basak" : "user", m.content || "");
      });
      document.body.classList.remove("oturum-acik");
      Chat.dibeKaydir();
    }
  } catch (e) {}
}
async function yeniSohbet() {
  if (state.busy) return;
  try { await api().yeni_sohbet(); } catch (e) {}
  $("messages").innerHTML = "";
  $("chatEmpty").style.display = "flex";
  document.body.classList.remove("goster-mesajlar");
  document.body.classList.remove("oturum-acik");
  oturumlariYukle();
}
$("btnOturum").addEventListener("click", () => {
  document.body.classList.toggle("oturum-acik");
  if (document.body.classList.contains("oturum-acik")) oturumlariYukle();
});
$("btnYeni").addEventListener("click", yeniSohbet);
$("btnMic").addEventListener("click", () => { if (!state.dinliyor) api().dinle(); });
$("btnTts").addEventListener("click", () => {
  state.ttsOn = !state.ttsOn;
  api().set_tts(state.ttsOn);
  $("btnTts").classList.toggle("active", state.ttsOn);
});
/* Hafizayi temizleme geri alinamaz, eskiden tek tiklaydi. Iki asamali
   onay: ikinci tik 4 saniye icinde gelmezse iptal olur. confirm() yerine
   bu desen secildi — pywebview'da yerel diyalog her zaman guvenilir
   behave etmiyor ve pencereyi kilitleyebiliyor. */
let temizleOnayi = null;
async function hafizaTemizle(btn) {
  if (temizleOnayi !== btn) {
    if (temizleOnayi) temizleOnayi.classList.remove("onay-bekliyor");
    temizleOnayi = btn;
    btn.classList.add("onay-bekliyor");
    setStatus("busy", "HAFIZAYI SİMEK İÇİN TEKRAR BAS");
    clearTimeout(hafizaTemizle._t);
    hafizaTemizle._t = setTimeout(() => {
      if (temizleOnayi) temizleOnayi.classList.remove("onay-bekliyor");
      temizleOnayi = null;
      setStatus("ok", (state.model || "hazır") + "");
    }, 4000);
    return;
  }
  clearTimeout(hafizaTemizle._t);
  btn.classList.remove("onay-bekliyor");
  temizleOnayi = null;
  /* 2026-08-24: clear() artik episodic anilari da unutturuyor (gecmis.json
     + basak.db episodic). Not/defter indeksleri bilerek KALIR. Mesaj
     gercegi soylesin: kac ani unutuldu. */
  let r = null;
  try {
    r = await api().clear();
  } catch (e) {
    setStatus("error", "temizleme hatası: " + e);
    return;
  }
  $("messages").innerHTML = "";
  $("chatEmpty").style.display = "block";
  sonGonderilen = "";
  const unutulan = (r && typeof r.unutulan_ani === "number") ? r.unutulan_ani : null;
  setStatus("ok", unutulan === null
    ? "SOHBET TEMİZLENDİ"
    : "SOHBET TEMİZLENDİ, " + unutulan + " ANI UNUTULDU");
}
$("btnClear").addEventListener("click", (e) => hafizaTemizle(e.currentTarget));
const bc2 = $("btnClear2"); if (bc2) bc2.addEventListener("click", (e) => hafizaTemizle(e.currentTarget));
$("btnClose").addEventListener("click", () => api().quit());
const bm = $("btnMesajlar"); if (bm) bm.addEventListener("click", () => {
  document.body.classList.toggle("goster-mesajlar");
});
const bk = $("btnKey"); if (bk) bk.addEventListener("click", async () => {
  const gk = $("groqKey"); const key = gk ? gk.value.trim() : '';
  const r = await api().set_key(key);
  if (r && r.cloud) {
    setStatus("ok", (state.model || "yerel beyin") + " + GROQ HAZIR");
    $("btnKey").textContent = "KAYDEDİLDİ";
  } else {
    $("btnKey").textContent = "ANAHTAR GEÇERSİZ";
  }
});

$("input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
$("input").addEventListener("input", () => {
  const el = $("input");
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 130) + "px";
});

/* ---------------- Açılış ---------------- */
let booted = false;
async function boot() {
  if (booted) return;
  booted = true;
  // Boot ekranını gizle, ana uygulamayı göster
  const bootEl = document.getElementById("bootScreen");
  if (bootEl) bootEl.classList.add("hidden");
  document.body.classList.add("sinema");
  // Jarvis hologramı başlat
  if (Orb && Orb.init) Orb.init();
  try {
    const status = await api().boot();
    if (status && status.ok) {
      state.ready = true;
      $("btnSend").disabled = false;
      $("btnMic").disabled = false;
      state.model = status.model;
      state.ttsOn = !!status.tts_on;
      setStatus("ok", (status.cloud ? "BULUT " + (status.model || "") + " HAZIR" : (status.model || "YEREL BEYİN") + " HAZIR"));
      // Token durumu gösterimi
      if (status.token_durumu) {
        const tl = $("tokenLabel");
        const ts = $("tokenStatus");
        if (tl) tl.textContent = "token: " + status.token_durumu;
        if (ts) ts.style.display = "block";
      }
      const sel = $("modelSelect");
      if (status.models && status.models.length) {
        sel.innerHTML = status.models
          .map((m) => "<option>" + mdKacis(m) + "</option>").join("");
        sel.value = status.model || status.models[0];
        sel.onchange = () => { state.model = sel.value; api().set_model(sel.value); setStatus("ok", sel.value + " HAZIR"); };
      }
      $("btnTts").classList.toggle("active", state.ttsOn);

      // Hatirlatmalari goster
      if (status.reminders && status.reminders.trim()) {
        Chat.add("basak", status.reminders);
      }
      try { oturumlariYukle(); } catch (e) {}
    } else {
      // 2026-09-09: mesaj gercegi soyler. Eskiden hep "OLLAMA KAPALI"
      // yaziyordu; oysa bulut biletleri de olmus olabilir. boot() ok=false
      // demek: yerel YOK ve bulut YOK. Dugmeler kilitli kalir cunku
      // gonderilecek beyin yok; hazir olunca acilir.
      setStatus("err", "HİÇBİR BEYİN YOK — Ollama kapalı, bulut biletleri de hazır değil");
      Chat.sistem("▲ Başak açılamadı: bilgisayardaki model (Ollama) kapalı ve internet biletleri de geçersiz. Önce internet bağlantını, sonra biletleri kontrol et.");
      setOrb("hata");
    }
  } catch (e) {
    setStatus("err", "BAĞLANTI SORUNU: " + String(e).slice(0, 120));
    setOrb("hata");
  } finally {
    // Her durumda boot screen gizli kalsın, ana uygulama görünsün
    if (bootEl) bootEl.classList.add("hidden");
    document.body.classList.add("sinema");
  }
  $("input").focus();
}

window.addEventListener("pywebviewready", boot);
setTimeout(() => { if (!booted && window.pywebview) boot(); }, 800);
setTimeout(() => { if (!booted) boot(); }, 2000);

