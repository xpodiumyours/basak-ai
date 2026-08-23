/* BasakHead v5 — parçacık insan büstü + elektrik arkları + bloom
   - örgülü kontur halkaları (organik dalgalı kesitler, silüet kenarı parlak)
   - meridyen akış çizgileri (yüzeyde boyuna dokuma hissi)
   - büyük kehribar yüz çekirdeği (beyaz-sarı çekirdek → turuncu → kızıl kenar)
   - göğüste dallanan altın sinir lifleri + üzerinde gezinen nabızlar
   - kafa üstü toz püskürtmesi
   - elektrik arkları (kısa ömürlü şimşek çizgileri)
   - bloom post-processing (CSS glow katmanı)
   Durumlar: bekliyor/dinliyor/algiliyor/dusunuyor/konusuyor/arac/hata/uyku */
(function () {
  "use strict";

  var renderer, scene, camera, grup;
  var U = {};            // paylaşılan shader uniformları
  var hedef = null;      // lerp edilecek durum hedefleri
  var anlik = null;      // şu anki değerler
  var halkalar = [];     // kontur çizgileri
  var meridyenler = [];  // boyuna akış çizgileri
  var lifler = [];       // nabızlar: {egri, top, mat, faz, altin}
  var dugumler = [];     // altın dal başlangıç parıltıları
  var yuzMesh;           // yüz çekirdeği
  var yuzParlama;        // yüz arkası yumuşak hâle
  var basladi = false;
  var sesSeviye = 0;
  var sesSon = -9;
  var arclar = [];       // elektrik arkları
  var bloomKatman = null; // CSS bloom katmanı

  /* ---------- durum tanımları ---------- */
  var DURUMLAR = {
    bekliyor:   { flow: 0.28, core: 0.38, face: 0.46, amp: 0.15, mix: 0, inward:  0, egim:  0    },
    dinliyor:   { flow: 0.55, core: 0.58, face: 0.48, amp: 0.22, mix: 0, inward:  1, egim:  0    },
    algiliyor:  { flow: 0.95, core: 1.00, face: 0.52, amp: 0.20, mix: 0, inward:  1, egim: -0.04 },
    dusunuyor:  { flow: 1.25, core: 1.15, face: 0.52, amp: 0.24, mix: 0, inward:  1, egim: -0.08 },
    konusuyor:  { flow: 0.75, core: 0.88, face: 1.00, amp: 1.00, mix: 0, inward:  0, egim:  0    },
    arac:       { flow: 1.50, core: 0.95, face: 0.62, amp: 0.30, mix: 0, inward: -1, egim:  0.05 },
    hata:       { flow: 0.03, core: 0.15, face: 0.12, amp: 0.02, mix: 1, inward:  0, egim:  0    },
    uyku:       { flow: 0.06, core: 0.10, face: 0.08, amp: 0.03, mix: 0, inward:  0, egim:  0    },
  };

  /* ---------- yardımcılar ---------- */
  function rast() { return Math.random(); }
  function clamp01(x) { return Math.min(1, Math.max(0, x)); }
  function sstep(a, b, x) {
    var t = clamp01((x - a) / (b - a));
    return t * t * (3 - 2 * t);
  }

  /* ---------- enerji küresi profili ----------
     Döndürür: {rx, rz, zc} — imza aynı kaldığı için çağıran her yer çalışır.
     Küre merkezi (0, 1.30, 0), yarıçap 1.05. */
  function profil(y) {
    var dt = (y - 1.30) / 1.05;
    var k = Math.sqrt(Math.max(0, 1 - dt * dt));
    var r = 1.05 * k;
    return { rx: r, rz: r, zc: 0 };
  }

  /* ---------- elektrik arkı (lightning arc) ---------- */
  function elektrikArcOlustur(t) {
    var adet = 2 + Math.floor(Math.random() * 3);
    for (var i = 0; i < adet; i++) {
      var noktalar = [];
      var basA = Math.random() * Math.PI * 2;
      var basY = 0.5 + Math.random() * 1.6;
      var segments = 4 + Math.floor(Math.random() * 5);
      for (var j = 0; j <= segments; j++) {
        var a = basA + (Math.random() - 0.5) * 0.9;
        var y = basY + (Math.random() - 0.5) * 0.18;
        var p = profil(y);
        var r = p.rx * (1.03 + Math.random() * 0.08);
        noktalar.push(new THREE.Vector3(
          Math.cos(a) * r, y, Math.sin(a) * r
        ));
      }
      var geo = new THREE.BufferGeometry().setFromPoints(noktalar);
      var mat = new THREE.LineBasicMaterial({
        color: 0xbbddff, transparent: true, opacity: 0.95,
        blending: THREE.AdditiveBlending, depthWrite: false,
      });
      var cizgi = new THREE.Line(geo, mat);
      grup.add(cizgi);
      arclar.push({ mesh: cizgi, olusum: t, sure: 0.06 + Math.random() * 0.14 });
    }
  }

  /* ---------- bloom CSS katmanı ---------- */
  function bloomKatmanOlustur() {
    if (bloomKatman) return;
    // Sahne div'ine CSS bloom efekti ekle — WebGL canvas'ı bozmaz
    var sahne = document.getElementById("sahne");
    if (!sahne) return;
    bloomKatman = document.createElement("div");
    bloomKatman.id = "bloomLayer";
    bloomKatman.style.cssText = "position:absolute;inset:0;pointer-events:none;" +
      "filter:blur(22px) brightness(1.5);opacity:0.30;mix-blend-mode:screen;";
    sahne.appendChild(bloomKatman);
  }

  /* ---------- yüzey geometrisi yardımcıları ---------- */
  function yuzeyNoktasi(y, a) {
    var p = profil(y);
    return [
      Math.cos(a) * p.rx,
      y,
      Math.sin(a) * p.rz + p.zc,
    ];
  }

  /* Sayısal türevle yüzey normali (dışa dönük). */
  function yuzeyNormali(y, a) {
    var e = 0.006;
    var Py1 = yuzeyNoktasi(y + e, a), Py0 = yuzeyNoktasi(y - e, a);
    var Pa1 = yuzeyNoktasi(y, a + e), Pa0 = yuzeyNoktasi(y, a - e);
    var S = [Py1[0] - Py0[0], Py1[1] - Py0[1], Py1[2] - Py0[2]]; // dP/dy
    var T = [Pa1[0] - Pa0[0], Pa1[1] - Pa0[1], Pa1[2] - Pa0[2]]; // dP/da
    var nx = S[1] * T[2] - S[2] * T[1];
    var ny = S[2] * T[0] - S[0] * T[2];
    var nz = S[0] * T[1] - S[1] * T[0];
    // dışa dönük olmayan ters çevrilir
    if (nx * Math.cos(a) + nz * Math.sin(a) < 0) { nx = -nx; ny = -ny; nz = -nz; }
    var u = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;
    return [nx / u, ny / u, nz / u];
  }

  /* ---------- parçacık bulutları ---------- */
  function yuzeyNoktalari(hedefDizi, adet, kabariklikMin, kabariklikMax,
                          normalller) {
    for (var i = 0; i < adet; i++) {
      var y = 0.27 + rast() * 2.06;
      var p = profil(y);
      if (p.rx < 0.02) { hedefDizi.push(0, y, 0); if (normalller) normalller.push(0, 1, 0); continue; }
      var a = rast() * Math.PI * 2;
      var n = null;
      if (normalller) {
        n = yuzeyNormali(y, a);
        normalller.push(n[0], n[1], n[2]);
      }
      var kabarik = 1 + kabariklikMin + rast() * (kabariklikMax - kabariklikMin);
      hedefDizi.push(
        Math.cos(a) * p.rx * kabarik,
        y + (rast() - 0.5) * 0.015,
        Math.sin(a) * p.rz * kabarik + p.zc
      );
    }
  }

  function beyinCekirdegi(hedefDizi, adet) {
    for (var i = 0; i < adet; i++) {
      var a = rast() * Math.PI * 2, q = Math.acos(2 * rast() - 1);
      var r = 0.16 + Math.pow(rast(), 1.6) * 0.42;
      hedefDizi.push(
        Math.sin(q) * Math.cos(a) * r * 0.85,
        1.30 + Math.cos(q) * r * 0.92,
        0.00 + Math.sin(q) * Math.sin(a) * r
      );
    }
  }

  /* kafa üstüne savrulan ince toz bulutu */
  function ustToz(hedefDizi, adet) {
    for (var i = 0; i < adet; i++) {
      var yuk = rast();
      var y = 2.35 + yuk * 0.55;
      var r = (0.60 * (1 - yuk) + 0.05) * Math.pow(rast(), 0.7);
      var a = rast() * Math.PI * 2;
      hedefDizi.push(Math.cos(a) * r, y, Math.sin(a) * r * 0.85);
    }
  }

  function parcacikMalzemesi(kenarGucu) {
    return new THREE.ShaderMaterial({
      uniforms: {
        uTime: U.uTime, uFlow: U.uFlow, uInward: U.uInward,
        uWave: U.uWave, uLevel: U.uLevel, uCore: U.uCore, uMix: U.uMix,
        uKenar: { value: kenarGucu || 0 },
      },
      vertexShader: [
        "attribute float aSeed;",
        "uniform float uTime,uFlow,uInward,uWave,uLevel;",
        "varying float vParlak; varying float vFresnel;",
        "void main(){",
        "  vec3 p = position;",
        "  float dalga = sin(uTime*(0.6+uFlow*2.2)+aSeed*17.0)*0.5+0.5;",
        "  vec3 eksen = normalize(vec3(p.x,(p.y-1.3)*0.45,p.z)+vec3(0.0001));",
        "  p += eksen * dalga * (0.006+uFlow*0.020);",
        "  p.y += sin(uTime*(uFlow*1.2+uLevel*2.0)+aSeed*31.0)*0.009*(uFlow+uLevel);",
        "  vec3 merkez = vec3(0.0,1.30,0.0);",
        "  p += (merkez-p)*(uInward*0.07*sin(uTime*2.0+aSeed*7.0));",
        "  vParlak = 0.45+0.55*dalga;",
        "  vec4 mv = modelViewMatrix*vec4(p,1.0);",
        "  vec3 n = normalize(normalMatrix*normal);",
        "  vec3 gorus = normalize(-mv.xyz);",
        "  vFresnel = pow(1.0-abs(dot(n,gorus)), 1.7);",
        "  gl_PointSize = min((0.52+aSeed*0.80)*(74.0/-mv.z), 5.5);",
        "  gl_Position = projectionMatrix*mv;",
        "}"
      ].join("\n"),
      fragmentShader: [
        "uniform float uCore,uMix,uLevel,uKenar;",
        "varying float vParlak; varying float vFresnel;",
        "void main(){",
        "  vec2 uv = gl_PointCoord-0.5;",
        "  float a = smoothstep(0.5,0.0,length(uv));",
        "  vec3 derin = vec3(0.14,0.36,0.90);",
        "  vec3 kenar = vec3(0.62,0.84,1.0);",
        "  vec3 renk = mix(derin,kenar,clamp(vFresnel*1.15+vParlak*0.25,0.0,1.0));",
        "  renk = mix(renk, vec3(0.97,0.44,0.44), uMix);",
        "  float alfa = a*(0.075+vFresnel*uKenar)*(0.48+uCore*0.46)",
        "             + a*vParlak*0.05 + a*uLevel*0.22;",
        "  gl_FragColor = vec4(renk, alfa);",
        "}"
      ].join("\n"),
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
  }

  function noktaBulutu(pozisyonlar, normaller, kenarGucu) {
    var g = new THREE.BufferGeometry();
    var seeds = new Float32Array(pozisyonlar.length / 3);
    for (var i = 0; i < seeds.length; i++) seeds[i] = rast();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pozisyonlar, 3));
    g.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 1));
    if (normaller && normaller.length) {
      g.setAttribute("normal", new THREE.Float32BufferAttribute(normaller, 3));
    } else {
      // normal yoksa hepsi öne bakar — fresnel etkisiz kalır
      var n0 = new Float32Array(pozisyonlar.length);
      for (var j = 0; j < n0.length; j += 3) { n0[j] = 0; n0[j + 1] = 0; n0[j + 2] = 1; }
      g.setAttribute("normal", new THREE.BufferAttribute(n0, 3));
    }
    return new THREE.Points(g, parcacikMalzemesi(kenarGucu));
  }

  /* ---------- kontur halkaları (örgülü kesitler) ----------
     Referanstaki akan topografya çizgileri: her halka profilin kesitidir ama
     ölü düz değildir — hafif dokuma dalgalanmasıyla organik akar.
     Parlaklık silüet kenarında artar. */
  function konturHalkalari() {
    var N = 140;                      // halka sayısı
    var M = 170;                      // halka başına nokta
    for (var i = 0; i < N; i++) {
      var t = i / (N - 1);
      var y = 0.29 + t * 2.02;       // 0.29 .. 2.31
      var p = profil(y);
      var pts = [];
      var renk = new Float32Array((M + 1) * 3);
      var orgu = rast() * Math.PI * 2;
      for (var j = 0; j <= M; j++) {
        var a = (j / M) * Math.PI * 2;
        // organik örgü dalgalanması
        var t_sim = performance.now() / 1000;
        var dy = 0.012 * Math.sin(a * 3 + orgu)
               + 0.008 * Math.sin(a * 7 - orgu * 1.7)
               + 0.005 * Math.sin(a * 13 + orgu * 2.3)
               + 0.004 * Math.sin(y * 5 + t_sim * 2.0);
        pts.push(new THREE.Vector3(
          Math.cos(a) * p.rx,
          y + dy,
          Math.sin(a) * p.rz + p.zc
        ));
        // silüet kenarı (|cos| tepe) en parlak — referansın imzası
        var kenar = Math.pow(Math.abs(Math.cos(a)), 3.0);
        var b = 0.16 + 0.84 * kenar;
        renk[j * 3] = b; renk[j * 3 + 1] = b; renk[j * 3 + 2] = b;
      }
      var geo = new THREE.BufferGeometry().setFromPoints(pts);
      geo.setAttribute("color", new THREE.BufferAttribute(renk, 3));
      var mat = new THREE.LineBasicMaterial({
        vertexColors: true, transparent: true, opacity: 0.34,
        blending: THREE.AdditiveBlending, depthWrite: false,
      });
      mat.color.setHex(0x66c2ff);
      var cizgi = new THREE.LineLoop(geo, mat);
      cizgi.userData = { faz: rast() * Math.PI * 2, taban: 0.16 + 0.20 * Math.sin(t * Math.PI), y: y };
      grup.add(cizgi);
      halkalar.push(cizgi);
    }
  }

  /* ---------- meridyen akışları ----------
     Yüzeyde boyuna akan ince çizgiler — dokuma hissini tamamlar. */
  function meridyenAkislari() {
    var adet = 36, SEG = 90;
    for (var i = 0; i < adet; i++) {
      var a0 = (i / adet) * Math.PI * 2 + rast() * 0.14;
      var faz = rast() * Math.PI * 2;
      var pts = [];
      for (var j = 0; j <= SEG; j++) {
        var q = j / SEG;
        var yy = 2.33 - q * 2.06;             // 2.33 .. 0.27
        var aa = a0 + Math.sin(yy * 1.6 + faz) * 0.10;
        var p = profil(yy);
        pts.push(new THREE.Vector3(
          Math.cos(aa) * p.rx * 1.006,
          yy,
          Math.sin(aa) * p.rz * 1.006 + p.zc
        ));
      }
      var geo = new THREE.BufferGeometry().setFromPoints(pts);
      var mat = new THREE.LineBasicMaterial({
        color: 0x3f92e8, transparent: true, opacity: 0.10,
        blending: THREE.AdditiveBlending, depthWrite: false,
      });
      var cizgi = new THREE.Line(geo, mat);
      cizgi.userData = { faz: faz };
      grup.add(cizgi);
      meridyenler.push(cizgi);
    }
  }

  /* ---------- nabız dokusu ---------- */
  function nabizDokusu(rgb) {
    var cv = document.createElement("canvas");
    cv.width = cv.height = 64;
    var cx = cv.getContext("2d");
    var grd = cx.createRadialGradient(32, 32, 1, 32, 32, 32);
    grd.addColorStop(0, "rgba(255,255,255,1)");
    grd.addColorStop(0.25, "rgba(" + rgb + ",0.95)");
    grd.addColorStop(0.6, "rgba(" + rgb + ",0.35)");
    grd.addColorStop(1, "rgba(" + rgb + ",0)");
    cx.fillStyle = grd;
    cx.fillRect(0, 0, 64, 64);
    return new THREE.CanvasTexture(cv);
  }

  /* ---------- altın dallanan sinir lifleri ----------
     Boğazdan sternuma inen ana damar + göğse açılan yan dallar;
     her dalda eğri boyunca gezinen kehribar nabızlar. */
  function altinDallar() {
    var amberDoku = nabizDokusu("255,190,90");

    function nabizEkle(egri) {
      var top = new THREE.Sprite(new THREE.SpriteMaterial({
        map: amberDoku,
        transparent: true, blending: THREE.AdditiveBlending,
        depthWrite: false, opacity: 0.8,
      }));
      top.scale.set(0.055, 0.055, 1);
      grup.add(top);
      lifler.push({ egri: egri, top: top, mat: null, faz: rast(), altin: true });
    }

    function dugumEkle(nokta) {
      var s = new THREE.Sprite(new THREE.SpriteMaterial({
        map: amberDoku,
        transparent: true, blending: THREE.AdditiveBlending,
        depthWrite: false, opacity: 0.35,
      }));
      s.position.copy(nokta);
      s.scale.set(0.07, 0.07, 1);
      grup.add(s);
      dugumler.push(s);
    }

    function dalEkle(noktaListesi, opasite, renk, nabizAdet) {
      var egri = new THREE.CatmullRomCurve3(noktaListesi);
      var geo = new THREE.BufferGeometry().setFromPoints(egri.getPoints(40));
      var mat = new THREE.LineBasicMaterial({
        color: renk, transparent: true, opacity: opasite,
        blending: THREE.AdditiveBlending, depthWrite: false,
      });
      grup.add(new THREE.Line(geo, mat));
      for (var k = 0; k < nabizAdet; k++) nabizEkle(egri);
      return egri;
    }

    // plazma kolları: çekirdekten küre yüzeyine uzanan altın damarlar
    var merkez = new THREE.Vector3(0, 1.30, 0);

    function yon() {
      var a = rast() * Math.PI * 2, q = Math.acos(2 * rast() - 1);
      return new THREE.Vector3(
        Math.sin(q) * Math.cos(a), Math.cos(q), Math.sin(q) * Math.sin(a)
      );
    }

    function sapdir(dir, aci) {
      var eksen = new THREE.Vector3(rast() - 0.5, rast() - 0.5, rast() - 0.5).normalize();
      return dir.clone().applyAxisAngle(eksen, aci).normalize();
    }

    function kol(opasite, renk, nabizAdet, dugumVar) {
      var d1 = yon();
      var bas = merkez.clone().add(d1.clone().multiplyScalar(0.22));
      var orta = merkez.clone().add(sapdir(d1, 0.35).multiplyScalar(0.62));
      var son = merkez.clone().add(sapdir(d1, 0.55).multiplyScalar(0.98));
      dalEkle([bas, orta, son], opasite, renk, nabizAdet);
      if (dugumVar) dugumEkle(bas);
    }

    kol(0.55, 0xffb14e, 3, true);   // ana damar
    // yan kollar (sayı/opaklık/renk aynen korunuyor)
    var kolOpaklari = [0.32, 0.32, 0.28, 0.28, 0.24, 0.24];
    for (var i = 0; i < kolOpaklari.length; i++) kol(kolOpaklari[i], 0xf5a53f, 1, true);
    // alt kollar (düğümsüz)
    var altOpaklari = [0.16, 0.16, 0.16, 0.16];
    for (i = 0; i < altOpaklari.length; i++) kol(altOpaklari[i], 0xd99445, 1, false);
  }

  /* ---------- mavi veri nabızlı ince lifler ---------- */
  function sinirLifleri() {
    var maviDoku = nabizDokusu("120,180,255");
    var adet = 12;
    for (var i = 0; i < adet; i++) {
      // plazma kolu: çekirdekten yüzeye (mavi veri nabzı)
      var maviMerkez = new THREE.Vector3(0, 1.30, 0);
      var qa = Math.acos(2 * rast() - 1);
      var fa = rast() * Math.PI * 2;
      var d1 = new THREE.Vector3(
        Math.sin(qa) * Math.cos(fa), Math.cos(qa), Math.sin(qa) * Math.sin(fa));
      var eksen = new THREE.Vector3(rast() - 0.5, rast() - 0.5, rast() - 0.5).normalize();
      var d2 = d1.clone().applyAxisAngle(eksen, 0.35).normalize();
      var eksen2 = new THREE.Vector3(rast() - 0.5, rast() - 0.5, rast() - 0.5).normalize();
      var d3 = d1.clone().applyAxisAngle(eksen2, 0.55).normalize();
      var egri = new THREE.CatmullRomCurve3([
        maviMerkez.clone().add(d1.clone().multiplyScalar(0.22)),
        maviMerkez.clone().add(d2.clone().multiplyScalar(0.62)),
        maviMerkez.clone().add(d3.clone().multiplyScalar(0.98)),
      ]);

      var merkezde = (i % 4 === 0);
      var mat = new THREE.LineBasicMaterial({
        color: merkezde ? 0xffb85c : 0x4d9aff,
        transparent: true, opacity: 0.11,
        blending: THREE.AdditiveBlending, depthWrite: false,
      });
      var geo = new THREE.BufferGeometry().setFromPoints(egri.getPoints(46));
      grup.add(new THREE.Line(geo, mat));

      var top = new THREE.Sprite(new THREE.SpriteMaterial({
        map: merkezde ? nabizDokusu("255,200,110") : maviDoku,
        transparent: true, blending: THREE.AdditiveBlending,
        depthWrite: false, opacity: 0.8,
      }));
      top.scale.set(0.055, 0.055, 1);
      grup.add(top);

      lifler.push({ egri: egri, top: top, mat: mat, faz: rast(), altin: false });
    }
  }

  /* ---------- yüz çekirdeği: dalgalı kehribar enerji ----------
     Referanstaki gibi: beyaz-sarı çekirdek → turuncu → kızıl kenar,
     ince yatay girişim şeritleri, yavaş dikey dalga. */
  function yuzCekirdegi() {
    var geo = new THREE.PlaneGeometry(1.15, 1.15);
    var mat = new THREE.ShaderMaterial({
      uniforms: U,
      vertexShader: [
        "varying vec2 vUv;",
        "void main(){",
        "  vUv = uv;",
        "  gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);",
        "}",
      ].join("\n"),
      fragmentShader: [
        "uniform float uTime,uFace,uLevel;",
        "varying vec2 vUv;",
        "void main(){",
        "  vec2 p = vUv-0.5;",
        "  p.x *= 1.0;",
        "  float d = length(p);",
        "  float maske = smoothstep(0.56,0.10,d);",
        // ince yatay girişim şeritleri + ikinci ince doku + yavaş dalga
        "  float serit = 0.58+0.42*sin(vUv.y*58.0-uTime*(2.0+uLevel*13.0));",
        "  float ince  = 0.80+0.20*sin(vUv.y*23.0+uTime*2.6);",
        "  float dalga = 0.5+0.5*sin(vUv.y*6.5-uTime*(1.5+uLevel*5.0)+sin(vUv.x*5.0)*0.9);",
        "  vec3 cekirdek  = vec3(1.0,0.98,0.76);",
        "  vec3 turuncu   = vec3(0.99,0.53,0.07);",
        "  vec3 koyuKenar = vec3(0.66,0.17,0.03);",
        "  vec3 sicak = mix(cekirdek,turuncu,smoothstep(0.03,0.30,d));",
        "  sicak = mix(sicak,koyuKenar,smoothstep(0.30,0.56,d));",
        "  float parlak = maske*serit*ince*(0.72+uFace*0.95)*(0.62+uLevel*1.9)*(0.72+0.28*dalga);",
        "  gl_FragColor = vec4(sicak*parlak, maske*(0.52+uFace*0.48));",
        "}",
      ].join("\n"),
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    });
    yuzMesh = new THREE.Mesh(geo, mat);
    yuzMesh.position.set(0, 1.30, 0.35);
    grup.add(yuzMesh);

    // arkasına geniş yumuşak kehribar hâle (bloom hissi)
    yuzParlama = new THREE.Sprite(new THREE.SpriteMaterial({
      map: nabizDokusu("245,158,11"),
      transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    yuzParlama.scale.set(1.60, 1.60, 1);
    yuzParlama.position.set(0, 1.30, 0.20);
    grup.add(yuzParlama);
  }

  /* ---------- ana döngü ---------- */
  function dongu(t0) {
    requestAnimationFrame(dongu);
    if (document.hidden || !renderer) return;
    var t = performance.now() / 1000;

    // durum yumuşatması (lerp)
    if (hedef && anlik) {
      for (var k in hedef) anlik[k] += (hedef[k] - anlik[k]) * 0.045;
    }
    var A = anlik || DURUMLAR.bekliyor;

    // ses zarfı: konuşma durunca dalga yavaşça söner
    if (t - sesSon > 0.30) sesSeviye *= 0.90;
    U.uTime.value = t;
    U.uFlow.value = A.flow;
    U.uInward.value = A.inward;
    U.uWave.value = A.amp;
    U.uCore.value = A.core;
    U.uFace.value = A.face;
    U.uLevel.value += (sesSeviye - U.uLevel.value) * 0.25;
    U.uMix.value += ((hedef ? hedef.mix : 0) - U.uMix.value) * 0.06;

    // nefes: kamera çok hafif yakınlaşır/uzaklaşır
    camera.position.z = 3.80 + Math.sin(t * 0.21) * 0.06;
    camera.lookAt(0, 1.30, 0);

    // büst çok hafif sağa-sola döner (kürede halkaların dönüşü hoş görünür)
    var hareket = 0.35 + 0.65 * Math.min(1, A.flow);
    grup.rotation.y = Math.sin(t * 0.13) * 0.11 * hareket;
    grup.rotation.z = Math.sin(t * 0.09) * 0.014 * hareket;

    // kontur halkaları: aşağıdan yukarı akan tarama dalgası + hata tonu
    var km = U.uMix.value;
    for (var i = 0; i < halkalar.length; i++) {
      var h = halkalar[i];
      var dalga = 0.5 + 0.5 * Math.sin(t * (0.8 + A.flow * 1.5) - h.userData.y * 2.4 + h.userData.faz);
      h.material.opacity = (h.userData.taban + 0.32 * dalga) *
                           (0.65 + 0.85 * Math.min(1, A.flow + 0.35));
      h.material.color.setRGB(
        0.30 + 0.67 * km,
        0.66 - 0.22 * km,
        1.00 - 0.56 * km
      );
    }

    // meridyen akışları: yavaş parlaklık nefesi
    for (i = 0; i < meridyenler.length; i++) {
      var m = meridyenler[i];
      m.material.opacity = (0.05 + 0.08 * (0.5 + 0.5 * Math.sin(t * 0.45 + m.userData.faz))) *
                           (0.55 + 0.75 * Math.min(1, A.flow));
    }

    // lifler: eğrilerde gezinen nabızlar — altın damarlar her zaman görünür
    for (i = 0; i < lifler.length; i++) {
      var L = lifler[i];
      var tp, parlama, olcu;
      if (L.altin) {
        tp = (t * (0.05 + A.flow * 0.06) + L.faz) % 1;
        parlama = 0.5 + 0.5 * Math.sin(t * (0.9 + A.flow * 1.1) + L.faz * 9);
        L.top.material.opacity = (0.35 + 0.60 * parlama) *
                                 Math.min(1, 0.45 + A.flow * 0.35 + sesSeviye * 0.6);
        olcu = 0.050 + 0.030 * parlama + sesSeviye * 0.04;
      } else {
        tp = (t * (0.10 + A.flow * 0.13) + L.faz) % 1;
        parlama = 0.5 + 0.5 * Math.sin(t * (1 + A.flow * 2.2) + L.faz * 9);
        L.top.material.opacity = (0.25 + 0.65 * parlama) *
                                 Math.min(1, 0.30 + A.flow + sesSeviye * 0.5);
        L.mat.opacity = 0.07 + 0.14 * parlama * Math.min(1, A.flow + 0.2);
        olcu = 0.050 + 0.032 * parlama + sesSeviye * 0.05;
      }
      L.top.position.copy(L.egri.getPoint(tp));
      L.top.scale.set(olcu, olcu, 1);
    }

    // altın dal düğümleri: yumuşak yanıp söner
    for (i = 0; i < dugumler.length; i++) {
      dugumler[i].material.opacity = 0.22 + 0.20 * (0.5 + 0.5 * Math.sin(t * 1.6 + i));
    }

    // yüz çekirdeği: kameraya dönük kalsın + nabzı
    if (yuzMesh) {
      yuzMesh.quaternion.copy(camera.quaternion);
      var olcek = 0.92 + A.face * 0.28 + sesSeviye * 0.20;
      yuzMesh.scale.set(olcek, olcek, 1);
    }
    if (yuzParlama) {
      yuzParlama.material.opacity =
        (0.20 + A.face * 0.40 + sesSeviye * 0.32) * (0.85 + 0.15 * Math.sin(t * 2.4));
      var po = 1.55 + 0.10 * Math.sin(t * 1.8);
      yuzParlama.scale.set(po, po, 1);
    }

    // elektrik arkları: rastgele üretim + temizlik
    if (Math.random() < 0.05 * (0.3 + A.flow + sesSeviye)) {
      elektrikArcOlustur(t);
    }
    for (i = arclar.length - 1; i >= 0; i--) {
      if (t - arclar[i].olusum > arclar[i].sure) {
        grup.remove(arclar[i].mesh);
        arclar[i].mesh.geometry.dispose();
        arclar.splice(i, 1);
      } else {
        // arç parlaması: hızlı sönen parlaklık
        var arcan = 1 - (t - arclar[i].olusum) / arclar[i].sure;
        arclar[i].mesh.material.opacity = arcan * 0.95;
      }
    }

    renderer.render(scene, camera);


  }

  /* ---------- genel API ---------- */
  window.BasakHead = {
    init: function () {
      if (basladi || !window.THREE) return;
      basladi = true;
      bloomKatmanOlustur();
      var tuval = document.getElementById("sahneCanvas");
      renderer = new THREE.WebGLRenderer({ canvas: tuval, alpha: true, antialias: false });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.6));
      renderer.setSize(window.innerWidth, window.innerHeight);
      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(46, window.innerWidth / window.innerHeight, 0.1, 100);
      camera.position.set(0, 1.30, 3.80);
      grup = new THREE.Group();
      scene.add(grup);

      U = {
        uTime:   { value: 0 }, uFlow:   { value: 0.28 },
        uInward: { value: 0 }, uWave:   { value: 0.15 },
        uCore:   { value: 0.38 }, uFace:  { value: 0.34 },
        uMix:    { value: 0 }, uLevel:  { value: 0 },
      };

      var ten = [], tenN = [], hale = [], beyin = [], ust = [];
      yuzeyNoktalari(ten, 7200, 0.0, 0.014, tenN);   // cilt yüzeyi (sıkı, az toz)
      yuzeyNoktalari(hale, 2400, 0.05, 0.22, null);  // silüet çevresi püskürtme
      beyinCekirdegi(beyin, 2000);                   // beynin iç kümesi
      ustToz(ust, 800);                              // kafanın tepesinde savrulan toz
      grup.add(noktaBulutu(ten, tenN, 0.90));        // fresnel kenarlı cilt
      grup.add(noktaBulutu(hale, null, 0));
      grup.add(noktaBulutu(beyin, null, 0));
      grup.add(noktaBulutu(ust, null, 0));

      konturHalkalari();
      meridyenAkislari();
      altinDallar();
      sinirLifleri();
      yuzCekirdegi();

      anlik = JSON.parse(JSON.stringify(DURUMLAR.bekliyor));
      hedef = DURUMLAR.bekliyor;

      window.addEventListener("resize", function () {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
      });

      requestAnimationFrame(dongu);
    },

    durum: function (ad) {
      if (DURUMLAR[ad]) hedef = DURUMLAR[ad];
    },

    /* Gerçek ses seviyesi (0..1): yüz dalgaları, beyin parlaklığı, lif nabzı */
    ses: function (seviye) {
      var v = Math.min(1, Math.max(0, Number(seviye) || 0));
      sesSeviye = Math.max(sesSeviye * 0.6, v);
      sesSon = performance.now() / 1000;
    },
  };
})();
