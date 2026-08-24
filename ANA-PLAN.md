# ANA-PLAN - Yapi-Garantiye Gecis Programi

> **Plan zinciri:** Bu ilk program tamamlandıktan sonra
> [ANAPLAN-SONRASI-PROFESYONEL-MIMARI.md](./ANAPLAN-SONRASI-PROFESYONEL-MIMARI.md)
> uygulanır. Her iki planın OpenAI ve Anthropic resmî belgelerine göre ortak
> güvenlik, kalite, şeffaflık ve verimlilik ölçütleri
> [Resmidökümanuyum.md](./Resmidökümanuyum.md) belgesinde tanımlanır; o
> belgedeki **Ortak Çalışma Sözleşmesi** (§7) bu planın üst normudur.

> Sahip: mimar ajan. **Yetki kapsami (2026-08-24 revizyon, Casper onayli):**
> Mimar ajan yalnız Casper'in açıkça verdiği görev kapsamı içindedir.
> Salt-okunur inceleme değişiklik yetkisi vermez. Yazma, dış sistem etkisi,
> hassas veri gönderimi ve kapsam genişletme ayrı yetki sınıflarıdır;
> model/ajan kendi yetkisini veremez, genişletemez veya devredemez.
> Bağlayici hedef soz: "Mevcut temeli yikmadan, kural-prompt'tan
> yapi-garantisine gecen bir Basak; kirilgan katmanlar olculebilir ve yapisal
> olacak." Celistiginde bu dosya degil, soz kazanir.

## Ilke

- Mevcut temel yikilmaz: guncel testlerin TAMAMI yesil kalir (sabit sayi
  kullanilmaz — DURUM/CI listesi esastir), davranis gerilemez.
- Her faz cikista: testler yesil + eval gerilemesi YOK + defter kaydi +
  AGENTS.md maddesi + DURUM.md olcumu.
- Kural-prompt'ta kalan her sey suclu until delilidir (guilty until proven).
- **Ortak faz kapisi:** faz; temsilî normal/uç/saldırgan vakalarda ölçüm,
  kritik olay sifir (yetkisiz eylem, sır sızıntısı, veri kaybı, yanlış başarı
  bildirimi), sürüm kaydı ve denenmiş geri dönüş adımı olmadan kapanmaz.
  Başarısızlıkta önceki kararlı sürüm varsayılan kalır.

## FAZ 0 - Olcum Citasi (TAMAM 2026-08-24)

| # | Is | Durum |
|---|---|---|
| 0.1 | Eval bankasi + puanlayici (`tests/eval/`) + canli taban (%33.3 / 4 sizinti) | TAMAM |
| 0.2 | Saglayici veri karti: model/snapshot, gönderilen alanlar, saklama, abuse monitoring, ZDR, üçüncü taraf, doğrulama tarihi | ACIK — kart dolana kadar yeni saglayici (DeepSeek/Kimi dâhil) zincire girmez |
| 0.3 | Iz sozlesmesi: `run_id`/`call_id`/`conversation_id`, maskeleme, saklama suresi | ACIK |
| 0.4 | Eval seti gelistirme: soru basina coklu deneme (5), saldirgan/tuzak kategorisinin genisletilmesi, kod+insan grader kalibrasyonu | ACIK |

## FAZ 1 - Yapısal Çikiş Kapisi (SOZUN ILK MADDESI)

Sorun: `olcu.py` regex/string kapisi + `PROMPT_BLOGU` isaret dayatmasi
model degisince sessiz bozulur; "olum birimi" string eslestirme.

