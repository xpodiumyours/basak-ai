/* web/olcum.js — cerezsiz anonim sayfa sayaci + arac geri bildirimi.
   Cerez YOK, kimlik YOK: yalniz sayfa yolu ve gun toplam sayilir.
   DNT/GPC sinyali varsa hicbir sey gonderilmez. */
(function () {
  "use strict";

  function dntAcik() {
    try {
      return (navigator.doNotTrack === "1" ||
              window.doNotTrack === "1" ||
              navigator.msDoNotTrack === "1" ||
              navigator.globalPrivacyControl === true);
    } catch (e) { return false; }
  }

  function gonder(adres, veri) {
    try {
      var metin = JSON.stringify(veri);
      if (navigator.sendBeacon) {
        navigator.sendBeacon(adres, metin);
        return;
      }
      var x = new XMLHttpRequest();
      x.open("POST", adres, true);
      x.setRequestHeader("Content-Type", "text/plain");
      x.send(metin);
    } catch (e) { /* sayim kritik degil; sessiz gec */ }
  }

  if (dntAcik()) return;

  gonder("/api/olcum", { yol: location.pathname });

  // ── Araç sayfasi mikro-geri bildirimi (yerel hesaplayicilar) ──────
  var dugme = document.getElementById("hesapla");
  var sonuc = document.getElementById("sonuc");
  if (!dugme || !sonuc) return;

  var gosterildi = false;

  function kutuKur() {
    if (gosterildi) return;
    var metin = (sonuc.textContent || "").trim();
    if (!metin || sonuc.classList.contains("hata")) return;
    gosterildi = true;
    var kutu = document.createElement("div");
    kutu.className = "geri-bildirim";
    var soru = document.createElement("span");
    soru.textContent = "Bu araç işinize yaradı mı?";
    kutu.appendChild(soru);
    ["1", "-1"].forEach(function (deger) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = deger === "1" ? "👍 Evet" : "👎 Hayır";
      b.addEventListener("click", function () {
        gonder("/api/oy", { yol: location.pathname, oy: parseInt(deger, 10) });
        kutu.textContent = "Geri bildiriminiz için teşekkürler.";
      });
      kutu.appendChild(b);
    });
    sonuc.parentNode.appendChild(kutu);
  }

  dugme.addEventListener("click", function () {
    setTimeout(kutuKur, 600);
  });
})();
