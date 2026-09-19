// app.js — web sohbeti. Tek beyin kurali: yalniz yerel kopruyle konusur
// (/api/sohbet POST + /api/olaylar SSE). Baska hicbir arka uca dokunmaz.
const chatEl = document.getElementById("chat");
const msgEl = document.getElementById("message");
const sendEl = document.getElementById("send");

const olaylar = window.basakSse("/api/olaylar");
const balonlar = new Map();   // istek no -> gosterilen balon
const kapat = (el) => el && el.querySelector(".meta")?.remove();

olaylar.addEventListener("message", (e) => {
  let o;
  try { o = JSON.parse(e.data); } catch { return; }
  const no = o.istek;
  if (o.tur === "thinking") {
    if (!balonlar.has(no)) {
      balonlar.set(no, bubble("assistant", "Başak düşünüyor…"));
    }
    return;
  }
  if (o.tur === "toolStatus") {
    let b = balonlar.get(no);
    if (b) {
      b.querySelector(".meta")?.remove();
      b.textContent = "…";
      const m = document.createElement("span");
      m.className = "meta";
      m.textContent = o.metin;
      b.appendChild(m);
    } else {
      balonlar.set(no, bubble("assistant", "…", o.metin));
    }
    return;
  }
  if (o.tur === "parca") {
    let b = balonlar.get(no);
    if (b) {
      kapat(b);
      const ilk = b.textContent === "…" ||
                  b.textContent === "Başak düşünüyor…";
      b.textContent = ilk ? o.metin : b.textContent + o.metin;
    } else {
      b = bubble("assistant", o.metin);
      balonlar.set(no, b);
    }
    return;
  }
  if (o.tur === "bitir") {
    let b = balonlar.get(no);
    if (b) {
      kapat(b);
    } else {
      bubble("assistant", o.cevap || "…");
    }
    balonlar.delete(no);
    sendEl.disabled = false;
    msgEl.focus();
    return;
  }
  if (o.tur === "error") {
    const b = balonlar.get(no);
    if (b) b.remove();
    bubble("assistant", "Hata: " + o.metin);
    balonlar.delete(no);
    sendEl.disabled = false;
  }
});

function bubble(role, text, meta) {
  const el = document.createElement("div");
  el.className = "bubble " + role;
  el.textContent = text;
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

async function send() {
  const text = msgEl.value.trim();
  if (!text || sendEl.disabled) return;
  msgEl.value = "";
  bubble("user", text);
  sendEl.disabled = true;
  try {
    const r = await window.basakFetch("/api/sohbet", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ metin: text }),
    });
    const d = await r.json();
    if (!r.ok || !d.ok) {
      throw new Error(d.error || "Sohbet isteği başarısız");
    }
  } catch (err) {
    bubble("assistant", "Hata: " + (err.message || err));
    sendEl.disabled = false;
  }
}

sendEl.addEventListener("click", send);
msgEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
msgEl.focus();
