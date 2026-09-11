# BAŞAK — FAZ 0 ÖLÇÜM RAPORU

Durum: **BAŞLADI**  
Tarih: **12 Eylül 2026**  
Plan: `ANA-PLAN.md`  
Çalışma dalı: `plan/basak-para-kazandiran-asistan-20260912`  
Kod davranışı değişikliği: **0**

## 1. Sabit baz çizgisi

Bugünkü çalışan Başak için değişmez referans:

- repo: `xpodiumyours/basak-ai`
- dal: `master`
- commit: `27b03a9b69e9dd0d7dc224679b43411917f4ff36`
- commit mesajı: `cevap stili: paragraf araligi, ==vurgu== renkli isaret, emoji kurali kaldirildi`

Bu commit FAZ 0 boyunca karşılaştırma tabanıdır. Yeni deney bunun davranışını geriletirse kabul edilmez.

## 2. GitHub doğrulama durumu

`27b03a9b...` için GitHub combined status sonucu boş: zorunlu CI/status check kanıtı yok.

Sonuç:

- geçmiş commit mesajlarındaki `xxx test yeşil` ifadeleri tarihî kanıttır;
- bugünkü HEAD için otomatik test sonucu sayılmaz;
- FAZ 0 yeni ölçümü kendi kanıtını üretmelidir.

## 3. Streaming → araç yolu: doğrulanmış mevcut davranış

`tests/test_akis_ham_arac.py` bugünkü `master`da mevcut.

Testin doğruladığı akış:

1. Streaming metni açıkça ham araç çağrısı gibi görünürse (`list_files(...)`) normal cevap çöpe atılır ve tam araç yoluna düşülür.
2. Streaming temiz düz metin üretirse `brain.cevapla(...)` hiç çağrılmadan cevap doğrudan biter.

Testte bu açıkça `test_temiz_akis_dogrudan_biter` ile korunuyor ve `cevapla_cagrildi == 0` bekleniyor.

FAZ 0 yorumu: Bu bir hata ilan edilmedi. Fakat araç gerektiren soruda küçük/ücretsiz model düz metin kaçışı yaparsa gerçek tool-call yolunun atlanabilmesi yapısal olarak mümkündür. A/B ölçümü zorunludur.

## 4. Küçük/ücretsiz model kapasite kapısı: doğrulanmış mevcut davranış

`tests/test_kapasite_kapi.py` bugünkü `master`da mevcut.

Doğrulananlar:

- `ollama` havuzu küçük sayılır.
- `qwen2.5:3b` küçük model sayılır.
- `groq + ollama` havuzu güçlü sayılır.
- küçük model için daha dar core araç seti vardır.
- `TOOL_YONLENDIRME` küçük modelde prompttan düşürülmemelidir.

Önemli sınır: Dosyanın kendi açıklamasına göre bu test sınıflandırma/sözleşme davranışını doğrular; canlı model başarısını tek başına kanıtlamaz.

## 5. Timeout / fallback: doğrulanmış mevcut ünite testi

`tests/test_router.py` bugünkü `master`da mevcut.

Doğrulanan davranışlar:

- ilk sağlayıcı hata verirse sıradaki sağlayıcı denenir;
- timeout hatası 60 saniyelik kısa cooldown alır;
- sonraki istekte timeout alan sağlayıcı cooldown boyunca atlanır;
- 429 rate-limit 120 saniyelik daha uzun cooldown alır.

Bu testler sahte istemcilerle, ağ kullanmadan çalışır.

## 6. Canlı failover kanıtındaki boşluk

24 Ağustos tarihli geçmiş committe `tests/live/test_provider_failover.py` ile canlı sağlayıcı/failover test hattı kurulmuş ve o tarihte 11/11 canlı test raporlanmıştı.

Bugünkü `master`da `tests/live/test_provider_failover.py` bulunamadı ve kod aramasında da sonuç yok.

Sonuç:

- canlı failover geçmişte ölçülmüş;
- bugünkü HEAD için aynı canlı test artık mevcut değil;
- FAZ 0 timeout/fallback maddesi yalnız mevcut ünite testine dayanarak `[x]` yapılamaz;
- gerçek ortam ölçümü ayrıca gerekir.

## 7. Prompt, profil, geçmiş ve araç yükü — ilk sayısal baz

Bugünkü `master` kaynak metinleri doğrudan sayıldı. Profil, geçmiş ve kullanıcı mesajı eklenmeden önce sabit blokların karakter yükü:

| Blok | Karakter |
|---|---:|
| `KIMLIK_BLOGU` | 190 |
| `KISILIK` | 1.867 |
| `TOOL_YONLENDIRME` | 791 |
| `OLCU_YONLENDIRME` | 251 |
| `BIKIMLONDIRME_YONLENDIRME` | 613 |
| **Sabit toplam** | **3.712** |

Bu değer token tahmini değildir; kaynak metindeki gerçek karakter sayısıdır.

Küçük model core araç seti 4 araçtır:

- `web_search`
- `add_task`
- `list_files`
- `read_file`

