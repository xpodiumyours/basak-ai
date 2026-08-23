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
  if (s.startsWith("groq")) ad = "Groq";
  else if (s.startsWith("gemini")) ad = "Gemini";
  else if (s.startsWith("glm")) ad = "GLM";
  else if (s.startsWith("deepseek")) ad = "DeepSeek";
  else if (s.startsWith("qwen")) ad = "Qwen";
  else if (s.startsWith("nvidia")) ad = "Nemotron";
  else if (s.startsWith("openrouter")) ad = "OpenRouter";
  else if (s.startsWith("yerel")) ad = "Yerel";

  const parcalar = s.split("·");
  if (ad && parcalar.length > 1 && parcalar[1].trim()) {
    ad += " · " + parcalar[1].trim();
  }
  el.textContent = ad || "—";
}

/* ---------------- API köprüsü ---------------- */
const api = () => window.pywebview.api;

/* ---------------- 3D Orb (Three.js) ---------------- */
const Orb = (function () {
  let scene, camera, renderer, sphere, ring, particles, stateMesh = "bekliyor";
  const colors = {
    bekliyor: 0x8B5CF6, dusunuyor: 0x3B82F6, cevapliyor: 0x34D399,
    hata: 0xF87171, dinliyor: 0xF59E0B,
  };
  function init() {
    const wrap = $("orbWrap"), canvas = $("orbCanvas");
    if (!wrap || !window.THREE) return;   // sinema sahnesi yoksa eski orb da kurulmaz
    const w = wrap.clientWidth, h = wrap.clientHeight;
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    camera.position.z = 3.2;
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    sphere = new THREE.Mesh(
      new THREE.SphereGeometry(0.85, 48, 48),
      new THREE.MeshPhongMaterial({ color: colors.bekliyor, transparent: true, opacity: 0.92, emissive: colors.bekliyor, emissiveIntensity: 0.35, shininess: 40 })
    );
    scene.add(sphere);
    ring = new THREE.Mesh(
      new THREE.RingGeometry(1.15, 1.28, 64),
      new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.25, side: THREE.DoubleSide })
    );
    ring.rotation.x = Math.PI / 2.4;
    scene.add(ring);
    const g = new THREE.BufferGeometry();
    const N = 260, pos = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      const r = 1.5 + Math.random() * 1.4;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = r * Math.cos(phi);
    }
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    particles = new THREE.Points(g, new THREE.PointsMaterial({ color: 0x8B5CF6, size: 0.022, transparent: true, opacity: 0.8 }));
    scene.add(particles);
    const light = new THREE.DirectionalLight(0xffffff, 1.1);
    light.position.set(2, 3, 4);
    scene.add(light);
    scene.add(new THREE.AmbientLight(0x404060, 0.6));
    animate();
  }
  function animate() {
    requestAnimationFrame(animate);
    if (!sphere) return;
    const t = performance.now() / 1000;
    sphere.rotation.y = t * 0.55; sphere.rotation.x = Math.sin(t * 0.4) * 0.12;
    ring.rotation.y = t * 0.8; ring.rotation.z = t * 0.35;
    particles.rotation.y = t * 0.1; particles.rotation.x = Math.sin(t * 0.13) * 0.08;
    renderer.render(scene, camera);
  }
  function setState(s) {
    if (!sphere) return;
    const c = colors[s] || colors.bekliyor;
    const target = new THREE.Color(c);
    const tween = () => {
      sphere.material.color.lerp(target, 0.08);
      sphere.material.emissive.lerp(target, 0.08);
      const glow = (s === "dusunuyor" || s === "dinliyor") ? 0.28 + Math.sin(performance.now() / 180) * 0.2 : 0.35;
      sphere.material.emissiveIntensity = glow;
      // THREE.Color.distanceTo yok — manuel RGB karsilastirma
      const c1 = sphere.material.color, c2 = target;
      const dist = Math.abs(c1.r - c2.r) + Math.abs(c1.g - c2.g) + Math.abs(c1.b - c2.b);
      if (dist > 0.02) requestAnimationFrame(tween);
    };
    tween();
    particles.material.color.copy(target);
  }
  return { init, setState };
})();

/* ---------------- Metin bicimleme ---------------- */
/* Kucuk markdown: kod blogu, satir ici kod, kalin. Disaridan kutuphane
   yuklenmiyor — uygulama cevrimdisi de acilmali, CDN'e bagimli olamaz.
   Model ciktisi guvenilmez metindir: once HTML kacisi yapilir, bicimleme
   ANCAK ondan sonra uygulanir. */
