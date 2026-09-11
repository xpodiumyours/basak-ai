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

## 7. Şu ana kadarki FAZ 0 durumu

### Kanıtlandı

- [x] Bugünkü `master` commitini değişmez referans/baz çizgisi olarak kaydet.

### Statik/ünite düzeyinde incelendi, canlı ölçüm bekliyor

- [ ] Normal sohbet kalitesi.
- [ ] Dosya bulma ve dosya okuma başarısı.
- [ ] Web araştırma başarısı.
- [ ] Gereksiz araç çağrısı.
- [ ] Doğru araç seçimi.
- [ ] Araçsız streaming vs gerçek tool-call A/B.
- [ ] Timeout/cooldown/fallback gerçek zinciri.
- [ ] Prompt büyüklüğü.
- [ ] Araç sayısı ve araç şeması yükü.
- [ ] Cevap süresi ve tur sayısı.
- [ ] Uydurma oranı.
- [ ] Görevin gerçekten tamamlanma oranı.

## 8. İlk ölçüm kararı

**KANITLANDI:** sabit baz çizgisi oluşturuldu.

**KANITLANMADI:** streaming yolunun araç kullanımını gerçekten ne kadar bozduğu. Mevcut kod/test bunun mümkün olduğunu gösteriyor fakat oran bilinmiyor.

**KANITLANMADI:** bugünkü HEAD'in canlı timeout/fallback başarısı. Ünite testi var, güncel canlı test yok.

Bu nedenle henüz davranış değiştiren kod yazılmayacak.

## 9. Sıradaki ölçüm

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
