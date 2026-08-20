/* ============ Başak — ön yüz mantığı (js_api köprüsü) ============ */

const $ = (id) => document.getElementById(id);
const state = { busy: false, ready: false, model: null, dinliyor: false, ttsOn: false, gucle: false };

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
    if (!window.THREE) { $("orbStatus").textContent = "3D yok"; return; }
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

/* ---------------- Sohbet ---------------- */
const Chat = (function () {
  const scroll = $("chatScroll"), list = $("messages"), empty = $("chatEmpty");
  function add(role, text) {
    empty.style.display = "none";
    const div = document.createElement("div");
    div.className = "msg " + role;
    div.innerHTML = '<div class="msg-avatar">' + (role === "basak" ? "B" : "S") + '</div><div class="msg-body"><div class="msg-name">' + (role === "basak" ? "BAŞAK" : "SEN") + '</div><div class="msg-bubble"></div></div>';
    div.querySelector(".msg-bubble").textContent = text;
    list.appendChild(div);
    scroll.scrollTop = scroll.scrollHeight;
    return div;
  }
  function thinking() {
    empty.style.display = "none";
    const div = document.createElement("div");
    div.className = "msg basak thinking";
    div.innerHTML = '<div class="msg-avatar">B</div><div class="msg-body"><div class="msg-name">BAŞAK</div><div class="msg-bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div></div>';
    list.appendChild(div);
    scroll.scrollTop = scroll.scrollHeight;
    return div;
  }
  function remove(el) { el.remove(); }
  return { add, thinking, remove };
})();

/* ---------------- Durum ---------------- */
function setStatus(kind, label) {
  const dot = $("brainDot");
  dot.className = "dot" + (kind === "ok" ? " ok" : kind === "err" ? " err" : kind === "busy" ? " busy" : "");
  $("brainLabel").textContent = label;
}
function setOrb(s) {
  Orb.setState(s);
  const labels = { bekliyor: "BEKLİYOR", dusunuyor: "DÜŞÜNÜYOR", cevapliyor: "CEVAPLIYOR", hata: "HATA", dinliyor: "DİNLİYOR" };
  $("orbStatus").textContent = labels[s] || s;
}

/* ---------------- Python'dan gelen geri çağrılar ---------------- */
window.BasakUI = {
  thinking() {
    Chat.thinking();
    state.busy = true;
    $("btnSend").disabled = true;
    setStatus("busy", "Başak düşünüyor...");
    setOrb("dusunuyor");
  },
  toolStatus(text) {
    const el = document.querySelector(".msg.basak.thinking .msg-bubble");
    if (el) el.textContent = text;
    setStatus("busy", text);
    setOrb("dusunuyor");
  },
  reply(text, modelInfo) {
    Chat.add("basak", text);
    state.busy = false;
    $("btnSend").disabled = false;
    setOrb("bekliyor");
    const ml = modelInfo || state.model || "yerel beyin";
    setStatus("ok", ml + " hazır");
    $("input").focus();
  },
  error(msg) {
    Chat.add("basak", "Üzgünüm, bir sorun var: " + msg);
    state.busy = false;
    $("btnSend").disabled = false;
    setOrb("hata");
    setStatus("err", "beyin yanıt vermedi");
  },
  listening(on) {
    state.dinliyor = on;
    $("btnMic").classList.toggle("active", on);
    $("btnMic").disabled = on;
    setOrb(on ? "dinliyor" : "bekliyor");
    $("orbStatus").textContent = on ? "DİNLİYOR" : "BEKLİYOR";
  },
  sttResult(text) {
    const input = $("input");
    input.value = text;
    send();
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
  list.innerHTML = files.map((f) => '<li><span class="file-ico">📄</span> ' + f + "</li>").join("");
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
  input.value = "";
  input.style.height = "auto";
  Chat.add("user", text);
  api().mesaj(text);
}

/* ---------------- Olaylar ---------------- */
$("btnSend").addEventListener("click", send);
$("btnMic").addEventListener("click", () => { if (!state.dinliyor) api().dinle(); });
$("btnTts").addEventListener("click", () => {
  state.ttsOn = !state.ttsOn;
  api().set_tts(state.ttsOn);
  $("btnTts").classList.toggle("active", state.ttsOn);
});
$("btnClear").addEventListener("click", async () => {
  await api().clear();
  $("messages").innerHTML = "";
  $("chatEmpty").style.display = "block";
});
$("btnClear2").addEventListener("click", async () => {
  await api().clear();
  $("messages").innerHTML = "";
  $("chatEmpty").style.display = "block";
});
$("btnClose").addEventListener("click", () => api().quit());
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
  Orb.init();
  try {
    const status = await api().boot();
    if (status && status.ok) {
      state.ready = true;
      $("btnSend").disabled = false;
      $("btnMic").disabled = false;
      state.model = status.model;
      state.ttsOn = !!status.tts_on;
      state.gucle = !!status.gucle_mod;
      setStatus("ok", (status.model || "yerel beyin") + " hazır");
      $("topSub").textContent = "yerel beyin " + (status.model || "") + " hazır";
      const sel = $("modelSelect");
      if (status.models && status.models.length) {
        sel.innerHTML = status.models.map((m) => "<option>" + m + "</option>").join("");
        sel.value = status.model || status.models[0];
        sel.onchange = () => { state.model = sel.value; api().set_model(sel.value); setStatus("ok", sel.value + " hazır"); };
      }
      $("btnTts").classList.toggle("active", state.ttsOn);
      const ct = $("cloudToggle");
      if (ct) {
        ct.textContent = state.gucle ? "Açık" : "Kapalı";
        ct.classList.toggle("active", state.gucle);
        ct.onclick = () => {
          state.gucle = !state.gucle;
          api().set_cloud(state.gucle);
          ct.classList.toggle("active", state.gucle);
          ct.textContent = state.gucle ? "Açık" : "Kapalı";
        };
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
