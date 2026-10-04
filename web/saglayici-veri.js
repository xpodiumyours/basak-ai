/* web/saglayici-veri.js — sağlayici veri saklama tablosunu gosterir.
   YALNIZ SEFFAFLIK: hicbir karar vermez, hicbir yonlendirme yapmaz.
   Sunucu /api/saglayici-veri ucundan (brain/registry.py) okur.
   Tablo satirlari sunucu HTML'inde hazir durur (JS gerekmez); betik
   yalnizca canli veriyle tazeler. Uc bulunamazsa statik tablo oldugu
   gibi kalir. */
(function () {
  "use strict";

  var ETIKET = {
    "kaydetmez": "Saklamadığını resmen bildiriyor",
    "kaydeder": "Saklayabilir",
    "egitime_kullanilir": "Eğitim/model geliştirme için kullanabilir",
    // Iddia yok: dogruyu da yalani da soylemeyiz. Kullaniciya
    // "tahmin yok, guvenli tarafi dusun" diyoruz.
    "dogrulanmadi": "Doğrulanmadı — iddia yok"
  };

  function hucre(metin) {
    var td = document.createElement("td");
    td.textContent = metin;
    return td;
  }

  fetch("/api/saglayici-veri", { credentials: "omit" })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (v) {
      var liste = (v && v.saglayicilar) || [];
      if (!liste.length) throw new Error("bos");
      var govde = document.querySelector("#saglayici-tablosu tbody");
      // Statik satirlari canli veriyle DEGISTIR: ucten gelen liste
      // ayni kaynaktan gelir; ustune ekleme yapilirsa satirlar iki
      // kez gorunur.
      govde.textContent = "";
      liste.forEach(function (s) {
        var tr = document.createElement("tr");
        tr.appendChild(hucre(s.ad_guncel || s.ad));
        tr.appendChild(hucre(ETIKET[s.durum] || s.aciklama || s.durum));
        tr.appendChild(hucre(s.kaynak || "—"));
        govde.appendChild(tr);
      });
      document.getElementById("saglayici-tablosu").hidden = false;
    })
    .catch(function () {
      // Yenileme olmadi: sunucu HTML'indeki statik tablo oldugu gibi
      // gorunur; ayrica gosterilecek hata metnine gerek yoktur.
    });
})();
