# POTA — Algoritma damıtma düzeni

*22 Ağustos 2026. Casper'ın kararı: önce algoritmayı **arayan** makineyi kur, çıkanı sonra inşa et.*

Pota, metalin eritildiği kaptır. İçine ham cevher atılır, ısıtılır, cüruf yanar, altta saf metal kalır.

Bu düzen de aynısını yapar: içine **aday algoritmalar** atılır, hepsi aynı sınavdan geçirilir, tutmayanlar yanar. Altta kalan, Casper'ın gerçekten istediği algoritmadır.

**FAY dahil.** FAY Motoru bu potaya `aday #0` olarak girer, ayrıcalığı yoktur. Sınavı geçemezse elenir.

---

## 1. Temel fikir: "ne istiyorsun" diye sormuyoruz

Casper'a "nasıl bir algoritma istersin" diye sormak işe yaramaz — istediği şeyi cümleye dökebilseydi zaten yazdırırdı. Ama elinde bundan çok daha değerli bir şey var:

**Aylardır biriken gerçek geçmişi.**

- 26 hafıza dosyası
- Başak'ın hafıza veritabanı (3,3 MB)
- Dört projenin belgeleri ve git geçmişleri
- Aylara yayılmış kendi cümleleri, kararları, hataları

Bu bir **sınav kâğıdı**. İçinde gerçekten olmuş olaylar var: neye inanılmıştı, gerçek neydi, bedeli ne oldu.

Dolayısıyla soru şuna dönüşür:

> *"Bu algoritma 4 Ağustos'ta çalışıyor olsaydı, 19 Ağustos'ta canını yakan şeyi yakalar mıydı?"*

Bu soru **ölçülebilir**. Zevk meselesi olmaktan çıkıp sınav olur. Ve bunu yapabilecek tek kişi Casper — çünkü bu külliyat başka kimsede yok.

---

## 2. Düzenin altı adımı

### Adım 1 — Acı Haritası (sınav sorularını çıkar)

Külliyat taranır, **tekrar eden acılar** çıkarılır. Bir "olay" sayılması için üç şey gerekir:

1. Bir şeye inanılmıştı *(belge, rapor, hatıra)*
2. Gerçek farklıydı *(git, dosya, canlı site, sonraki cümleler)*
3. Bir bedel ödendi *(boşa iş, yanlış zemin, geri dönüş, kayıp zaman)*

Her olay tek satıra indirilir:

```
2026-08-20 | inanılan: "plan kodda uygulandı"
           | gerçek:   commit yok, push yok
           | bedel:    ertesi gün baştan doğrulama
           | kanıt:    git log
```

**Sert kural:** kanıtı olmayan olay haritaya girmez. Şüpheliler ayrı bir kutuya konur ve **puanlamaya katılmaz**.

Beklenen sonuç: 30-60 gerçek olay.

### Adım 2 — Aday üretimi (üç ayrı kaynaktan, bilerek farklı)

Adaylar üç ayrı yoldan üretilir ki birbirine benzemesinler:

| Yol | Nasıl | Örnek |
|---|---|---|
| **A — Acıdan** | En sık tekrar eden olay kümesini doğrudan hedefleyen bir algoritma | "her cevaptan önce git'e bak" |
| **B — Aktarımdan** | Başka yerde çalışan bir mekanizmayı buraya taşı — Casper'ın kendi çözümleri veya dışarıdaki bilinen yöntemler | "uçak kontrol listesi mantığı" |
| **C — Tersinden** | Mevcut kurgudaki bir varsayımı sistematik olarak ters çevir | "yedek zincir → jüri" *(FAY böyle doğdu)* |

Her aday **sabit ve kısa** bir forma yazılır — yoksa karşılaştırılamazlar:

```
ad:            <tek kelime>
ne ölçer:      <tek cümle>
ne zaman konuşur: <tek cümle>
ne sorar:      <tek cümle>
asla yapmaz:   <tek cümle>
```