function mdKacis(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function mdRender(metin) {
  const parcalar = String(metin == null ? "" : metin).split("```");
  let html = "";
  for (let i = 0; i < parcalar.length; i++) {
    if (i % 2 === 1) {
      // Tek indisler kod blogu. Ilk satir dil adi olabilir ("python" gibi);
      // bosluk iceriyorsa dil degil, kodun kendisidir — dokunma.
      const satirlar = parcalar[i].split("\n");
      const bas = (satirlar[0] || "").trim();
      const dil = /^[a-z0-9+#._-]{1,15}$/i.test(bas) ? satirlar.shift().trim() : "";
      const kod = satirlar.join("\n").replace(/^\n+|\n+$/g, "");
      html += '<div class="kod-blok"><div class="kod-bas">'
        + '<span class="kod-dil">' + mdKacis(dil || "kod") + "</span>"
        + '<button class="kod-kopya" type="button">kopyala</button></div>'
        + "<pre><code>" + mdKacis(kod) + "</code></pre></div>";
    } else {
      html += mdKacis(parcalar[i])
        .replace(/`([^`\n]+)`/g, '<code class="satir-kod">$1</code>')
        .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
    }
  }
  return html;
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
    document.body.classList.add("goster-mesajlar");   // sinema modunda perde otomatik açılsın
    const dipte = dipteMi();
    const div = document.createElement("div");
    div.className = "msg " + role;
    div.innerHTML = '<div class="msg-avatar">' + (role === "basak" ? "B" : "S")
      + '</div><div class="msg-body"><div class="msg-name">'
      + (role === "basak" ? "BAŞAK" : "SEN")
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
    setOrb("hata");
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
  dot.className = "dot" + (kind === "ok" ? " ok" : kind === "err" ? " err" : kind === "busy" ? " busy" : "");
  $("brainLabel").textContent = label;
}
function setOrb(s) {
  const labels = { bekliyor: "BAŞAK dinliyor", dusunuyor: "BAŞAK düşünüyor", cevapliyor: "BAŞAK konuşuyor", arac: "BAŞAK çalışıyor", hata: "HATA — bir sorun var", dinliyor: "BAŞAK dinliyor" };
  const ds = $("durumSatiri");
  if (ds) ds.textContent = labels[s] || "BAŞAK";
  try {
    if (window.BasakHead) {
      const harita = { bekliyor: "bekliyor", dusunuyor: "dusunuyor", cevapliyor: "konusuyor", arac: "arac", hata: "hata", dinliyor: "dinliyor" };
      BasakHead.durum(harita[s] || "bekliyor");
    }
  } catch (e) { /* sahne yoksa sohbet etkilenmez */ }
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
    setStatus("busy", "Başak düşünüyor...");
    setOrb("dusunuyor");
  },
  toolStatus(text) {
    const el = document.querySelector(".msg.basak.thinking .msg-bubble");
    if (el) el.textContent = text;
    setStatus("busy", text);
    setOrb("arac");
  },
  reply(text, modelInfo) {
    Chat.add("basak", text);
    brainKaynakEtiketi(modelInfo);
    kilidiAc();
    setOrb("cevapliyor");
    if (!state.ttsOn) setTimeout(() => setOrb("bekliyor"), 2200);
    const ml = modelInfo || state.model || "yerel beyin";
    setStatus("ok", ml + " hazır");
    $("input").focus();
  },
  error(msg) {
    // Hata Basak'in AGZINDAN cikmis gibi gorunmemeli: eskiden sohbet
    // balonuna "Uzgunum, bir sorun var: ..." diye ekleniyordu ve baglanti
    // hatasi ile gercek cevap ayni yerde duruyordu.
    Chat.sistem("Bağlantı sorunu: " + msg, true);
    kilidiAc();
    setOrb("hata");
    setStatus("err", "beyin yanıt vermedi");
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
      if (window.BasakHead) BasakHead.ses(seviye / 100);
      if (seviye > 2) {
        setOrb("cevapliyor");
        clearTimeout(sesZamanlayici);
        sesZamanlayici = setTimeout(() => setOrb("bekliyor"), 1200);
      }
    } catch (e) {}
  },
};

/* ---------------- Görünümler ---------------- */
document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const view = btn.dataset.view;
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    $("view-" + view).classList.add("active");
    if (view === "kutuphane") loadKnowledge();
  });
});

async function loadKnowledge() {
  const list = $("fileList");
  const files = await api().knowledge();
  if (!files || !files.length) {
    list.innerHTML = '<li>📁 <span class="muted">Henüz dosya yok — Başak\\knowledge klasörüne ekle</span></li>';
    return;
  }
  // Dosya adlari innerHTML'e dogrudan giriyordu: yerel veri oldugu icin
  // risk dusuktu ama "<" iceren bir ad listeyi bozardi.
  list.innerHTML = files
    .map((f) => '<li><span class="file-ico">📄</span> ' + mdKacis(f) + "</li>")
    .join("");
}

/* ---------------- Gönder ---------------- */
function send() {
  const input = $("input");
  const text = input.value.trim();
  if (!text || state.busy) return;
  if (!state.ready || !window.pywebview || !window.pywebview.api) {
    setStatus("err", "Başak henüz hazırlanıyor, birkaç saniye bekle");
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
$("btnMic").addEventListener("click", () => { if (!state.dinliyor) api().dinle(); });
$("btnTts").addEventListener("click", () => {
  state.ttsOn = !state.ttsOn;
  api().set_tts(state.ttsOn);
  $("btnTts").classList.toggle("active", state.ttsOn);
});
/* Hafizayi temizleme geri alinamaz, eskiden tek tiklaydi. Iki asamali
   onay: ikinci tik 4 saniye icinde gelmezse iptal olur. confirm() yerine
   bu desen secildi — pywebview'da yerel diyalog her zaman guvenilir
   davranmiyor ve pencereyi kilitleyebiliyor. */
let temizleOnayi = null;
async function hafizaTemizle(btn) {
  if (temizleOnayi !== btn) {
    if (temizleOnayi) temizleOnayi.classList.remove("onay-bekliyor");
    temizleOnayi = btn;
    btn.classList.add("onay-bekliyor");
    setStatus("busy", "Hafızayı silmek için tekrar bas");
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
  await api().clear();
  $("messages").innerHTML = "";
  $("chatEmpty").style.display = "block";
  sonGonderilen = "";
  setStatus("ok", "hafıza temizlendi");
}
$("btnClear").addEventListener("click", (e) => hafizaTemizle(e.currentTarget));
$("btnClear2").addEventListener("click", (e) => hafizaTemizle(e.currentTarget));
$("btnClose").addEventListener("click", () => api().quit());
$("btnMesajlar").addEventListener("click", () => {
  document.body.classList.toggle("goster-mesajlar");
});
$("btnKey").addEventListener("click", async () => {
  const key = $("groqKey").value.trim();
  const r = await api().set_key(key);
  if (r && r.cloud) {
    setStatus("ok", (state.model || "yerel beyin") + " + Groq hazır");
    $("btnKey").textContent = "Kaydedildi";
  } else {
    $("btnKey").textContent = "Anahtar geçersiz";
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
  document.body.classList.add("sinema");
  if (!window.BasakHead) Orb.init();   // sahne yoksa eski orb devrede
  try {
    const status = await api().boot();
    if (status && status.ok) {
      state.ready = true;
      $("btnSend").disabled = false;
      $("btnMic").disabled = false;
      state.model = status.model;
      state.ttsOn = !!status.tts_on;
      setStatus("ok", (status.cloud ? "hızlı bulut hazır" : (status.model || "yerel beyin") + " hazır"));
      // Token durumu gösterimi
      if (status.token_durumu) {
        $("tokenLabel").textContent = "token: " + status.token_durumu;
        $("tokenStatus").style.display = "block";
      }
      const sel = $("modelSelect");
      if (status.models && status.models.length) {
        sel.innerHTML = status.models
          .map((m) => "<option>" + mdKacis(m) + "</option>").join("");
        sel.value = status.model || status.models[0];
        sel.onchange = () => { state.model = sel.value; api().set_model(sel.value); setStatus("ok", sel.value + " hazır"); };
      }
      $("btnTts").classList.toggle("active", state.ttsOn);

      // Hatirlatmalari goster
      if (status.reminders && status.reminders.trim()) {
        Chat.add("basak", status.reminders);
      }
    } else {
      setStatus("err", "Ollama kapalı — Başak'ı Başlat.cmd çalıştır");
      setOrb("hata");
    }
  } catch (e) {
    setStatus("err", "Bağlantı sorunu");
    setOrb("hata");
  }
  $("input").focus();
}

window.addEventListener("pywebviewready", boot);
setTimeout(() => { if (!booted && window.pywebview) boot(); }, 800);
setTimeout(() => { if (!booted) boot(); }, 2000);

/* Canlı varlık sahnesini başlat (pywebview'den bağımsız) — hata görünür olsun */
function sahneBaslat() {
  try {
    if (!window.THREE) { $("durumSatiri").textContent = "sahne: Three.js yüklenmedi"; return; }
    if (!window.BasakHead) { $("durumSatiri").textContent = "sahne: head.js yüklenmedi"; return; }
    BasakHead.init();
  } catch (e) {
    $("durumSatiri").textContent = "sahne hatası: " + (e && e.message ? e.message : e);
  }
}
sahneBaslat();
