/* web/eklenti-kart.js — sohbet ekranındaki tarayıcı eklentisi kartı.
 *
 * Neden ayrı dosya: kart yalnız ARAYÜZ. Model çağırmaz, sunucuya istek
 * atmaz, kullanıcı metnini yorumlamaz. Tek işi var: bu tarayıcıda eklenti
 * kurulu mu (sinyal görüntüsü yüklenebiliyor mu), kullanıcıya kimlikli
 * kurulum adımlarını göstermek ve kartı o kullanıcı için hatırlamak.
 *
 * Telefon/tablet kuralı: eklenti oraya KURULAMAZ (chrome://extensions
 * mobilde yok, araç çubuğu simgesi yok). Uygulanamaz kurulum adımı
 * göstermek yalan olur; kart buralarda hiç görünmez.
 *
 * Durum neden istemcide: eklentinin bağlantısı sunucuda tek instance'a
 * çivilenir; web isteği onu göremez. "Kurulu mu" sorusunun tek güvenilir
 * cevabı tarayıcının kendisindedir.
 *
 * Gizlilik: sinyal yalnız Başak'ın kendi adreslerine açıktır
 * (manifest → web_accessible_resources). Başka siteler eklentiyi göremez.
 */
(function () {
  "use strict";

  // Sabit eklenti kimliği manifest'teki "key" alanından türetilir; böylece
  // her makinede aynıdır (paketlenmemiş kurulumda da kimlik değişmez).
  var EKLENTI_ID = "dpldleggjfdcmddkmmfdijbbojgedmoj";
  var SINYAL = "chrome-extension://" + EKLENTI_ID + "/sinyal.png";
  var KART_ANAHTARI = "basak_eklenti_kart_v1";
  var DENEME_MS = 1500;

  var kart = document.getElementById("eklentiKarti");
  if (!kart) return;

  var durumEl = document.getElementById("eklentiDurum");
  var noktaEl = document.getElementById("eklentiNokta");
  var kimlikEl = document.getElementById("eklentiKimlik");
  var kapatEl = document.getElementById("eklentiKapat");
  var adimlarEl = document.getElementById("eklentiAdimlar");

  function kimlik() {
    var k = window.basakKimlik || {};
    return {
      id: String(k.kullanici || "").trim(),
      gorunen: String(k.basak_id || "").trim()
    };
  }

  // Kurulum adımları yalnız masaüstü tarayıcıda uygulanabilir. Chromium,
  // "mobile" sinyalini kendisi söyler (userAgentData); söylenmiyorsa
  // tarayıcı kimliğinden okunur. iPadOS masaüstü kimliği söyler; o yüzden
  // dokunmatik Mac de mobil sayılır.
  function kurulumMumkunMu() {
    try {
      var uad = navigator.userAgentData;
      if (uad && typeof uad.mobile === "boolean") return !uad.mobile;
    } catch (hata) {
      /* sinyal yoksa tarayıcı kimliğinden devam */
    }
    var ua = navigator.userAgent || "";
    if (/Mobi|Android|iPhone|iPod|iPad|Windows Phone/i.test(ua)) return false;
    if (/Macintosh/.test(ua) && (navigator.maxTouchPoints || 0) > 1) {
      return false;
    }
    return true;
  }

  function depoAnahtari() {
    var kid = kimlik().id;
    return KART_ANAHTARI + ":" + (kid || "misafir");
  }

  function kapaliMi() {
    try {
      return localStorage.getItem(depoAnahtari()) === "kapali";
    } catch (hata) {
      return false;
    }
  }

  function durumYaz(tur) {
    kart.hidden = false;
    noktaEl.className = "eklenti-nokta " + tur;
    if (tur === "kurulu") {
      durumEl.textContent =
        "Bu tarayıcıda kurulu görünüyor. Araç çubuğundaki Başak simgesine " +
        "basınca panel açılır ve bağlantı kendiliğinden kurulur; her tıklama " +
        "senden onay ister.";
      if (adimlarEl) adimlarEl.hidden = true;
    } else if (tur === "yok") {
      durumEl.textContent =
        "Bu tarayıcıda kurulu görünmüyor. Sayfayla ilgili işler için üç " +
        "adım yeterli:";
      if (adimlarEl) adimlarEl.hidden = false;
    } else {
      durumEl.textContent =
        "Tarayıcı eklenti durumunu bildirmedi. Kuruluysa Başak simgesine " +
        "bas; değilse üç adım:";
      if (adimlarEl) adimlarEl.hidden = false;
    }
  }

  function kimlikYaz() {
    if (!kimlikEl) return;
    var g = kimlik().gorunen;
    kimlikEl.textContent = g
      ? "Bu kart yalnız bu tarayıcıdaki kimliğine özel · Başak ID " + g
      : "Bu kart yalnız bu tarayıcıya özel";
  }

  function dene() {
    return new Promise(function (coz) {
      var bitti = false;
      var goruntu = new Image();
      var zaman = setTimeout(function () {
        if (bitti) return;
        bitti = true;
        coz("bilinmiyor");
      }, DENEME_MS);
      goruntu.onload = function () {
        if (bitti) return;
        bitti = true;
        clearTimeout(zaman);
        coz("kurulu");
      };
      goruntu.onerror = function () {
        if (bitti) return;
        bitti = true;
        clearTimeout(zaman);
        coz("yok");
      };
      goruntu.src = SINYAL;
    });
  }

  function tazele() {
    if (!kurulumMumkunMu() || kapaliMi()) {
      kart.hidden = true;
      return;
    }
    kimlikYaz();
    durumYaz("bilinmiyor");
    dene().then(function (tur) {
      if (kapaliMi()) return;
      durumYaz(tur);
    });
  }

  if (kapatEl) {
    kapatEl.addEventListener("click", function () {
      try {
        localStorage.setItem(depoAnahtari(), "kapali");
      } catch (hata) {
        /* depo yoksa kart bu oturumda gizlenir, kalıcı olmaz */
      }
      kart.hidden = true;
    });
  }

  window.addEventListener("basak:kimlik", function () {
    tazele();
  });
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) tazele();
  });

  tazele();
})();