Bu dört araç şeması kompakt JSON gösteriminde yaklaşık **1.325 karakter** ek yük oluşturur.

### Profil yükü

`memory/profil.py` mevcut yapıda:

- ad: en fazla 80 karakterlik tek değer,
- tercihler: en fazla 30 kayıt,
- bilgiler: en fazla 30 kayıt,
- her kayıt: en fazla 80 karakter

tutabiliyor.

Bu sınırların tamamı dolduğunda `blok()` çıktısının teorik büyüklüğü yaklaşık **5.091 karakter** olur.

### Geçmiş yükü

`_chat_legacy.py` içinde `GECMIS_KILO_LIMITI = 4000`.

`_gecmis_pencere` yeni mesajlardan geriye doğru yaklaşık 4.000 karakterlik pencere oluşturuyor. Ancak mevcut test sözleşmesine göre en yeni tek mesaj limitten büyük olsa bile bütün olarak korunuyor; dolayısıyla gerçek geçmiş yükü bazı durumlarda 4.000 karakteri aşabilir.

### Birleşik yük resmi

Normal dolu profil + yaklaşık 4.000 karakter geçmiş varsayımıyla:

- ilk araçsız streaming turu: **3.712 + 5.091 + 4.000 = yaklaşık 12.803 karakter** + kullanıcı mesajı,
- gerçek tool-call yoluna geçildiğinde küçük core araç şemaları da eklenirse: **yaklaşık 14.128 karakter** + kullanıcı mesajı.

Bu üst-sınır örneğidir; her tur bu kadar dolu değildir. Ancak küçük modelin ağırlaşmasının sadece "çok araç"tan değil, sabit prompt + tüm profil + geçmiş birleşiminden de gelebileceğini ölçülebilir hale getirir.

### Kimlik yükünde ayrıca doğrulanmış çelişki

- `KIMLIK_BLOGU`: `Sen Edercanım'sın` diyor.
- `KISILIK`: önce `Sen Başak'sın`, sonra `sen Edercanım'sın`, ardından `kendine asla Edercanım deme` diyor.

Bu FAZ 0'da ayrı mevcut hata/bağlam gürültüsü olarak tutulur; henüz düzeltme yapılmaz. Harness A/B ölçümünde aynı çelişkinin etkisi ayrıca gözlenmelidir.

## 8. Şu ana kadarki FAZ 0 durumu

### Kanıtlandı

- [x] Bugünkü `master` commitini değişmez referans/baz çizgisi olarak kaydet.
- [x] Sabit system prompt karakter yükünü kaynak üzerinden ölç.
- [x] Küçük model core araç sayısını ve yaklaşık şema karakter yükünü ölç.
- [x] Profil bloğunun teorik üst karakter yükünü ölç.
- [x] Geçmiş penceresinin 4.000 karakter hedefini ve aşım davranışını doğrula.

### Statik/ünite düzeyinde incelendi, canlı ölçüm bekliyor

- [ ] Normal sohbet kalitesi.
- [ ] Dosya bulma ve dosya okuma başarısı.
- [ ] Web araştırma başarısı.
- [ ] Gereksiz araç çağrısı.
- [ ] Doğru araç seçimi.
- [ ] Araçsız streaming vs gerçek tool-call A/B.
- [ ] Timeout/cooldown/fallback gerçek zinciri.
- [ ] Cevap süresi ve toplam tur sayısı.
- [ ] Uydurma oranı.
- [ ] Görevin gerçekten tamamlanma oranı.

## 9. İlk ölçüm kararı

**KANITLANDI:** sabit baz çizgisi oluşturuldu.

**KANITLANDI:** prompt + profil + geçmiş + küçük core araç yükünün büyüklüğü kaynak koddan sayısallaştırıldı.

**KANITLANMADI:** streaming yolunun araç kullanımını gerçekten ne kadar bozduğu. Mevcut kod/test bunun mümkün olduğunu gösteriyor fakat oran bilinmiyor.

**KANITLANMADI:** bugünkü HEAD'in canlı timeout/fallback başarısı. Ünite testi var, güncel canlı test yok.

Bu nedenle henüz davranış değiştiren kod yazılmayacak.

## 10. Sıradaki ölçüm

Önce aynı görev kümesinde iki yol karşılaştırılacak:

A. Bugünkü mevcut akış: önce streaming, gerekirse tool-call.  
B. Deney yolu: araç gerektiği bilinen görevde doğrudan tool-call.

İlk görev grupları:

- `Masaüstündeki dosyaları göster.`
- `Şu dosyanın içinde ne yazıyor?`
- `Bugünkü güncel bir bilgiyi webde araştır ve kaynağını söyle.`
- `Merhaba, nasılsın?` (araç gerektirmeyen kontrol)

Ölçü:

- doğru araç çağrıldı mı
- araçsız cevapla kaçtı mı
- doğru sonuç verdi mi
- kaç tur kullandı
- süre
- prompt/araç yükü
- doğrulanmamış bilgi üretti mi

Bu A/B ölçümü çıkmadan streaming veya tool yönlendirme kodu değiştirilmez.
