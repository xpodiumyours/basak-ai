// lab.js — kabul matrisi goruntuleyici (salt-okunur). Tek kaynak:
// /api/matris -> data/kabul-matrisi.json. Hicbir sey yazmaz, hicbir
// simulasyon uretmez; kirmizi hucre gercek kirmizi kalir.
async function yukle() {
  const ozetEl = document.getElementById("ozet");
  const kok = document.getElementById("matris");
  try {
    const r = await window.basakFetch("/api/matris", { cache: "no-store" });
    if (r.status === 401) {
      localStorage.removeItem("basak_token");
      ozetEl.textContent = "Kod gecersiz. Sayfayi yenile, kod tekrar sorulur.";
      return;
    }
    const m = await r.json();
    const d2 = m.duzey2 || {};
    let ty = 0, tk = 0, ts = 0;
    kok.textContent = "";
    for (const s of Object.keys(d2).sort()) {
      const hucreler = d2[s];
      let y = 0, k = 0, sk = 0;
      for (const h of Object.values(hucreler)) {
        if (h.durum === "YESIL") y++;
        else if (h.durum === "KIRMIZI") k++;
        else if (h.durum === "SKIP") sk++;
      }
      ty += y; tk += k; ts += sk;
      const baslik = document.createElement("h3");
      baslik.textContent = s + " — ✅ " + y + "  ❌ " + k + "  ⏭ " + sk;
      kok.appendChild(baslik);
      const tablo = document.createElement("table");
      tablo.style.width = "100%";
      tablo.innerHTML =
        "<tr><th>arac</th><th>durum</th><th>sure</th><th>hata</th></tr>";
      for (const a of Object.keys(hucreler).sort()) {
        const h = hucreler[a];
        const simge = h.durum === "YESIL" ? "✅" :
                      h.durum === "KIRMIZI" ? "❌" : "⏭";
        const tr = document.createElement("tr");
        tr.innerHTML = "<td>" + a + "</td><td>" + simge + " " + h.durum +
          "</td><td>" + (h.sure != null ? h.sure + " sn" : "—") +
          "</td><td style='max-width:420px;overflow-wrap:anywhere'>" +
          (h.hata ? String(h.hata).slice(0, 120) : "") + "</td>";
        tablo.appendChild(tr);
      }
      kok.appendChild(tablo);
    }
    ozetEl.textContent = "Düzey 2: " + ty + " YEŞİL / " + tk +
      " KIRMIZI / " + ts + " SKIP";
  } catch (e) {
    ozetEl.textContent = "Matris okunamadi: " + e;
  }
}
yukle();
setInterval(yukle, 60000);
