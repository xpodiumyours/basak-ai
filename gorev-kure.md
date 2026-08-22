# Görev — Arka plandaki büstü "enerji küresi"ne çevir (ui/head.js)

## Amaç
Parçacık insan büstü ikna edici bir insan silüeti vermiyor (mantar/ampul gibi görünüyor). Karar: **insan şeklinden vazgeçiliyor.**

Yerine: nefes alan dev bir **enerji küresi** — yüzeyinde enlem gibi akan kontur halkaları, içinde nabız atan altın çekirdek, çekirdekten yüzeye uzanan altın plazma lifleri, tepesinde savrulan toz.

**Titreşim, akış, renk paleti, halka dokusu ve tüm durum animasyonları aynen korunacak.** Sadece şeklin kendisi değişiyor.

## Dokunulacak tek dosya
`ui/head.js`

## Değiştirmeyeceklerin (kapsam kilidi)
- `DURUMLAR` tablosu ve `dongu()` içindeki animasyon mantığı (halka dalgası, ses seviyesi, nabızlar, lerp).
- `parcacikMalzemesi` shader'ı, renkler, `nabizDokusu`, blending ayarları.
- `ui/style.css`, `ui/app.js`, Python tarafı, `BasakHead` dış API'si (`init` / `durum` / `ses`) — hiçbiri.
- Yeni kütüphane, yeni dosya yok.

**Küre merkezi: `(0, 1.30, 0)` — yarıçap `1.05`.** Aşağıdaki her sayı bununla uyumlu.

---

## 1. `profil()` — anatomi gidiyor, küre geliyor
Fonksiyonun tüm gövdesini (kafa/boyun/omuz harmanı) sil, yerine küre kesiti koy. İmza ve dönüş yapısı **aynı kalsın** (`{rx, rz, zc}`) — çağıran her yer bozulmadan çalışır:

```js
function profil(y) {
  var dt = (y - 1.30) / 1.05;
  var k = Math.sqrt(Math.max(0, 1 - dt * dt));
  var r = 1.05 * k;
  return { rx: r, rz: r, zc: 0 };
}
```

`sstep` başka yerlerde kullanılıyorsa dursun; kullanılmıyorsa da silme.

## 2. Y aralıklarını küreye eşitle (4 ayrı yerde elle yazılı)
Küre `0.25` ile `2.35` arasında yaşıyor. Biri unutulursa boşluk/artık çizgi kalır:

- `yuzeyNoktalari`: `var y = -0.84 + rast() * 3.18;` → `var y = 0.27 + rast() * 2.06;`
- `konturHalkalari`: `var y = -0.82 + t * 3.14;` → `var y = 0.29 + t * 2.02;`
  (kutuplara tam değmemesi bilinçli — orada yarıçap sıfıra iner)
- `meridyenAkislari`: `var yy = 2.28 - q * 3.06;` → `var yy = 2.33 - q * 2.06;`
- `ustToz`: `var y = 2.34 + yuk * 0.55;` → `var y = 2.35 + yuk * 0.55;`

## 3. İç çekirdek kümesi (`beyinCekirdegi`)
Kafanın içindeydi, şimdi kürenin ortasında olacak:

- `1.72 + Math.cos(q) * r * 0.92` → `1.30 + Math.cos(q) * r * 0.92`
- `0.04 + Math.sin(q)...` → `0.0 + Math.sin(q)...`
- `var r = 0.13 + Math.pow(rast(), 1.6) * 0.30;` → `0.16 + Math.pow(rast(), 1.6) * 0.42;`

## 4. Shader'daki merkez noktası
`parcacikMalzemesi` içindeki içe çekilme merkezi kafaya göre ayarlıydı:

- `vec3 merkez = vec3(0.0,1.55,0.05);` → `vec3 merkez = vec3(0.0,1.30,0.0);`