| # | Is | Durum |
|---|---|---|
| 1.1 | Cevap sozlesmesi `{yanit, iddialar}` + yapi threading (10 saglayici) | TAMAM (49 test) |
| 1.2 | Kapı v2: iddia->kanit yapisal baglama; uyumluluk modu korunur | TAMAM |
| 1.3 | chat.py tek sözleşme entegrasyonu | TAMAM |
| 1.4a | Canli A/B gece koşusu: sızıntı 5>4 → `sozlesme_modu=kapali` GERİ ÇEKİLDİ (kural uygulandı) | TAMAM |
| 1.4b | **Yapısal sonuç durum makinesi:** `ok/refusal/incomplete/invalid`; JSON bozuksa tek kontrollü düzeltme denemesi; sonra eski kapıya düşüş. Gerekçe resmî: DeepSeek boş-content hatası + Kimi length-truncation uyarısı (`defter/saglayici-dokuman-arastirmasi.md`) | ACIK |
| 1.4c | Sözleşme modunda yeterli `max_tokens` + `finish_reason` denetimi | ACIK |
| 1.4d | Groq "tool choice is none" 400 düzeltmesi (temiz A/B ön koşulu): son turda araçsızken gelen tool_call'a karşı tek nudge'lı retry | ACIK |
| 1.4e | Temiz havuzda A/B tekrarı (glm ayakta, groq dinlenmiş). Kabul: sızıntı < taban VE disiplin ≥ taban; sağlanamazsa FAZ 4'e ertelenir | ACIK |

**Araç ve izin sınırı (ortak madde):** Web, belge, bellek ve araç çıktıları
güvenilmeyen veridir; ayrıcalıklı talimat alanına taşınamaz. Model yalnız
öneri üretir; yürütme kayıtlı araç + izin alt kümesi + politika ile olur.
Kritik/dış etkili işlem tek çağrılık hedef+etki onayı ister (P6/P7'de).

## FAZ 2 - Donus Kuyrugu + Iptal

| # | Is | Cikis kritery |
|---|---|---|
| 2.1 | Mesaj-basina-thread yerine tek isci donus kuyrugu (`tools/is_kuyrugu.py` temel) | Paralel mesaj sirali islenir |
| 2.2 | Iptal: konusurken kesme, TTS durdurma, thread-safe iptal bayragi; kullanıcı iptali derhal işlenir | Iptal testleri |
| 2.3 | UI iptal dugmesi + orb durumu | Casper canli dogrulama |

## FAZ 3 - Durum Konsolidasyonu

| # | Is | Cikis kritery |
|---|---|---|
| 3.1 | `gorevler.json` -> SQLite (tasks API imzasi korunur); tek yazar + WAL disiplini | Eszamanlilik testleri DB uzerinde |
| 3.2 | Coklu surec karari (tray/zamanlayici): dosya kilidi VEYA tek-yazar; ADR deftere | ADR kaydi |

## FAZ 4 - Model Stratejisi

| # | Is | Cikis kritery |
|---|---|---|
| 4.1 | A/B: qwen2.5:3b vs adaylar (güçlü JSON üreticileri öncelikli: kimi-k3/k2.7-class, deepseek-v4-class — VERİ KARTI ŞARTIYLA), aynı eval bankasında 5 deneme | Karar raporu defterde |
| 4.2 | Kazanirsan: varsayilan degisim + prompt hafifletme | Eval gerilemesi yok |
| 4.3 | Model/prompt/şema/araç sürümleri birlikte pinlenir; değişiklik shadow/canary olmadan varsayılan olamaz | Sürüm kaydı |

## FAZ 5 - Dagitim ve Dayaniklilik

| # | Is | Cikis kritery |
|---|---|---|
| 5.1 | Paketleme (pyinstaller onedir) + kisayol | Sifir-kurulum denemesi |
| 5.2 | `data/` gunluk yedek (7 günlük) — SQLite Online Backup/VACUUM INTO ile tutarlı snapshot; canlı DB dosya kopyası yedek sayılmaz | Restore provası temiz profilde; yedek mesaji restore kaniti DEGILDIR |
| 5.3 | API anahtarlarının düz ayar dosyasından DPAPI korumalı depoya geçişi | Anahtar düz metinde kalmaz (log/yedek dâhil) |

## Yonetim Kurallari

- Alt ajanlar kesif/kod yazar; birlesen ve onaylayan mimardır. Mimarin yetkisi
  baştaki kapsam metniyle sınırlıdır; genişletme Casper onayı ister.
- Tamamlanan/asilan gorev belgeleri silinmez, `_arsiv/`e tasinir (kanit kulturu).
- GOREV_LISTESI.md ozellik biriktiricisidir; program sirasi bu dosyada yurur.
- Casper canli onayi gereken yerler: FAZ 2.3 (UI hissi), FAZ 4.2 (model sesi),
  herhangi bir yetki/genişletme talebi.
- Bu plan bittiginde AGENTS.md "Sonraki ozellikler" ile senkronlanır.
