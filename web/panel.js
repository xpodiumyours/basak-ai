// panel.js — ayarlar / hafıza / hatırlatma / kullanım paneli.
// Yalnız arayüz: karar vermez, sunucunun söylediğini gösterir. Sunucu
// ölçüm vermezse "—" yazar, sayı uydurmaz.

(() => {
  const panel = document.getElementById("panel");
  const backdrop = document.getElementById("panelBackdrop");
  const acBtn = document.getElementById("panelButton");
  if (!panel || !acBtn) return;

  const el = (id) => document.getElementById(id);

  async function veri(yol, secenek = {}) {
    const r = await window.basakFetch(yol, {
      cache: "no-store",
      ...secenek,
    });
    let govde = {};
    try {
      govde = await r.json();
    } catch {
      govde = {};
    }
    if (!r.ok) {
      throw new Error(govde.error || "Sunucu " + r.status + " döndü.");
    }
    return govde;
  }

  function ac(evet) {
    panel.hidden = !evet;
    backdrop.hidden = !evet;
    acBtn.setAttribute("aria-expanded", evet ? "true" : "false");
    if (evet) {
      ayarlariYukle();
      hafizayiYukle();
      hatirlatmalariYukle();
      kotayiYukle();
      const ilk = el("kisiselTalimat");
      if (ilk) setTimeout(() => ilk.focus(), 50);
    }
  }

  acBtn.addEventListener("click", () => ac(panel.hidden));
  const kapat = el("panelKapat");
  if (kapat) kapat.addEventListener("click", () => ac(false));
  if (backdrop) backdrop.addEventListener("click", () => ac(false));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !panel.hidden) ac(false);
  });

  // ── kişisel talimat ────────────────────────────────────────────────
  async function ayarlariYukle() {
    try {
      const d = await veri("/api/ayarlar");
      const a = d.ayarlar || {};
      el("kisiselTalimat").value = a.kisisel_talimat || "";
      el("hitap").value = a.hitap || "";
      el("dil").value = a.dil || "";
    } catch (e) {
      durum("ayarDurum", "Ayarlar okunamadı: " + e.message, true);
    }
  }

  function durum(id, metin, hata = false) {
    const k = el(id);
    if (!k) return;
    k.textContent = metin || "";
    k.classList.toggle("panel-durum-hata", !!hata);
  }

  const kaydet = el("ayarKaydet");
  if (kaydet) {
    kaydet.addEventListener("click", async () => {
      kaydet.disabled = true;
      durum("ayarDurum", "Kaydediliyor…");
      try {
        await veri("/api/ayarlar", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            kisisel_talimat: el("kisiselTalimat").value,
            hitap: el("hitap").value,
            dil: el("dil").value,
          }),
        });
        durum("ayarDurum", "Kaydedildi.");
      } catch (e) {
        durum("ayarDurum", e.message, true);
      } finally {
        kaydet.disabled = false;
      }
    });
  }

  // ── hatırlatmalar ──────────────────────────────────────────────────
  function zamanMetni(epoch) {
    if (!epoch) return "—";
    try {
      return new Date(epoch * 1000).toLocaleString("tr-TR", {
        dateStyle: "short",
        timeStyle: "short",
      });
    } catch {
      return "—";
    }
  }

  async function hatirlatmalariYukle() {
    const liste = el("hatirlatmaListe");
    if (!liste) return;
    try {
      const d = await veri("/api/hatirlatmalar");
      const hepsi = (d.bekleyen || []).concat(d.gelen || []);
      liste.textContent = "";
      if (!hepsi.length) {
        const li = document.createElement("li");
        li.className = "panel-bos";
        li.textContent = "Kurulmuş hatırlatma yok.";
        liste.appendChild(li);
        return;
      }
      for (const h of hepsi) {
        const li = document.createElement("li");
        li.className = "panel-ogee";
        const metin = document.createElement("span");
        metin.className = "panel-oge-metin";
        metin.textContent = (h.metin || "") + " · " + zamanMetni(h.zaman);
        const sil = document.createElement("button");
        sil.type = "button";
        sil.className = "panel-sil";
        sil.textContent = "×";
        sil.setAttribute("aria-label", "Hatırlatmayı sil");
        sil.addEventListener("click", async () => {
          sil.disabled = true;
          try {
            await veri("/api/hatirlatmalar/" + encodeURIComponent(h.id), {
              method: "DELETE",
            });
            await hatirlatmalariYukle();
          } catch (e) {
            metin.textContent = e.message;
          }
        });
        li.appendChild(metin);
        li.appendChild(sil);
        liste.appendChild(li);
      }
    } catch (e) {
      liste.textContent = "Hatırlatmalar okunamadı: " + e.message;
    }
  }

  const ekle = el("hatirlatmaEkle");
  if (ekle) {
    ekle.addEventListener("click", async () => {
      const metin = el("hatirlatmaMetin").value.trim();
      const zaman = el("hatirlatmaZaman").value;
      if (!metin || !zaman) {
        el("hatirlatmaMetin").focus();
        return;
      }
      ekle.disabled = true;
      try {
        await veri("/api/hatirlatmalar", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ metin, zaman }),
        });
        el("hatirlatmaMetin").value = "";
        el("hatirlatmaZaman").value = "";
        await hatirlatmalariYukle();
      } catch (e) {
        el("hatirlatmaMetin").value = metin;
        alert(e.message);
      } finally {
        ekle.disabled = false;
      }
    });
  }

  // ── hafıza ─────────────────────────────────────────────────────────
  async function hafizayiYukle() {
    const liste = el("hafizaListe");
    if (!liste) return;
    try {
      const d = await veri("/api/hafiza");
      const anilar = d.anilar || [];
      liste.textContent = "";
      if (!anilar.length) {
        const li = document.createElement("li");
        li.className = "panel-bos";
        li.textContent = "Henüz hatırlanan bir şey yok.";
        liste.appendChild(li);
        return;
      }
      for (const a of anilar) {
        const li = document.createElement("li");
        li.className = "panel-ogee";
        const metin = document.createElement("span");
        metin.className = "panel-oge-metin";
        const ham = String(a.metin || "").replace(/\s+/g, " ").trim();
        metin.textContent = ham.length > 160 ? ham.slice(0, 160) + "…" : ham;
        metin.title = ham;
        const sil = document.createElement("button");
        sil.type = "button";
        sil.className = "panel-sil";
        sil.textContent = "×";
        sil.setAttribute("aria-label", "Anıyı sil");
        sil.addEventListener("click", async () => {
          sil.disabled = true;
          try {
            await veri("/api/hafiza/" + encodeURIComponent(a.id), {
              method: "DELETE",
            });
            await hafizayiYukle();
          } catch (e) {
            durum("hafizaDurum", e.message, true);
          }
        });
        li.appendChild(metin);
        li.appendChild(sil);
        liste.appendChild(li);
      }
    } catch (e) {
      durum("hafizaDurum", "Hafıza okunamadı: " + e.message, true);
    }
  }

  const yenile = el("hafizaYenile");
  if (yenile) yenile.addEventListener("click", hafizayiYukle);

  const temizle = el("hafizaTemizle");
  if (temizle) {
    temizle.addEventListener("click", async () => {
      if (!confirm("Sohbetten öğrenilen tüm anılar silinsin mi?")) return;
      temizle.disabled = true;
      try {
        const d = await veri("/api/hafiza/temizle", { method: "POST" });
        durum("hafizaDurum", (d.silinen || 0) + " anı unutuldu.");
        await hafizayiYukle();
      } catch (e) {
        durum("hafizaDurum", e.message, true);
      } finally {
        temizle.disabled = false;
      }
    });
  }

  // ── kullanım ───────────────────────────────────────────────────────
  async function kotayiYukle() {
    const liste = el("kotaListe");
    if (!liste) return;
    try {
      const d = await veri("/api/kota");
      const kota = d.kota || {};
      const satirlar = kota.saglayicilar || [];
      liste.textContent = "";
      if (!satirlar.length) {
        const li = document.createElement("li");
        li.className = "panel-bos";
        li.textContent = "Ölçüm yok.";
        liste.appendChild(li);
        return;
      }
      for (const s of satirlar) {
        const li = document.createElement("li");
        li.className = "panel-ogee panel-oge-kota";
        const ad = document.createElement("span");
        ad.className = "panel-oge-metin";
        const token = s.bugun_token == null ? "—" : s.bugun_token + " token";
        ad.textContent = (s.gorunen || s.ad) + " · " + token;
        li.appendChild(ad);
        liste.appendChild(li);
      }
    } catch (e) {
      liste.textContent = "Kullanım okunamadı: " + e.message;
    }
  }

  // Kota göstergesi üst çubukta: yalnız ölçülmüş sayı.
  async function kotaSeridi() {
    const k = el("kotaDurum");
    if (!k) return;
    try {
      const d = await veri("/api/kota");
      const kota = d.kota || {};
      const token = Number(kota.bugun_token || 0);
      k.textContent = token ? "Bugün " + token.toLocaleString("tr-TR") + " token" : "";
      k.hidden = !token;
    } catch {
      k.hidden = true;
    }
  }

  // Dışarıdan açma: karşılama kartları bu köprüyü kullanır. Hedef id
  // verilirse panel açıldıktan sonra o alana kaydırılır.
  window.basakPanelAc = (hedefId) => {
    ac(true);
    if (!hedefId) return;
    setTimeout(() => {
      const hedef = el(hedefId);
      if (!hedef) return;
      hedef.scrollIntoView({ block: "center", behavior: "smooth" });
      if (typeof hedef.focus === "function") hedef.focus({ preventScroll: true });
    }, 120);
  };

  window.basakPanelKotaYenile = kotaSeridi;
  setTimeout(kotaSeridi, 1200);
})();
