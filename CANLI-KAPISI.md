# CANLI-KAPISI.md — Gerçek Dayanıklılık Kanıt Kapısı (24 Ağustos 2026)

İlke: **Güvenilirlik yüzlerce ünite testle değil, gerçek modeller, gerçek
dosyalar ve gerçek kesintiler altında kanıtlar.** Bu belge kabul ölçütlerini
ve her birinin ÖLÇÜM YÖNTEMİNİ sabitler. Ölçülemeyen satır "kanıt" sayılmaz.

## Çalışma sırası

```text
Canary modu → güvenlik saldırı testleri → canlı model testleri
→ hafıza yaşam döngüsü → görev/çökme kurtarma (job queue)
→ 8 saat kullanım sonda → sonuç raporu → sınırlı canlı kullanım
```

## Canary modu (Faz 1 — KURULDU)

`ayarlar.json`:

```json
{
  "calisma_modu": "canary",
  "izinli_projeler": ["vixrex"]
}
```

- `yazma` etiketli TÜM araçlar kapalıdır (onay kuyusu olmadığından
  "önce onay iste" yerine daha sıkı olan TAM ENGEL seçildi)
- `sistem` araçları opt-in anahtarı açılsa bile KAPALI kalır
- Dış projeler yalnız `izinli_projeler` listesinden okunur
- Salt-okunur + internet akar; her engel kullanıcıya CANARY gerekçesiyle söylenir
- Kod karşılığı: `tools/permissions.py calisma_modu()` + `file_ops._canary_dis_izinli`

## Kabul tablosu ve ölçüm yöntemi

| # | Ölçüm | Zorunlu | Ölçüm yöntemi | Durum |
|---|---|---|---|---|
| 1 | Yetkisiz dosya/sistem işlemi | 0 | `tests/test_savunma.py` + canary | ✅ Faz 1 |
| 2 | Gizli bilgi sızıntısı (log) | 0 | `_kirmala` testleri + log taraması | ✅ Faz 1 |
| 3 | Kontrolsüz ücretli çağrı | 0 | `test_router.py` + audit taraması | ✅ Mevcut |
| 4 | Model cevabının izni değiştirmesi | 0 | enjeksiyon testleri (savunma paketi) | ✅ Faz 1 |
| 5 | 8 saatte çökme | 0 | sonda modu (Faz 4) | ⏳ |
| 6 | Görev kaybı / yarım görev | 0 | `tests/test_is_kuyrugu.py` (Faz 3) | ✅ Kuruldu — süreç yeniden doğumu kanıtlı |
| 7 | Yeniden başlatınca devam | %100 | `tests/test_is_kuyrugu.py` (Faz 3) | ✅ Kuruldu — OS-restart provası Faz 4'te |
| 8 | Model failover başarısı | ≥%95 | `tests/live/test_provider_failover.py` (Faz 2) | ✅ Kuruldu — ilk koşum 4/4 |
| 9 | İzinli araç başarı oranı | ≥%95 | sonda raporu (Faz 4) | ⏳ |
| 10 | Temizlenen hafızanın geri gelmesi | 0 | `tests/live/test_memory_lifecycle.py` (Faz 2) | ✅ Kuruldu — ilk koşum 4/4 |
| 11 | Kanıtsız durum iddiası | 0 | olcu.py kapısı istatistiği (Faz 4 raporu) | ⏳ |

## Faz 2 durumu (2026-08-24)

`tests/live/` kuruldu; normal pytest'te otomatik ATLANIR, yalnız
`python -m pytest tests/live --live -q` ile koşar. **İlk gerçek koşum:
11/11 geçti (36 sn)** — açılış provası, geçersiz anahtarla gerçek HTTP
devri, kapalı portta açık hata, ücretli engeli, kapat-aç hatırlama,
temizlik semantiği, bin kayıt budamasında önemli anının korunması,
tekrar kayıt dedupe. Raporlar: `data/canli-rapor/`.

## Canlı hat disiplini (Faz 2 kuralları)

- `tests/live/` testleri NORMAL pytest koşusunda ATLANIR;
  yalnız `pytest tests/live --live` ile çalışır (kota harcar, servis ister)
- Her canlı test kendi sonucunu `data/canli-rapor/` altına JSON yazar
- Başarısız canlı test = faz kapanmaz; "canlıda düştü" meşru bulgudur

## Job queue (Faz 3 — KURULDU: `tools/is_kuyrugu.py`)

Saklama: plan taslağındaki 4 ayrı dosya YERİNE tek `data/jobs/kuyruk.json`
+ atomik yazım (tmp+rename) — çökme iki dosya arasında yakalanırsa görev
bölünür; tek dosyada durum her zaman tutarlıdır. Planın `durum` alanı
job içinde aynen korunur.

Alanlar: `id, baslik, adimlar[], mevcut_adim, calisan_adim, durum,
maksimum_deneme, deneme_sayisi, son_hata, kullanici_onayi,
onay_gerekli, ciktilar`.

Garantiler (testle kilitli):
- Her adım ÖNCE `calisiyor`+`calisan_adim`, SONRA `mevcut_adim+1`
  olarak diske yazılır → çökmede kaldığı yer görünür
- ONAYLANMIŞ adım asla iki kez koşmaz; yarım kalan adım en fazla
  `maksimum_deneme` kez denenir (adımlar idempotent yazılmalı)
- `sure_butcesi` / ayarlardaki `maksimum_gorev_suresi` dolunca iş
  BEKLIYOR'a döner — sonraki `kos_bekleyenleri()` çağrısı kaldığı
  adımdan sürer ("kota açılınca devam")
- `onay_gerekli=True` işler `onayla(id)` edilene kadar atlanır

ENTEGRASYON NOTU: Kuyruk bağımsız modül olarak kabul testlerinden
geçti; zamanlayıcıya/sunuma bağlanması ayrı küçük dilimdir (Faz 3b).

## Sonda (Faz 4)

Toplanacak alanlar: model+seçim gerekçesi, yanıt süresi, token, araç
başarısı, failover sayısı, yetki engeli, çökme. Kaynak: `data/model_stats.db`
+ `data/audit/audit.log` + `arac.log`. Rapor üretici bu üçünü birleştirir.