Beş satır. Uzun anlatım yasak. Anlatılamayan aday zaten kurulamaz.

Hedef: her turda **9 aday** (her yoldan 3), artı devam eden eski adaylar.

### Adım 3 — Geriye dönük sınav (POTANIN ATEŞİ)

Asıl eleme burada. Her aday × her olay için tek soru:

> *"Bu aday, bedel ödenmeden önce bu olayı yakalar mıydı?"*

**Kritik kural — geleceği göstermeyeceksin.** Sınav yapılırken külliyat o olayın tarihinde kesilir. Aday, olaydan sonra yazılmış hiçbir belgeyi göremez. Bu kurala uyulmazsa sınav sahtedir ve tüm düzen çöpe gider.

Her aday dört puan alır:

| Puan | Ne ölçer | İyi olan |
|---|---|---|
| **yakalama** | kaç gerçek olayı yakaladı | yüksek |
| **erkenlik** | bedelden kaç gün önce | yüksek |
| **gürültü** | hiçbir şey yokken kaç kez konuştu *(sakin dönemlerde ölçülür)* | düşük |
| **emek** | haftada kaç dakika Casper'ın dikkatini ister | düşük |

**Gürültü ölçümü şart.** Yoksa kazanan hep "her şeye alarm ver" olur — o da Casper'ı bir haftada bıktırır ve işe yaramaz.

**Sınav seti ayrılır:** en son bir aylık olaylar kenara konur, adaylar onları **hiç görmez**. Bir aday eski olayları ezberleyip yeni olayda çuvallıyorsa burada yakalanır.

### Adım 4 — Turnuva (yalnız sağ kalanlar)

Sınavdan geçenler ikişer ikişer karşılaştırılır — ama **sadece birbirinden ayrıştıkları olaylarda**. Aynı sonucu verdikleri yerlerde karşılaştırmanın bilgisi yok.

Hakem: **ücretsiz paralel jüri** (3 sağlayıcı aynı anda, kotaları ayrı, maliyet sıfır).

Bu adım `research-engine`'deki puanlı eleme turnuvasını ödünç alır — motorun tamamını bağlamaya gerek yok, o parça yeter.

### Adım 5 — Casper kapısı (tek kart, 10 dakika)

Sağ kalan **en fazla 3 aday** Casper'a gider. Liste değil, karşılaştırma kartı:

```
POTA — Tur 1 sonucu

  Elde 34 gerçek olay vardı.

  ADAY "bekçi"   → 22'sini yakalardı, ortalama 3 gün önce
                   ama haftada 5 kez seni rahatsız ederdi

  ADAY "fay"     → 14'ünü yakalardı, ortalama 6 gün önce
                   haftada 1 kez konuşurdu

  Fark: bekçi daha çok yakalıyor, fay daha az yoruyor.

  Soru: (a) çok yakalasın, rahatsız etsin
        (b) az konuşsun, bazılarını kaçırsın
        (c) ikisini melezleyelim
```

Casper'ın cevabı sadece kazananı seçmez — **puan ağırlıklarını günceller.** Sürekli sessiz olanı seçiyorsa "gürültü" ağırlığı yükselir. Yani pota, turlar geçtikçe **Casper'ın zevkini öğrenir.**

**TUR 1 KARARI (2026-08-24, Casper canlı cevabı):** **(a) Bekçi kazandı.**
- Ağırlık güncellemesi: `yakalama` öncelikli puan; `gürültü` cezası hafif tutulur ama ölçüm şart kuralı yerinde durur (bıkkınlık ileride tur 2+ sorusu olarak döner).
- Adım 6 uygulanır: fay'ın ayırt edici mekanizması (düşük konuşma sıklığı) alınır, bekçiyle melezlenir, yeni adaylar tur 2 sınavına girer.
- Kayıt: mimar ajan, Casper'in opencode oturumundaki canlı cevabından işlendi.

### Adım 6 — Melezleme ve yeni tur

