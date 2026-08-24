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
| 6 | Görev kaybı / yarım görev | 0 | job queue çökme testi (Faz 3) | ⏳ |
| 7 | Yeniden başlatınca devam | %100 | job queue resume testi (Faz 3) | ⏳ |
| 8 | Model failover başarısı | ≥%95 | `tests/live/test_provider_failover.py` (Faz 2) | ⏳ |
| 9 | İzinli araç başarı oranı | ≥%95 | sonda raporu (Faz 4) | ⏳ |
| 10 | Temizlenen hafızanın geri gelmesi | 0 | `tests/live/test_memory_lifecycle.py` (Faz 2) | ⏳ |
| 11 | Kanıtsız durum iddiası | 0 | olcu.py kapısı istatistiği (Faz 4 raporu) | ⏳ |

## Canlı hat disiplini (Faz 2 kuralları)

- `tests/live/` testleri NORMAL pytest koşusunda ATLANIR;
  yalnız `pytest tests/live --live` ile çalışır (kota harcar, servis ister)
- Her canlı test kendi sonucunu `data/canli-rapor/` altına JSON yazar
- Başarısız canlı test = faz kapanmaz; "canlıda düştü" meşru bulgudur

## Job queue taslağı (Faz 3'te inşa edilecek)

`data/jobs/{pending,running,completed,failed}.json`; alanlar:
`id, durum, mevcut_adim, maksimum_deneme, son_hata, kullanici_onayi`.
Kural: aynı adım iki kez koşamaz; kota açılınca kaldığı adımdan sürer.
`maksimum_gorev_suresi` ayarı bu fazda devreye girer.

## Sonda (Faz 4)

Toplanacak alanlar: model+seçim gerekçesi, yanıt süresi, token, araç
başarısı, failover sayısı, yetki engeli, çökme. Kaynak: `data/model_stats.db`
+ `data/audit/audit.log` + `arac.log`. Rapor üretici bu üçünü birleştirir.