(Aynı shader'daki `(p.y-1.3)*0.45` satırı zaten doğru merkezde — dokunma.)

## 5. Altın lifler: anatomiden plazmaya
`altinDallar()` ve `sinirLifleri()` şu an "boğazdan sternuma, göğse dallanan" noktalarla yazılı. Küre içinde bunlar havada sarkan çizgiler olarak görünür.

**Animasyon kodunu ve nabız mantığını değiştirme** — sadece eğrilerin geçtiği noktaları değiştir. Her lif artık **çekirdekten yüzeye uzanan bir plazma kolu** olsun:

```js
var merkez = new THREE.Vector3(0, 1.30, 0);
function yon(sapma) {
  var a = rast() * Math.PI * 2, q = Math.acos(2 * rast() - 1);
  return new THREE.Vector3(
    Math.sin(q) * Math.cos(a), Math.cos(q), Math.sin(q) * Math.sin(a)
  );
}
```
Her eğri 3–4 noktadan kurulsun:
- başlangıç: `merkez + yon * 0.22`
- orta: aynı yönün ±0.35 radyan saptırılmışı, mesafe `0.62`
- bitiş: bir kez daha hafif saptırılmış, mesafe `0.98`

Lif sayısı, opaklıklar, renkler, `nabizEkle`/`dugumEkle` çağrıları **aynı kalsın**. `dugumEkle` artık başlangıç noktasına (çekirdeğe yakın) konsun.

## 6. Yüz çekirdeği → küre çekirdeği (`yuzCekirdegi`)
Yatay yayvan yüz ışığıydı; artık ortada duran yuvarlak çekirdek olacak. Fonksiyon adı aynı kalabilir.

- `new THREE.PlaneGeometry(1.55, 1.08)` → `new THREE.PlaneGeometry(1.15, 1.15)`
- shader'daki `p.x *= 1.42;` → `p.x *= 1.0;` (yayvan değil, tam yuvarlak)
- `yuzMesh.position.set(0, 1.33, 0.68)` → `(0, 1.30, 0.35)`
- `dongu()` içindeki `yuzMesh.scale.set(olcek, olcek * 0.93, 1)` → `yuzMesh.scale.set(olcek, olcek, 1)`
- `yuzParlama.scale.set(2.15, 2.15, 1)` → `(1.60, 1.60, 1)`
- `yuzParlama.position.set(0, 1.33, 0.55)` → `(0, 1.30, 0.20)`
- `dongu()` içindeki `var po = 2.05 + 0.10 * Math.sin(t * 1.8);` → `1.55 + 0.10 * ...`

## 7. Kamera: küre kadrajı
- `camera.position.set(0, 1.02, 5.30)` → `(0, 1.30, 3.80)`
- `camera.lookAt(0, 1.02, 0)` → `camera.lookAt(0, 1.30, 0)`
- Nefes satırı: `camera.position.z = 5.30 + ...` → `3.80 + ...`
- `3.80` değerini gözle 3.5–4.3 arasında ayarla: küre ekran yüksekliğinin ~2/3'ünü kaplasın, kenarlara değmesin.

## 8. Dönüş hareketi
`grup.rotation.x` (eğilme) küre için anlamsız ve küreyi kaydırır; `grup.rotation.y` (yavaş dönüş) kalsın — halkalar döndükçe hoş görünür.

- `grup.rotation.x += ((A.egim || 0) - grup.rotation.x) * 0.03;` satırını **kaldır**.
- `DURUMLAR` tablosundaki `egim` alanlarına dokunma (başka bir şey okuyor olabilir, dursun).

---

## Doğrulama (bunlar yapılmadan "bitti" deme)
1. `node --check ui/head.js` hatasız.
2. `python basak_app.py` ile uygulamayı gerçekten aç.
3. Ekran görüntüsü al. Kabul ölçütü:
   - şekil net bir **küre**; yumurta/ampul/mantar gibi değil
   - kontur halkaları küre yüzeyinde enlem gibi akıyor, kenarlarda parlıyor
   - altın çekirdek tam ortada, kürenin **dışına taşmıyor**
   - kürenin altında/yanında sarkan artık çizgi, kopuk parçacık kümesi yok
   - küre ekranın yaklaşık 2/3'ü, kenarlara yapışmıyor
4. Konuş/dinle durumlarını dene: ses gelince çekirdek nabız atıyor, akış hızlanıyor (eskisi gibi).
5. Ölçütlerden biri tutmuyorsa sayıyı gözle ayarla, tekrar bak.