Kazanan nihai değil. İkinciden ayırt edici mekanizması alınır, kazananla melezlenir, yeni adaylarla birlikte tekrar sınava girer.

**Durma şartı (yoksa sonsuza kadar döner):**

1. Bir aday gerçek olayların **en az %60'ını** yakalıyor
2. Haftada **1'den az** yanlış alarm veriyor
3. Casper **iki ayrı turda** "evet, bu" diyor

Üçü birden sağlanınca pota söner, çıkan algoritma inşa fazına geçer.

---

## 3. Önemli tavsiye: önce yazılım yazma

Bu düzenin tamamını yazılım olarak kurmak haftalar sürer. Gerek yok.

**Tur 1 elle yürütülebilir.** Kod yazan ajan bir oturumda şunları yapar: külliyatı tarar, acı haritasını çıkarır, 9 aday üretir, geriye dönük sınavı uygular, kartı hazırlar. Çıktı: iki dosya.

Değer buradan çıkarsa otomatikleştirilir. Çıkmazsa hiçbir şey kaybedilmemiştir.

Bu, Casper'ın kendi kuralı: *kanıt olmadan sonraki faz açılmaz.*

---

## 4. Bu düzenin zayıf yerleri (bilerek yazıldı)

| Zayıflık | Neden önemli | Önlem |
|---|---|---|
| **Görünmeyen acılar** | Külliyatta yalnız *fark edilmiş* olaylar var. Hiç fark edilmemiş kayıplar sınavda yok, dolayısıyla hiçbir aday onlardan puan alamaz | Git geçmişi gibi nesnel kaynaklar öncelikli; "fark edilmedi ama izi var" olayları ayrıca aranır |
| **Ezberleme** | Aday geçmişi ezberleyip yeni durumda çuvallayabilir | Son bir ay sınav seti olarak ayrılır, aday görmez |
| **Olay çıkarımı bulanık** | "İnanılan" ile "gerçek" her zaman net ayrılmaz | Kanıtsız olay haritaya girmez, şüpheliler puanlamaya katılmaz |
| **Az veri** | 30-60 olay istatistik için az | Sonuç "kanıtlandı" değil "şu an en iyisi" diye okunur; turlar ilerledikçe olay sayısı artar |
| **Jüri de yanılır** | Hakem modeller de hata yapar | Jüri yalnız Adım 4'te, yalnız ayrıştıkları yerde kullanılır; asıl eleme ölçüme dayalı Adım 3'te yapılır |

---

## 5. Tur 1 için hazır giriş

Pota boş başlamıyor. Bu konuşmadan çıkan üç aday şimdiden elde:

| Aday | Nereden | Beş satırlık formu |
|---|---|---|
| **fay** | C (tersinden) | belge ile gerçeği çarpıştırır · çeliştiğinde konuşur · "hangisi doğru" diye sorar · asla kendi düzeltmez |
| **bekçi** | A (acıdan) | her önemli cevaptan önce git durumunu ölçer · her oturum başında konuşur · "şu 12 dosya ne olacak" diye sorar · asla commit atmaz |
| **karne** | B (aktarımdan) | hangi kaynağın kaç kez yanıldığını sayar · haftada bir konuşur · "buna hâlâ güveniyor musun" diye sorar · asla kaynak silmez |

Tur 1'de bunların üstüne 6 yeni aday üretilir.

---

## 6. Sıra

1. **POTA Tur 1** — elle, tek oturum. Çıktı: `acı-haritasi.md` + `pota-tur1-kart.md`
2. **Casper kararı** — kart üstünden, 10 dakika
3. **Gerekirse Tur 2** — melezleme ile
4. **Durma şartı sağlanınca** → kazanan algoritma `gelişimsüreci.md`'ye faz olarak yazılır ve inşa edilir

`gelişimsüreci.md` bu karara göre güncellendi: FAY artık doğrudan inşa sırasında değil, potanın adayı.
