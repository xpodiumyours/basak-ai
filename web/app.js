// app.js — web sohbeti. Tek beyin kurali: yalniz yerel kopruyle konusur
// (/api/sohbet POST + /api/olaylar HTTP polling). Baska arka uca dokunmaz.
const chatEl = document.getElementById("chat");
const msgEl = document.getElementById("message");
const sendEl = document.getElementById("send");

const balonlar = new Map();
const sonAracDurumu = new Map();
const kapat = (el) => el && el.querySelector(".meta")?.remove();
const uyu = (ms) => new Promise((coz) => setTimeout(coz, ms));

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
      b.textContent = "…";
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
      const ilk = b.textContent === "…" ||
                  b.textContent === "Başak düşünüyor…";
      b.textContent = ilk ? o.metin : b.textContent + o.metin;
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
      if (!b.textContent || b.textContent === "Başak düşünüyor…" ||
          b.textContent === "…") {
        b.textContent = o.cevap || "…";
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
msgEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
msgEl.focus();
