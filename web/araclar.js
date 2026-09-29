/* web/araclar.js — /araclar sayfalarinin tarayici ici kismi (Faz 3).
 *
 * Iki is var burada:
 * 1) Araclari ZIYARETCININ tarayicisinda hesaplamak: girdi sunucuya gitmez,
 *    sonuc aninda cikar (MIMARI ilke 5). Algoritmalar standarttir
 *    (WebCrypto, base64, BigInt); freetools.org kodu buraya kopyalanmaz.
 * 2) Cerez onayi: onay VERILMEDEN reklam kodu hic yuklenmez. Reklam
 *    adresi sabit bir metin olarak dosyada DEGIL, sayfadaki meta
 *    etiketinden okunur — yani onaysiz hicbir ucuncu taraf cagri olmaz.
 */
(function () {
  "use strict";

  var slug = window.ARAC_SLUG || "";
  var sonucEl = document.getElementById("sonuc");
  var dugme = document.getElementById("hesapla");

  function girdiAl() {
    var liste = [], i = 0;
    while (document.getElementById("g" + i)) {
      liste.push(document.getElementById("g" + i).value);
      i++;
    }
    return liste;
  }

  function goster(metin, hata) {
    if (!sonucEl) return;
    sonucEl.textContent = metin;
    sonucEl.classList.toggle("hata", !!hata);
  }

  function ondalik(d) {
    // 1.0000000000000002 gibi kaymalari temizler.
    var s = Number(d);
    if (!isFinite(s)) return String(d);
    return String(parseFloat(s.toPrecision(12)));
  }

  function sayi(metin, etiket) {
    var s = String(metin || "").trim().replace(",", ".");
    if (!s || isNaN(Number(s))) throw new Error(etiket + " bir sayi olmali");
    return Number(s);
  }

  function base64Coz(metin) {
    var ham = String(metin || "").trim().replace(/\s+/g, "");
    if (!ham || !/^[A-Za-z0-9+/]+={0,2}$/.test(ham)) {
      throw new Error("Gecersiz Base64 metni");
    }
    var bayt;
    try { bayt = atob(ham); } catch (e) {
      throw new Error("Gecersiz Base64 metni");
    }
    var u8 = new Uint8Array(bayt.length);
    for (var i = 0; i < bayt.length; i++) u8[i] = bayt.charCodeAt(i);
    try {
      return new TextDecoder("utf-8", { fatal: true }).decode(u8);
    } catch (e) {
      throw new Error("Cozulen veri UTF-8 metni degil");
    }
  }

  function base64Kodla(metin) {
    return btoa(unescape(encodeURIComponent(String(metin || ""))));
  }

  async function sha(metin, alg) {
    if (!window.crypto || !crypto.subtle) {
      throw new Error("Tarayiciniz WebCrypto yapamiyor; sohbette deneyin");
    }
    var harita = {
      "sha1": "SHA-1", "sha-1": "SHA-1",
      "sha256": "SHA-256", "sha-256": "SHA-256",
      "sha384": "SHA-384", "sha-384": "SHA-384",
      "sha512": "SHA-512", "sha-512": "SHA-512",
    };
    var ad = harita[String(alg || "sha256").trim().toLowerCase()];
    if (!ad) {
      throw new Error("Desteklenen algoritmalar: sha256, sha1, sha384, " +
                      "sha512 (md5 tarayicinin sifreleme arayuzunde yok)");
    }
    var veri = new TextEncoder().encode(String(metin || ""));
    var ozet = await crypto.subtle.digest(ad, veri);
    return Array.prototype.map.call(new Uint8Array(ozet), function (b) {
      return b.toString(16).padStart(2, "0");
    }).join("");
  }

  var HESAPLAR = {
    "sha-hash-generator": function (d) { return sha(d[0], d[1]); },

    "base64-encode-decode": function (d) {
      var coz = /decode|coz|çöz/i.test(d[1] || "");
      return coz ? base64Coz(d[0]) : base64Kodla(d[0]);
    },

    "base64-decoder": function (d) { return base64Coz(d[0]); },

    "url-encode-decode": function (d) {
      var coz = /decode|coz|çöz/i.test(d[1] || "");
      if (!coz) return encodeURIComponent(d[0] || "");
      try { return decodeURIComponent(d[0] || ""); }
      catch (e) { throw new Error("Gecersiz yüzde kodlamasi"); }
    },

    "percentage-calculator": function (d) {
      return ondalik(sayi(d[0], "Birinci deger") *
                     sayi(d[1], "Ikinci deger") / 100);
    },

    "letter-counter": function (d) {
      var m = d[0] || "";
      var harf = (m.match(/[\p{L}]/gu) || []).length;
      var rakam = (m.match(/\d/g) || []).length;
      return [
        "Karakter (bosluklu): " + m.length,
        "Karakter (bosluksuz): " + m.replace(/\s/g, "").length,
        "Kelime: " + (m.trim() ? m.trim().split(/\s+/).length : 0),
        "Harf: " + harf,
        "Rakam: " + rakam,
        "Satir: " + (m ? m.split(/\r\n|\r|\n/).length : 0),
      ].join("\n");
    },

    "reverse-text": function (d) {
      return Array.from(d[0] || "").reverse().join("");
    },

    "binary-hex-converter": function (d) {
      var t = String(d[0] || "").trim().toLowerCase();
      if (t.indexOf("0x") === 0) t = t.slice(2);
      if (!t) throw new Error("Sayi bos olamaz");
      if (/^[01]+$/.test(t)) {
        if (t.length > 4096) throw new Error("Cok uzun ikili sayi");
        return "0x" + BigInt("0b" + t).toString(16);
      }
      if (/^[0-9a-f]+$/.test(t)) {
        var ikili = BigInt("0x" + t).toString(2);
        var gruplar = [];
        while (ikili.length % 4 !== 0) ikili = "0" + ikili;
        for (var i = 0; i < ikili.length; i += 4) {
          gruplar.push(ikili.slice(i, i + 4));
        }
        return gruplar.join(" ");
      }
      throw new Error("Yalnizca 0/1 ikilisi veya hex rakamlari girin");
    },

    "hexadecimal-to-decimal-converter": function (d) {
      var t = String(d[0] || "").trim().toLowerCase();
      if (t.indexOf("0x") === 0) t = t.slice(2);
      if (!/^[0-9a-f]+$/.test(t)) {
        throw new Error("Gecersiz hex sayi (ornek: ff)");
      }
      return BigInt("0x" + t).toString(10);
    },

    "case-converter": function (d) {
      var m = String(d[0] || "");
      var kip = String(d[1] || "").trim().toLowerCase();
      if (!kip) {
        return [
          "BÜYÜK: " + m.toLocaleUpperCase("tr"),
          "küçük: " + m.toLocaleLowerCase("tr"),
          "Başlık: " + m.toLocaleLowerCase("tr").replace(/(^|\s)\S/g, function (h) {
            return h.toLocaleUpperCase("tr");
          }),
        ].join("\n");
      }
      if (/^(upper|buyuk|büyük)$/.test(kip)) return m.toLocaleUpperCase("tr");
      if (/^(lower|kucuk|küçük)$/.test(kip)) return m.toLocaleLowerCase("tr");
      if (/^(title|baslik|başlık)$/.test(kip)) {
        return m.toLocaleLowerCase("tr").replace(/(^|\s)\S/g, function (h) {
          return h.toLocaleUpperCase("tr");
        });
      }
      if (/^(capitalize|cumle|cümle)$/.test(kip)) {
        var k = m.toLocaleLowerCase("tr");
        return k.charAt(0).toLocaleUpperCase("tr") + k.slice(1);
      }
      throw new Error("Bilinmeyen kip (upper, lower, title)");
    },

    "text-binary": function (d) {
      var m = String(d[0] || "");
      var coz = /decode|coz|çöz/i.test(d[1] || "");
      if (!coz) {
        var veri = new TextEncoder().encode(m);
        var blok = [];
        for (var i = 0; i < veri.length; i++) {
          blok.push(veri[i].toString(2).padStart(8, "0"));
        }
        if (!blok.length) throw new Error("Metin bos olamaz");
        return blok.join(" ");
      }
      var parcalar = m.trim().split(/\s+/);
      if (!parcalar.length || !parcalar[0]) throw new Error("Ikili metin bos olamaz");
      var bayt = parcalar.map(function (p) {
        if (!/^[01]{8}$/.test(p)) throw new Error("Her blok 8 bit 0/1 olmali");
        return parseInt(p, 2);
      });
      try {
        return new TextDecoder("utf-8", { fatal: true }).decode(new Uint8Array(bayt));
      } catch (e) {
        throw new Error("Cozulen veri UTF-8 metni degil");
      }
    },

    "text-ascii": function (d) {
      var m = String(d[0] || "");
      var coz = /decode|coz|çöz/i.test(d[1] || "");
      if (!coz) {
        var veri = new TextEncoder().encode(m);
        var kod = [];
        for (var i = 0; i < veri.length; i++) kod.push(String(veri[i]));
        if (!kod.length) throw new Error("Metin bos olamaz");
        return kod.join(" ");
      }
      var parcalar = m.trim().split(/[\s,]+/);
      if (!parcalar.length || !parcalar[0]) throw new Error("Kod listesi bos olamaz");
      var bayt = parcalar.map(function (p) {
        if (!/^\d{1,3}$/.test(p) || Number(p) > 255) {
          throw new Error("Her kod 0-255 arasi sayi olmali");
        }
        return Number(p);
      });
      try {
        return new TextDecoder("utf-8", { fatal: true }).decode(new Uint8Array(bayt));
      } catch (e) {
        throw new Error("Cozulen veri UTF-8 metni degil");
      }
    },

    "remove-empty-lines": function (d) {
      var satir = String(d[0] || "").split(/\r\n|\r|\n/);
      var dolu = satir.filter(function (s) { return s.trim(); });
      if (!dolu.length) throw new Error("Temizlenecek dolu satir yok");
      return dolu.join("\n");
    },

    "line-break-remover": function (d) {
      var birlesik = String(d[0] || "").replace(/\s+/g, " ").trim();
      if (!birlesik) throw new Error("Birlestirilecek metin yok");
      return birlesik;
    },

    "character-remover": function (d) {
      var m = String(d[0] || "");
      var sil = String(d[1] || "");
      if (!m) throw new Error("Metin bos olamaz");
      if (!sil) {
        var temiz = m.replace(/[!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~]/g, "");
        if (!temiz) throw new Error("Temizlenecek noktalama yok");
        return temiz;
      }
      var kume = {};
      for (var i = 0; i < sil.length; i++) kume[sil[i]] = true;
      var cikti = "";
      for (var j = 0; j < m.length; j++) {
        if (!kume[m[j]]) cikti += m[j];
      }
      return cikti;
    },

    "character-replacer": function (d) {
      var m = String(d[0] || "");
      var kural = String(d[1] || "").trim();
      if (!m) throw new Error("Metin bos olamaz");
      if (!kural) throw new Error("Degisim kurali bos olamaz (ornek: a>e)");
      var cikti = m;
      var adimlar = kural.split("|");
      for (var i = 0; i < adimlar.length; i++) {
        var parca = adimlar[i].split(">");
        if (parca.length !== 2 || !parca[0]) {
          throw new Error("Gecersiz kural: '" + adimlar[i] + "' (ornek: a>e)");
        }
        cikti = cikti.split(parca[0]).join(parca[1]);
      }
      return cikti;
    },

    "tabs-to-space": function (d) {
      var m = String(d[0] || "");
      var adet = String(d[1] || "").trim();
      if (!m) throw new Error("Metin bos olamaz");
      var n = adet ? Number(adet) : 4;
      if (!isFinite(n) || Math.floor(n) !== n || n < 1 || n > 16) {
        throw new Error("Bosluk sayisi 1-16 arasi tam sayi olmali");
      }
      if (m.indexOf("\t") === -1) throw new Error("Metinde sekme yok");
      var bos = "";
      for (var i = 0; i < n; i++) bos += " ";
      return m.split("\t").join(bos);
    },

    "text-splitter": function (d) {
      var m = String(d[0] || "");
      var ayrac = String(d[1] || "").trim().toLowerCase();
      if (!m) throw new Error("Metin bos olamaz");
      var parcalar;
      if (!ayrac) {
        parcalar = m.split(/\r\n|\r|\n/);
      } else if (/^(kelime|word)$/.test(ayrac)) {
        parcalar = m.trim().split(/\s+/);
      } else if (/^(cumle|cümle|sentence)$/.test(ayrac)) {
        parcalar = m.match(/[^.!?…]+[.!?…]+["»”']?|\s*[^.!?…]+$/g) || [];
        parcalar = parcalar.map(function (p) { return p.trim(); })
          .filter(function (p) { return p; });
      } else {
        parcalar = m.split(ayrac);
      }
      if (!parcalar.length || (parcalar.length === 1 && !parcalar[0])) {
        throw new Error("Bolunecek parca yok");
      }
      return parcalar.map(function (p, i) { return (i + 1) + ". " + p; })
        .join("\n");
    },

    "space-remover": function (d) {
      var m = String(d[0] || "");
      if (!m.trim()) throw new Error("Metin bos olamaz");
      return m.split(/\r\n|\r|\n/).map(function (s) {
        return s.trim().replace(/[ \t]+/g, " ");
      }).join("\n");
    },

    "comma-inserter": function (d) {
      var m = String(d[0] || "");
      var ayrac = String(d[1] || "").trim() || ",";
      if (!m.trim()) throw new Error("Liste bos olamaz");
      var ogeler = m.split(/\r\n|\r|\n/).map(function (s) { return s.trim(); })
        .filter(function (s) { return s; });
      if (ogeler.length <= 1) {
        ogeler = m.trim().split(/\s+/).filter(function (s) { return s; });
      }
      if (!ogeler.length) throw new Error("Birlestirilecek oge yok");
      return ogeler.join(ayrac + " ");
    },

    "json-formatter": function (d) {
      var m = String(d[0] || "");
      var girinti = String(d[1] || "").trim();
      if (!m.trim()) throw new Error("JSON metni bos olamaz");
      var n = girinti ? Number(girinti) : 2;
      if (!isFinite(n) || Math.floor(n) !== n || n < 0 || n > 8) {
        throw new Error("Girinti 0-8 arasi tam sayi olmali");
      }
      var veri;
      try { veri = JSON.parse(m); }
      catch (e) { throw new Error("Gecersiz JSON: " + (e.message || "cozumlenemedi")); }
      if (veri === undefined) throw new Error("Gecersiz JSON");
      return JSON.stringify(veri, null, n);
    },

    "html-entities": function (d) {
      var m = String(d[0] || "");
      var coz = /decode|coz|çöz/i.test(d[1] || "");
      if (!m) throw new Error("Metin bos olamaz");
      if (!coz) {
        return m.replace(/&/g, "&amp;").replace(/</g, "&lt;")
          .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");
      }
      var cikti = m.replace(/&(amp|lt|gt|quot|#39|#x27|#34|#60|#62|#38);/g,
        function (eslesme, ad) {
          var harita = {
            amp: "&", lt: "<", gt: ">", quot: '"', "#39": "'",
            "#x27": "'", "#34": '"', "#60": "<", "#62": ">", "#38": "&",
          };
          return harita[ad] || eslesme;
        });
      var kalan = cikti.match(/&#[0-9]+;|&#x[0-9a-fA-F]+;/g) || [];
      for (var i = 0; i < kalan.length; i++) {
        var kod = kalan[i].toLowerCase().indexOf("&#x") === 0
          ? parseInt(kalan[i].slice(3, -1), 16)
          : parseInt(kalan[i].slice(2, -1), 10);
        if (isFinite(kod) && kod >= 0 && kod <= 0x10FFFF) {
          cikti = cikti.split(kalan[i]).join(String.fromCodePoint(kod));
        }
      }
      return cikti;
    },
  };

  if (dugme) {
    dugme.addEventListener("click", function () {
      var hesap = HESAPLAR[slug];
      if (!hesap) {
        goster("Bu aracin tarayici surumu yok; sohbette deneyin.", true);
        return;
      }
      goster("Hesaplanıyor…");
      Promise.resolve()
        .then(function () { return hesap(girdiAl()); })
        .then(function (sonuc) { goster(String(sonuc)); })
        .catch(function (e) {
          goster((e && e.message) || "Hesaplanamadi", true);
        });
    });
  }

  // ── Çerez onayı: onaydan önce reklam kodu yüklenmez ───────────────
  // Yanlışlıkla bile reklam gibi görünmemek için: meta reklam-yerlesimi
  // boşsa alan "Reklam alanı" yazısıyla BOS kalır; kod YOK, istek YOK.
  var ANAHTAR = "basak_cerez_onay_v1";

  function onayOku() {
    try { return JSON.parse(localStorage.getItem(ANAHTAR) || "null"); }
    catch (e) { return null; }
  }

  function onayYaz(deger) {
    try { localStorage.setItem(ANAHTAR, JSON.stringify(deger)); }
    catch (e) { /* gizli modda saklayamazsa onaysiz devam eder */ }
  }

  function reklamYerlesim() {
    var alan = document.getElementById("reklamAlani");
    if (!alan) return;
    var onay = onayOku();
    if (!onay || !onay.reklam) { alan.hidden = true; return; }
    alan.hidden = false;
    var meta = document.querySelector('meta[name="reklam-yerlesimi"]');
    if (!meta || !meta.content) {
      alan.textContent = "Reklam alanı — reklam hesabı tanımlandığında görünür.";
      return;
    }
    var etiket = document.createElement("script");
    etiket.async = true;
    etiket.src = meta.content;
    etiket.onerror = function () { alan.textContent = "Reklam yüklenemedi."; };
    document.head.appendChild(etiket);
  }

  var bant = document.getElementById("cerezBandi");
  if (bant && !onayOku()) bant.hidden = false;

  var onayla = document.getElementById("cerezOnay");
  if (onayla) {
    onayla.addEventListener("click", function () {
      onayYaz({ reklam: true, tarih: Date.now() });
      if (bant) bant.hidden = true;
      reklamYerlesim();
    });
  }

  var reddet = document.getElementById("cerezRed");
  if (reddet) {
    reddet.addEventListener("click", function () {
      onayYaz({ reklam: false, tarih: Date.now() });
      if (bant) bant.hidden = true;
      reklamYerlesim();
    });
  }

  reklamYerlesim();
})();
