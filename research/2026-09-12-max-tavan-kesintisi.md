# ARAŞTIRMA — max_tokens TAVANI GERÇEK CEVAPLARI KESİYOR

Tarih: 2026-09-12
Durum: KANITLANDI — KOD DENEYİNE İZİN
Risk sınıfı: Düşük (tek sabit; davranış yalnız tavana vuran uzun cevaplarda değişir)

## 1. Hedef

Ücretsiz zincirde `max_tokens=1024` tavanına takılıp yarım kalan cevapları onarmak:
10 adaptör + streaming yolunda tavan 1024 → 2048. Kilo (`VARSAYILAN_JETON=1500`,
ölçülü gerekçesi dosya başında) ve NVIDIA-büyük (zaten 2048) HARİÇ tutulur.

## 2. Kabul kriteri

- `pytest tests -q` yeşil (test_kilo `>=1500` pini korunur).
- Canlı auditte `token_out=1024` kümesi erir; `_bitis=length` alarmı susar.
- Kısa cevapların token tüketimi değişmez (tavan harcanan değil, üst sınırdır).

## 3. Mevcut durum kanıtı

- `data/model_stats.db` son 72 saat: `token_out` TAM 1024 olan BAŞARILI çağrı
  kümesi — nvidia 11, groq 7, openrouter 5 (toplam 23). Doğal dağılımda en
  üst 10 değerin tamamının birebir 1024 olması tavan kanıtıdır.
- Tüm adaptörlerde `"max_tokens": 1024` (grep kanıtı, 2026-09-12).
- Kullanıcı ekranında kısa cevaplar tavan ALTINDA bitti (prob: 703 karakter) —
  o şikâyetin kökü incelik + bekleme; AMA tavan da gerçek kesinti üretir (23 vaka).

## 4. Sorun kanıtı

Yukarıdaki 23 vaka + kullanıcı şikâyeti ("cevap kesik"). Kısa-cimri cevaplar
ayrı kökten (harness görev kalıpları) — bu paket yalnız gerçek kesintiyi kapatır.

## 5. Dış referans

- Groq gpt-oss-20b TPM duvarı ~8000/dk (audit 429 kayıtları): 2048 tavanla
  dakikada 3-4 uzun cevap sığar; kısa cevaplar etkilenmez.
- OpenAI best practice: tavan, harcanan değildir — yükseltmek kısa isteklerin
  kotasını değiştirmez.

## 6. Doğrulanan gerçekler

- Tavan kümesi SQL ile sayıldı; adaptör grep'i yapıldı; kilo/nvidia istisnaları
  koddan okundu.

## 7. DOĞRULANAMADI

- 2048'in de vurulduğu vaka henüz YOK (gözlenirse ayrı paket).

## 8. İzin verilen kapsam

- 10 adaptörde `1024 → 2048` (+ ilgili hız yorumları), `brain/yayin.py:52`,
  `brain/nvidia.py` küçük-model dalı. Kilo ve nvidia-büyük DOKUNULMAZ.

## 9. Yasak kapsam

- temperature, timeout, provider sırası, tool seti, promptlar — dokunulmaz.
- GLM timeout salgını (24 saatte ~394) bu pakette DEĞİL — FAZ1 ölçümüne not
  edildi (aşağıya bak).

## 10. Korunacak davranışlar

- Kısa cevapların uzunluğu/kotası değişmez; test_kilo pini korunur.
- `stats` token muhasebesi aynen çalışır.

## 11. Risk sınıfı

Düşük. Sensör: tam paket + audit tavan-kümesi takibi.

## 12. Kabul sensörleri

`pytest tests -q`, `py_compile`, canlı `token_out=1024` sayımı + `_bitis` alarmı.

## 13. Geri alma koşulu

TPM-429 artışı veya test gerilemesi olursa tek commit geri alınır.

## 15. Sonuç (2026-09-12 uygulandı)

- 10 adaptör + streaming + nvidia-küçük dalı 2048'e çıktı; kilo/nvidia-büyük korundu.
- `_bitis` alarmı eklendi (`brain/kullanim.py` + brain uyarısı); yan etki (kilo exact-dict testi) yakalanıp düzeltildi — alarm yalnız şüpheli bitişlerde işaretler.
- Sensörler: `pytest tests -q` = 566 geçti / 0 hata. Tavan-kümesi takibi canlıda sürecek.
- KANITLANDI → paket tamamlandı (commit bekliyor).

## 14. FAZ1'e not (bu paket DIŞI gözlemler)

- GLM 24 saatte ~394 timeout (`Request timed out` 297 + `read operation` 97),
  başarı %62. Her vaka ~12 sn donma. Timeout değeri körü körüne değişmedi;
  maliyet-bilinçli sıralama FAZ1 ölçüm konusudur.
- `model_stats.db` içinde test artığı (`'patladi'` hataları) var — testler üretim
  istatistik DB'sine yazıyor; karne verisi kirleniyor. conftest izolasyonu
  ayrı paket ister.
- Cloudflare 403 (47) + 401 (33)/24sa: P3 uzun pas-geçme devrede, zincir sağlıklı.
- `'Brain' object has no attribute '_ollama'` ×17: yerel fallback yolunda
  kurulum eksiği şüphesi — ayrı paket ister.
