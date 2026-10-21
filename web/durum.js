/* web/durum.js — Başak'ın canlı durumunu ölçer.
 *
 * Kurallar:
 * - Her satır GERÇEK bir istekle ölçülür. Ölçülemeyen şey "yeşil" yazılmaz;
 *   ölçülemediyse "ölçülemedi" yazılır.
 * - Bu sayfa yalnız ARAYÜZ + ÖLÇÜM GÖRÜNTÜLEYİCİDİR: ikinci bir beyin,
 *   ikinci bir sağlayıcı zinciri veya ikinci bir araç çalıştırıcı yoktur.
 *   Ölçtüğü şey çekirdeğin kendi uçlarıdır (/api/durum, /api/sohbet,
 *   /api/eklenti).
 * - Model çağrısı yalnız "Beyin yanıt veriyor" satırı içindir; o da
 *   kullanıcının gerçekten gördüğü cevaptır (sabit metin, sahte sonuç yok).
 */
(function () {
  "use strict";

  var SORU = "Canlı test: 3+4 kaç? Sadece sayı yaz.";
  var KANAL_SURESI = 5000;
  var canliAracSayisi = 0;      // canlı /api/durum ölçümü
  var kabulVeri = null;         // depoda kayıtlı ölçüm

  var kontrollerEl = document.getElementById("kontroller");
  var sonEl = document.getElementById("sonOlcum");
  var kabulEl = document.getElementById("kabul");
  var sinirlarEl = document.getElementById("sinirlar");
  var yenileEl = document.getElementById("yenile");

  if (!kontrollerEl) return;

  /* ── Satır kurucusu ───────────────────────────────────────────── */
  var satirlar = {};

  function satirEkle(ad, baslik) {
    var kutu = document.createElement("div");
    kutu.className = "kontrol";
    var sol = document.createElement("strong");
    sol.textContent = baslik;
    var sag = document.createElement("div");
    sag.className = "durum waiting";
    sag.textContent = "ölçülüyor…";
    kutu.appendChild(sol);
    kutu.appendChild(sag);
    kontrollerEl.appendChild(kutu);
    satirlar[ad] = {
      el: sag,
      yaz: function (durum, metin, ayrinti) {
        sag.className = "durum " + durum;
        sag.textContent = metin || "";
        if (ayrinti) {
          var alt = document.createElement("span");
          alt.className = "ayrinti";
          alt.textContent = ayrinti;
          sag.appendChild(alt);
        }
      }
    };
    return satirlar[ad];
  }

  function yaz(ad, durum, metin, ayrinti) {
    if (satirlar[ad]) satirlar[ad].yaz(durum, metin, ayrinti);
  }

  /* ── Ölçüm 1: sunucunun kendi durumu ──────────────────────────── */
  async function sunucuOlc() {
    var r = await window.basakFetch("/api/durum", { cache: "no-store" });
    if (!r.ok) throw new Error("Sunucu " + r.status + " döndü");
    var d = await r.json();
    if (!d || !d.ok) throw new Error("Sunucu \"ok\" demedi");

    var arac = Number(d.arac_sayisi || 0);
    canliAracSayisi = arac;
    yaz("arac", arac > 0 ? "pass" : "fail",
        arac > 0 ? arac + " araç hazır" : "Araç sayısı okunamadı",
        arac > 0 ? "Her araç gerçek bir iş yapar; gizli seçici yok." : "");

    var saglayicilar = Array.isArray(d.saglayicilar) ? d.saglayicilar : [];
    var eksik = Array.isArray(d.eksik_saglayicilar) ? d.eksik_saglayicilar : [];
    yaz("saglayici", saglayicilar.length ? "pass" : "fail",
        saglayicilar.length + " model sağlayıcı bağlı",
        saglayicilar.join(", ") +
        (eksik.length ? " · eksik: " + eksik.join(", ") : ""));

    var surum = String(d.commit || "").trim();
    yaz("surum", surum ? "pass" : "waiting",
        surum ? "Sürüm " + surum : "Sürüm damgası yok",
        d.runtime === "vercel" ? "Bulutta (Vercel) çalışıyor." : "Yerelde çalışıyor.");

    yaz("akis", d.tasima === "canli-ndjson" ? "pass" : "waiting",
        d.tasima === "canli-ndjson" ? "Cevap harf harf akıyor" : "Cevap tek parça geliyor",
        d.tasima === "canli-ndjson"
          ? "Beklemeden yazıyor; uzun cevaplar da kesilmeden görünüyor."
          : "Bu sürümde akış tek parça.");

    yaz("devam", d.checkpoint_resume ? "pass" : "waiting",
        d.checkpoint_resume ? "Yarım kalan iş sürdürülebiliyor" : "Yarım kalan iş sürdürülemiyor",
        d.checkpoint_resume
          ? "Kopan bir tur kaldığı yerden devam eder."
          : "Bağlantı koparsa tur baştan başlar. Henüz eklenmedi.");
  }

  /* ── Ölçüm 2: beyin gerçekten yanıt veriyor mu ─────────────────── */
  async function beyinOlc() {
    var baslangic = (window.performance && performance.now)
      ? performance.now() : Date.now();
    var r = await window.basakFetch("/api/sohbet", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "accept": "application/x-ndjson"
      },
      body: JSON.stringify({ metin: SORU, misafir: true, gecmis: [] })
    });
    if (!r.ok) {
      var hata = "";
      try {
        var d = await r.json();
        hata = d.error || "";
      } catch (e) { /* gövde JSON değil */ }
      throw new Error(hata || "Sunucu " + r.status + " döndü");
    }

    var tur = String(r.headers.get("content-type") || "").toLowerCase();
    var cevap = "";
    var kaynak = "";
    if (tur.indexOf("application/x-ndjson") >= 0 && r.body) {
      var okuyucu = r.body.getReader();
      var cozucu = new TextDecoder("utf-8");
      var tampon = "";
      for (;;) {
        var oku = await okuyucu.read();
        if (oku.done) break;
        tampon += cozucu.decode(oku.value, { stream: true });
        var satirlar = tampon.split("\n");
        tampon = satirlar.pop();
        for (var i = 0; i < satirlar.length; i++) {
          var satir = satirlar[i].trim();
          if (!satir) continue;
          var olay;
          try { olay = JSON.parse(satir); } catch (e) { continue; }
          if (!olay || typeof olay !== "object") continue;
          if (olay.tur === "bitir") {
            cevap = String(olay.cevap || olay.metin || "");
            kaynak = String(olay.kaynak || kaynak);
          } else if (olay.tur === "runState" && olay.provider) {
            kaynak = String(olay.provider);
          } else if (olay.tur === "error") {
            throw new Error(String(olay.metin || "Beyin hata verdi"));
          }
        }
      }
    } else {
      var govde = await r.json();
      cevap = String(govde.cevap || "");
      kaynak = String(govde.kaynak || "");
      if (Array.isArray(govde.olaylar)) {
        for (var j = 0; j < govde.olaylar.length; j++) {
          var o = govde.olaylar[j] || {};
          if (o.tur === "bitir") {
            cevap = String(o.cevap || o.metin || cevap);
            kaynak = String(o.kaynak || kaynak);
          }
        }
      }
    }

    var sure = Math.round(((window.performance && performance.now)
      ? performance.now() : Date.now()) - baslangic);
    if (!cevap) throw new Error("Cevap boş geldi");
    yaz("beyin", "pass", "Evet — " + (kaynak || "sağlayıcı belirtilmedi") +
        ", " + (sure / 1000).toFixed(1) + " sn",
        "Soru: " + SORU + " · Cevap: " + cevap.slice(0, 200));
    return { cevap: cevap, kaynak: kaynak, sure: sure };
  }

  /* ── Ölçüm 3: tarayıcı eklentisi kanalı ───────────────────────── */
  function kanalOlc() {
    return new Promise(function (coz) {
      var sema = location.protocol === "https:" ? "wss:" : "ws:";
      var adres = sema + "//" + location.host + "/api/eklenti";
      var soket = null;
      var bitti = false;
      var zaman = setTimeout(function () {
        if (bitti) return;
        bitti = true;
        try { if (soket) soket.close(); } catch (e) { /* yoksay */ }
        coz({ ok: false, hata: KANAL_SURESI / 1000 + " saniyede yanıt yok" });
      }, KANAL_SURESI);

      try {
        soket = new WebSocket(adres);
      } catch (e) {
        clearTimeout(zaman);
        coz({ ok: false, hata: String((e && e.message) || e) });
        return;
      }
      soket.onopen = function () {
        if (bitti) return;
        bitti = true;
        clearTimeout(zaman);
        try { soket.close(); } catch (e) { /* yoksay */ }
        coz({ ok: true });
      };
      soket.onerror = function () {
        if (bitti) return;
        bitti = true;
        clearTimeout(zaman);
        coz({ ok: false, hata: "Sunucu bağlantıyı kabul etmedi" });
      };
    });
  }

  /* ── Genel akış ───────────────────────────────────────────────── */
  var calisiyor = false;

  async function olc() {
    if (calisiyor) return;
    calisiyor = true;
    if (yenileEl) {
      yenileEl.disabled = true;
      yenileEl.textContent = "Ölçülüyor…";
    }
    var zaman = new Date();
    var hatalar = 0;

    try {
      await sunucuOlc();
    } catch (hata) {
      hatalar += 1;
      yaz("arac", "fail", "Sunucuya ulaşılamadı", String((hata && hata.message) || hata));
      yaz("saglayici", "waiting", "Ölçülemedi");
      yaz("surum", "waiting", "Ölçülemedi");
      yaz("akis", "waiting", "Ölçülemedi");
      yaz("devam", "waiting", "Ölçülemedi");
    }

    try {
      await beyinOlc();
    } catch (hata) {
      hatalar += 1;
      yaz("beyin", "fail", "Yanıt gelmedi", String((hata && hata.message) || hata));
    }

    try {
      var kanal = await kanalOlc();
      if (kanal.ok) {
        yaz("kanal", "pass", "Kanal açık",
            "Eklentinin kullandığı adres bu an bağlantıyı kabul etti.");
      } else {
        yaz("kanal", "fail", "Kanal açılmadı", kanal.hata);
      }
    } catch (hata) {
      hatalar += 1;
      yaz("kanal", "fail", "Kanal açılmadı", String((hata && hata.message) || hata));
    }

    if (sonEl) {
      sonEl.textContent = "Son ölçüm: " + zaman.toLocaleTimeString("tr-TR") +
        (hatalar ? " · " + hatalar + " kontrol yanıt alamadı."
                  : " · tüm kontroller yanıt verdi.");
    }
    if (yenileEl) {
      yenileEl.disabled = false;
      yenileEl.textContent = "Yeniden ölç";
    }
    calisiyor = false;
    if (kabulVeri) kabulCiz();
  }

  /* ── Depoda kayıtlı ölçüm (canlı değil) ───────────────────────── */
  async function kabulOku() {
    try {
      var r = await fetch("/durum-kabul.json", { cache: "no-store" });
      if (!r.ok) throw new Error("dosya yok (" + r.status + ")");
      kabulVeri = await r.json();
      kabulCiz();
    } catch (hata) {
      kabulEl.textContent = "Depoda kayıtlı ölçüm okunamadı: " +
        String((hata && hata.message) || hata);
      sinirlarEl.textContent = "";
    }
  }

  function kabulCiz() {
    if (!kabulVeri) return;
    try {
      var d = kabulVeri;
      kabulEl.textContent = "";

      var sayilar = document.createElement("div");
      sayilar.className = "sayilar";
      var alanlar = [
        ["Test", (d.test_gecen || 0) + " geçti"],
        ["Atlanan", String(d.test_atlandi || 0)],
        ["Araç", String(d.arac_sayisi || 0)],
        ["Yetenek alanı", String(d.yetenek_alani || 0)]
      ];
      for (var i = 0; i < alanlar.length; i++) {
        var kutu = document.createElement("div");
        kutu.className = "sayi";
        var buyuk = document.createElement("b");
        buyuk.textContent = alanlar[i][1];
        var etiket = document.createElement("span");
        etiket.textContent = alanlar[i][0];
        kutu.appendChild(buyuk);
        kutu.appendChild(etiket);
        sayilar.appendChild(kutu);
      }
      kabulEl.appendChild(sayilar);

      var not = document.createElement("div");
      not.className = "olcum-notu";
      var tarih = d.uretildi || "tarih yok";
      not.textContent = "Ölçüm " + tarih + " tarihinde `" + (d.komut || "pytest") +
        "` ile alındı. Bu bir canlı ölçüm değildir; yukarıdaki canlı satırlar " +
        "her zaman tazedir.";
      kabulEl.appendChild(not);

      if (typeof d.arac_sayisi === "number" && d.arac_sayisi) {
        var canli = canliAracSayisi;
        if (canli && canli !== d.arac_sayisi) {
          var uyari = document.createElement("div");
          uyari.className = "olcum-notu uyari";
          uyari.textContent = "Kayıtlı ölçüm eski: o tarihte " + d.arac_sayisi +
            " araç vardı, şu an canlı sayı farklı. Canlı satıra bak.";
          kabulEl.appendChild(uyari);
        }
      }

      if (Array.isArray(d.sinirlar) && d.sinirlar.length) {
        var liste = document.createElement("ul");
        liste.className = "duz";
        for (var j = 0; j < d.sinirlar.length; j++) {
          var li = document.createElement("li");
          li.textContent = d.sinirlar[j];
          liste.appendChild(li);
        }
        sinirlarEl.textContent = "";
        sinirlarEl.appendChild(liste);
      }
    } catch (hata) {
      kabulEl.textContent = "Depoda kayıtlı ölçüm çizilemedi: " +
        String((hata && hata.message) || hata);
    }
  }

  /* ── Başlat ───────────────────────────────────────────────────── */
  satirEkle("beyin", "Beyin yanıt veriyor");
  satirEkle("arac", "Kaç araç var");
  satirEkle("saglayici", "Hangi modeller bağlı");
  satirEkle("kanal", "Tarayıcı eklentisi kanalı");
  satirEkle("surum", "Canlı sürüm");
  satirEkle("akis", "Cevap akışı");
  satirEkle("devam", "Yarım kalan işi sürdürme");

  if (yenileEl) yenileEl.addEventListener("click", function () { olc(); });

  kabulOku();
  olc();
})();
