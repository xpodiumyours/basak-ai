/* eklenti/panel.js — yan panel: sohbet + bağlantı + gözlem önizlemesi.
 *
 * Sohbet burada ÜRETİLMEZ: mesaj çekirdeğe gider (arka.js → WS), cevap
 * aynı kanaldan döner. Panel yalnız gösterir.
 */

const $ = (id) => document.getElementById(id);

/* Oturum geçmişi: bulutta kalıcı disk yok ve bağlantı 300 sn'de yenilenir.
 * Bu yüzden her mesajla birlikte son konuşma gönderilir; model, hangi
 * instance'a düşerse düşsün konuşmayı hatırlar. Kırpma yok (AGENTS §0). */
const GECMIS = [];

function durumYaz(durum, hata) {
  const rozet = $("durum");
  rozet.textContent = durum === "bagli" ? "bağlı" :
    durum === "baglaniyor" ? "bağlanıyor…" :
    durum === "hata" ? "ulaşılamadı" : "kapalı";
  rozet.className = "rozet " + (durum === "bagli" ? "iyi" :
    durum === "hata" ? "kotu" : "kapali");
  $("hata").textContent = hata || "";
}

async function durumSor() {
  try {
    const cevap = await chrome.runtime.sendMessage({ tip: "durum" });
    if (cevap) durumYaz(cevap.durum, cevap.sonHata);
  } catch (hata) {
    durumYaz("kapali", "");
  }
}

async function ayarlariYukle() {
  const veri = await chrome.storage.local.get(["sunucu", "anahtar"]);
  if (veri.sunucu) $("sunucu").value = veri.sunucu;
  if (veri.anahtar) $("anahtar").value = veri.anahtar;
}

/* ── Sohbet ───────────────────────────────────────────────────────── */

function balon(kim, metin) {
  const bos = $("mesajlar").querySelector(".bos");
  if (bos) bos.remove();
  const kutu = document.createElement("div");
  kutu.className = "balon " + kim;
  kutu.textContent = metin;
  $("mesajlar").appendChild(kutu);
  $("mesajlar").scrollTop = $("mesajlar").scrollHeight;
  return kutu;
}

function yaziyorMu(acik) {
  let nokta = $("mesajlar").querySelector(".bekliyor");
  if (acik && !nokta) {
    nokta = document.createElement("div");
    nokta.className = "balon basak bekliyor";
    nokta.textContent = "yazıyor…";
    $("mesajlar").appendChild(nokta);
    $("mesajlar").scrollTop = $("mesajlar").scrollHeight;
  } else if (!acik && nokta) {
    nokta.remove();
  }
}

$("yaz").addEventListener("submit", async (olay) => {
  olay.preventDefault();
  const metin = $("metin").value.trim();
  if (!metin) return;
  $("metin").value = "";
  $("gonder").disabled = true;
  balon("kullanici", metin);
  yaziyorMu(true);

  let cevap;
  try {
    cevap = await chrome.runtime.sendMessage({
      tip: "sohbet", metin, gecmis: GECMIS.slice()
    });
  } catch (hata) {
    cevap = { ok: false, hata: String(hata) };
  }
  yaziyorMu(false);
  $("gonder").disabled = false;

  if (!cevap) {
    balon("hata", "cevap gelmedi");
    return;
  }
  if (!cevap.ok) {
    balon("hata", cevap.hata || "bilinmeyen hata");
    return;
  }
  const sonuc = cevap.sonuc || {};
  GECMIS.push({ role: "user", content: metin });
  GECMIS.push({ role: "assistant", content: sonuc.cevap || "" });
  balon("basak", sonuc.cevap || "(boş cevap)");
  if (sonuc.kaynak) {
    const kaynak = document.createElement("div");
    kaynak.className = "kaynak";
    kaynak.textContent = "kaynak: " + sonuc.kaynak;
    $("mesajlar").appendChild(kaynak);
  }
});

$("metin").addEventListener("keydown", (olay) => {
  if (olay.key === "Enter" && !olay.shiftKey) {
    olay.preventDefault();
    $("yaz").requestSubmit();
  }
});

/* ── Bağlantı ─────────────────────────────────────────────────────── */

$("baglan").addEventListener("click", async () => {
  $("baglan").disabled = true;
  try {
    const cevap = await chrome.runtime.sendMessage({
      tip: "baglan",
      sunucu: $("sunucu").value,
      anahtar: $("anahtar").value
    });
    durumYaz((cevap && cevap.durum) || "kapali", (cevap && cevap.sonHata) || "");
  } finally {
    $("baglan").disabled = false;
  }
});

/* ── Gözlem önizlemesi ────────────────────────────────────────────── */

$("onizle").addEventListener("click", async () => {
  const ozet = $("ozet");
  const liste = $("liste");
  ozet.textContent = "okunuyor…";
  liste.innerHTML = "";
  let cevap;
  try {
    cevap = await chrome.runtime.sendMessage({ tip: "onizleme" });
  } catch (hata) {
    ozet.textContent = "okunamadı: " + String(hata);
    return;
  }
  if (!cevap || !cevap.ok) {
    ozet.textContent = "okunamadı: " + ((cevap && cevap.hata) || "bilinmeyen hata");
    return;
  }
  const gozlem = cevap.gozlem || {};
  const ogeler = gozlem.ogeler || [];
  ozet.textContent = (gozlem.baslik || gozlem.url || "sayfa") +
    " — " + ogeler.length + " öğe";
  ogeler.slice(0, 40).forEach((oge) => {
    const satir = document.createElement("li");
    const rol = document.createElement("span");
    rol.className = "rol";
    rol.textContent = oge.rol;
    const ad = document.createElement("span");
    ad.className = "ad";
    ad.textContent = oge.ad || "(adsız)";
    satir.appendChild(rol);
    satir.appendChild(ad);
    if (oge.deger) {
      const deger = document.createElement("em");
      deger.textContent = oge.deger;
      satir.appendChild(deger);
    }
    if (oge.kapali) {
      const kapali = document.createElement("span");
      kapali.className = "kapali";
      kapali.textContent = "kapalı";
      satir.appendChild(kapali);
    }
    liste.appendChild(satir);
  });
  if (ogeler.length > 40) {
    const kalan = document.createElement("li");
    kalan.className = "fazla";
    kalan.textContent = "… " + (ogeler.length - 40) + " öğe daha var (Başak hepsini görebilir)";
    liste.appendChild(kalan);
  }
});

document.addEventListener("DOMContentLoaded", async () => {
  await ayarlariYukle();
  await durumSor();
  setInterval(durumSor, 3000);
  $("metin").focus();
});
