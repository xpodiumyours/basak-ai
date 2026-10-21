/* eklenti/icerik.js — sayfayı Başak'ın göreceği gözleme çevirir.
 *
 * Sözleşme (tools/tarayici_goz.py ile aynı):
 *   {url, baslik, ogeler: [{rol, ad, deger, gorunur, kapali}]}
 *
 * Kurallar:
 * - Gizli öğe gönderilmez: kullanıcının görmediği şeye basılamaz.
 * - Şifre alanının DEĞERİ asla okunmaz (yalnız alanın kendisi görünür).
 * - Rolü tanınmayan öğe silinmez; "diger" olarak korunur (sessiz kayıp yok).
 * - Site adı, alan adı, kelime listesi yok: her sayfada aynı kod çalışır.
 */
(function (kok) {
  "use strict";
  if (kok.__basakGozlem) return;

  var ETIKET_TAVANI = 500;
  var METIN_TAVANI = 2000;

  // Kalıcı öğe kimliği: her öğe sayfa ömrü boyunca AYNI numarayı taşır.
  // Çekirdek ref'i "<nesil>-<kimlik>" olur ve eylemde kimliği geri yollar;
  // böylece gözlem listesindeki süzülmüş sıra kayması eylemi kaydırmaz.
  var kimlikSayaci = 0;
  var kimlikler = new WeakMap();
  var ters = {};            // kimlik -> öğe (her gözlemde tazelenir)
  var sonUrl = "";          // son gözlemin adresi: sayfa değiştiyse eylem yok

  function kimlikAl(el) {
    var k = kimlikler.get(el);
    if (!k) {
      kimlikSayaci += 1;
      k = kimlikSayaci;
      kimlikler.set(el, k);
    }
    return k;
  }

  var SECICI = [
    "a[href]", "button", "input", "select", "textarea",
    "[contenteditable='true']", "[role]",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "li", "td", "th", "label", "blockquote", "pre", "figcaption",
    "img[alt]"
  ].join(",");

  function temiz(deger, tavan) {
    var metin = String(deger == null ? "" : deger).replace(/\s+/g, " ").trim();
    return metin.length > tavan ? metin.slice(0, tavan) : metin;
  }

  function gorunurMu(el) {
    if (!el || el.nodeType !== 1) return false;
    // Atalar da denetlenir: display:none bir kapsayıcının içindeki düğme
    // kendi stilinde görünür görünür ama ekranda YOKTUR.
    var dugum = el;
    while (dugum && dugum.nodeType === 1) {
      if (dugum.hidden) return false;
      if (dugum.getAttribute && dugum.getAttribute("aria-hidden") === "true") {
        return false;
      }
      var ataStil = kok.getComputedStyle ? kok.getComputedStyle(dugum) : null;
      if (ataStil) {
        if (ataStil.display === "none" || ataStil.visibility === "hidden") {
          return false;
        }
        if (ataStil.opacity === "0") return false;
      }
      dugum = dugum.parentElement;
    }
    if (typeof el.getBoundingClientRect === "function") {
      var kutu = el.getBoundingClientRect();
      // Kutu tamamen sıfırsa yerleşim bilgisi yok (ör. test ortamı):
      // gizli saymayız, yoksa her öğe düşerdi.
      if ((kutu.width || kutu.height) && (kutu.width < 2 || kutu.height < 2)) {
        return false;
      }
    }
    return true;
  }

  function rolBul(el) {
    var rol = el.getAttribute && el.getAttribute("role");
    if (rol) {
      var r = rol.toLowerCase();
      if (r === "button" || r === "link" || r === "textbox" ||
          r === "combobox" || r === "checkbox" || r === "radio" ||
          r === "heading" || r === "tab" || r === "menuitem") {
        return r;
      }
      return "diger";
    }
    var etiket = el.tagName ? el.tagName.toLowerCase() : "";
    if (etiket === "a") return "link";
    if (etiket === "button") return "button";
    if (etiket === "select") return "combobox";
    if (etiket === "textarea") return "textbox";
    if (etiket === "img") return "img";
    if (/^h[1-6]$/.test(etiket)) return "heading";
    if (etiket === "input") {
      var tip = (el.getAttribute("type") || "text").toLowerCase();
      if (tip === "checkbox" || tip === "radio") return tip;
      if (tip === "submit" || tip === "button" || tip === "reset") return "button";
      if (tip === "hidden") return "gizli";
      return "textbox";
    }
    if (etiket === "p" || etiket === "li" || etiket === "td" ||
        etiket === "th" || etiket === "label" || etiket === "pre" ||
        etiket === "blockquote" || etiket === "figcaption") {
      return "metin";
    }
    return "diger";
  }

  function adBul(el) {
    var adaylar = [];
    if (el.getAttribute) {
      adaylar.push(el.getAttribute("aria-label"));
      adaylar.push(el.getAttribute("placeholder"));
      adaylar.push(el.getAttribute("title"));
      adaylar.push(el.getAttribute("alt"));
    }
    if (el.labels && el.labels.length) {
      adaylar.push(el.labels[0].textContent);
    }
    if (el.id && kok.document && kok.document.querySelector) {
      var bagli = kok.document.querySelector('[for="' + el.id + '"]');
      if (bagli) adaylar.push(bagli.textContent);
    }
    // Form alanının "içeriği" etiket değildir: select'in içindeki seçenek
    // metni adı sanılırsa alan yanlış tanıtılır ("Ankara" adlı kutu olmaz).
    var etiketAdi = el.tagName ? el.tagName.toLowerCase() : "";
    if (etiketAdi !== "input" && etiketAdi !== "select" &&
        etiketAdi !== "textarea") {
      adaylar.push(el.textContent);
    }
    for (var i = 0; i < adaylar.length; i++) {
      var temizAd = temiz(adaylar[i], ETIKET_TAVANI);
      if (temizAd) return temizAd;
    }
    return "";
  }

  function degerBul(el, rol) {
    var etiket = el.tagName ? el.tagName.toLowerCase() : "";
    if (rol === "checkbox" || rol === "radio") {
      return el.checked ? "true" : "false";
    }
    if (etiket === "input" || etiket === "textarea" || etiket === "select") {
      var tip = (el.getAttribute("type") || "").toLowerCase();
      // Şifre ve dosya alanının değeri DIŞARI ÇIKMAZ.
      if (tip === "password" || tip === "file") return "";
      return temiz(el.value, ETIKET_TAVANI);
    }
    if (el.isContentEditable) return temiz(el.textContent, ETIKET_TAVANI);
    return "";
  }

  function gozlemCikar() {
    var liste = [];
    ters = {};
    sonUrl = String(kok.location ? kok.location.href : "");
    var dugumler = kok.document.querySelectorAll(SECICI);
    for (var i = 0; i < dugumler.length; i++) {
      var el = dugumler[i];
      if (!gorunurMu(el)) continue;
      var rol = rolBul(el);
      if (rol === "gizli") continue;
      var ad = adBul(el);
      var deger = degerBul(el, rol);
      // Etkileşimli öğe adsız olsa da korunur: boş bir kutu da kullanıcının
      // doldurabileceği bir alandır, sessizce düşürülmez. Yalnız içi boş
      // metin blokları atılır.
      var etkilesimli = rol === "button" || rol === "link" ||
        rol === "textbox" || rol === "combobox" || rol === "checkbox" ||
        rol === "radio" || rol === "tab" || rol === "menuitem";
      if (!ad && !deger && !etkilesimli) continue;
      if (ad.length > METIN_TAVANI) ad = ad.slice(0, METIN_TAVANI);
      var kimlik = kimlikAl(el);
      ters[kimlik] = el;
      liste.push({
        sira: kimlik,
        rol: rol,
        ad: ad,
        deger: deger,
        gorunur: true,
        kapali: !!(el.disabled || el.getAttribute("aria-disabled") === "true")
      });
    }
    return {
      url: sonUrl,
      baslik: String(kok.document.title || ""),
      ogeler: liste
    };
  }

  /* ── Eylem: tıklama ve yazma ────────────────────────────────────────
   * Kural: gözlemde görünmeyen, kopmuş ya da kapalı öğeye eylem yok.
   * Şifre ve dosya alanına YAZILMAZ: sır ekranda kalır, akışa girmez.
   */

  function ogeBul(sira) {
    var el = ters[sira];
    if (!el) return null;
    if (el.isConnected === false) return null;
    if (!gorunurMu(el)) return null;
    return el;
  }

  function eylemHatasi(mesaj) {
    return { hata: mesaj };
  }

  function tikla(sira) {
    if (!sira) return eylemHatasi("gecersiz oge kimligi");
    var el = ogeBul(sira);
    if (!el) {
      return eylemHatasi("Oge bulunamadi ya da sayfa degisti; " +
                         "sayfaya yeniden bakilmali.");
    }
    if (el.disabled || el.getAttribute("aria-disabled") === "true") {
      return eylemHatasi("Oge kapali (disabled); tiklanamaz.");
    }
    if (kok.location && String(kok.location.href) !== sonUrl) {
      return eylemHatasi("Sayfa adresi degisti; yeniden bakilmali.");
    }
    if (typeof el.scrollIntoView === "function") {
      try { el.scrollIntoView({ block: "center", inline: "center" }); }
      catch (hata) { /* yerleşimi olmayan ortam: zararsız */ }
    }
    try { if (el.focus) el.focus(); } catch (hata) { /* odak zorunlu değil */ }
    el.click();
    return { sonuc: {
      yapildi: "tikla",
      sira: sira,
      rol: rolBul(el),
      ad: adBul(el),
      url: String(kok.location ? kok.location.href : ""),
      baslik: String(kok.document.title || "")
    } };
  }

  function duzenlenebilirMi(el) {
    if (el.isContentEditable) return true;
    var deger = el.getAttribute && el.getAttribute("contenteditable");
    return deger === "" || deger === "true" || deger === "plaintext-only";
  }

  function degerYaz(el, metin) {
    var etiket = el.tagName ? el.tagName.toLowerCase() : "";
    var proto = null;
    if (etiket === "textarea") proto = kok.HTMLTextAreaElement && kok.HTMLTextAreaElement.prototype;
    else if (etiket === "select") proto = kok.HTMLSelectElement && kok.HTMLSelectElement.prototype;
    else if (etiket === "input") proto = kok.HTMLInputElement && kok.HTMLInputElement.prototype;
    // React/Vue kendi value izleyicisini kurar: alanın yerel setter'ı
    // üzerinden yazılmazsa çerçeve değişikliği görmez.
    var tanim = proto && Object.getOwnPropertyDescriptor(proto, "value");
    if (tanim && tanim.set) tanim.set.call(el, metin);
    else el.value = metin;
    el.dispatchEvent(new kok.Event("input", { bubbles: true }));
    el.dispatchEvent(new kok.Event("change", { bubbles: true }));
  }

  function yaz(sira, metin) {
    if (!sira) return eylemHatasi("gecersiz oge kimligi");
    var el = ogeBul(sira);
    if (!el) {
      return eylemHatasi("Oge bulunamadi ya da sayfa degisti; " +
                         "sayfaya yeniden bakilmali.");
    }
    if (el.disabled || el.readOnly || el.getAttribute("aria-disabled") === "true") {
      return eylemHatasi("Oge yazmaya kapali (disabled/readonly).");
    }
    if (kok.location && String(kok.location.href) !== sonUrl) {
      return eylemHatasi("Sayfa adresi degisti; yeniden bakilmali.");
    }
    var etiket = el.tagName ? el.tagName.toLowerCase() : "";
    var tip = (el.getAttribute && (el.getAttribute("type") || "")).toLowerCase();
    if (tip === "password") {
      return eylemHatasi("Sifre alanina yazilmaz (sir ekranda kalir).");
    }
    if (tip === "file") {
      return eylemHatasi("Dosya secimi alanina metin yazilamaz.");
    }
    var yazilabilir = etiket === "input" || etiket === "textarea" ||
      etiket === "select" || duzenlenebilirMi(el);
    if (!yazilabilir) {
      return eylemHatasi("Oge yazilabilir alan degil (" + (etiket || "?") + ").");
    }
    try { if (el.focus) el.focus(); } catch (hata) { /* odak zorunlu değil */ }
    if (duzenlenebilirMi(el) && etiket !== "input" && etiket !== "textarea") {
      el.textContent = String(metin);
      el.dispatchEvent(new kok.Event("input", { bubbles: true }));
    } else {
      degerYaz(el, String(metin));
    }
    return { sonuc: {
      yapildi: "yaz",
      sira: sira,
      rol: rolBul(el),
      ad: adBul(el),
      uzunluk: String(metin).length,
      url: String(kok.location ? kok.location.href : "")
    } };
  }

  kok.__basakGozlem = gozlemCikar;
  kok.__basakTikla = tikla;
  kok.__basakYaz = yaz;

  if (kok.chrome && kok.chrome.runtime && kok.chrome.runtime.onMessage) {
    kok.chrome.runtime.onMessage.addListener(function (mesaj, _gonderen, yanitla) {
      if (!mesaj || !mesaj.tip) return undefined;
      try {
        if (mesaj.tip === "gozlem") { yanitla(gozlemCikar()); return true; }
        if (mesaj.tip === "tikla") { yanitla(tikla(Number(mesaj.sira))); return true; }
        if (mesaj.tip === "yaz") {
          yanitla(yaz(Number(mesaj.sira), mesaj.metin == null ? "" : mesaj.metin));
          return true;
        }
      } catch (hata) {
        yanitla({ hata: "sayfa islemi basarisiz: " + String(hata) });
        return true;
      }
      return undefined;
    });
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
