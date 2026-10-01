# FAZ 5 — YAYIN GÜNÜ PLANI (yalnız Casper onayıyla işler)

**Tarih:** 2026-09-28 · **Dal:** `feat/freetools-koprosu`
Kural: bu listede Casper'ın açık "olur"u olmadan hiçbir üretim işlemi yapılmaz.

> ## ⚠️ 2026-10-01 DÜZELTMESİ — "tek üretim deployu" YANLIŞTI
>
> Bu belge “ajan `vercel --prod` calistirir, 1 deploy” diyordu.
> **Ölçüm bu yanlışı gösterdi: o ayrı adım yok.** Vercel `main`'e
> bağlı ve **`main`'e merge olması otomatik production deploy tetikler.**
>
> Kanıt (ölçüldü 2026-10-01):
> - PR #20 merge: `8067205`, **09:33:19Z**
> - Production deployment: **09:33:49Z** — yani merge'den **30 saniye** sonra
> - CI koşusu: 09:33:22Z, `success`
>
> Geri almak da aynı hızda olur: **bir merge = bir production deploy.**
> Bu yüzden geri alma `vercel --prod` ile değil, **merge geri alma**
> (revert commit) veya Vercel dashboard'dan önceki deployment'ı
> promote etmekle yapılır.
>
> **Değişen kural:** Kapı “deploy” değil, **merge öncesi kontrol**.
> Bu belgedeki 1. ve 2. maddeler aşağıda güncellendi.

## 0. Ön denetim (ajan yaptı, 2026-09-28)

| Kontrol | Durum |
|---|---|
| Kod: 851 test yeşil, chatbot yasağı 11/11 | ✅ |
| Preview: tüm Faz 2+3 sayfaları 200 (6/6 canlı doğrulandı) | ✅ |
| `BASAK_WEB_TOKEN` (yönetici kapısı) Production'da var | ✅ |
| `DATABASE_URL` (Postgres — kota + hafıza) Production'da var | ✅ |
| Model anahtarları (GROQ, GEMINI...) Production'da var | ✅ |
| `BASAK_OTURUM_ANAHTARI` Production'da | ❌ **EKLENECEK** |
| `BASAK_ANONIM_KOTA_TAVAN` Production'da | — isteğe bağlı (yoksa 50) |

> **P0.5 ölçümü (2026-10-01):** Canlıda `POST /api/kimlik` → **200** ve
> imzalı çerez dönüyor (`u9976591660579896`). Yani üretimde **en az biri
> tanımlı**. Hangisinin tanımlı olduğu **dışarıdan ayırt edilemiyor**:
> `kullanici.py:181` ikisini de kabul ediyor (`BASAK_OTURUM_ANAHTARI`
> önce gelir, yoksa `BASAK_WEB_TOKEN`) ve imza aynı anahtarla atılıyor.
> Kesin belirleme Vercel panelinden env listesine bakmayı gerektirir.
> *Bu bir varsayım değil, ölçülen sınırdır.*

## 1. Casper'ın yapacakları (sırayla, ~10 dakika)

1. **Oturum anahtarını ekle** (üretimde imzalı çerezin anahtarı):
   - Vercel → basak-vercel → Settings → Environment Variables
   - `BASAK_OTURUM_ANAHTARI` = uzun rastgele bir metin (32+ karakter)
     - üretebilirsin: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - Environment: **Production** (Preview'da gerekmez ama eklersen zarar yok)
2. **Preview'da 10 maddeyi test et** (BIRLIKTE-TEST-SENARYOLARI.md) → "olur"
3. **Merge onayı:** PR yeşil olduğunda `main`'e merge edilir. Merge
   otomatik olarak production deploy tetikler (ayrı deploy adımı YOK —
   yukarıdaki ölçüme bak).
4. Yayın sonrası ajan canlı denetim raporu verir (sayfalar + kota + kimlik)

## 2. Ajanın yayın günü yapacakları (onay sonrası)

- PR merge (**bu production deploy tetikler** — ayrı `vercel --prod` yok)
- Üretimde canlı denetim: `/`, `/araclar`, örnek araç sayfası, `sitemap.xml`,
  `robots.txt`, `/api/kimlik` (anonim ID üretmeli), kota davranışı
- `BASAK_ANONIM_KOTA_TAVAN` üretimde istenirse ayarlanır (varsayılan 50)
- Geri alma planı: sorun olursa **revert commit ile merge geri alma**
  (aynı hızda yeni bir production deploy oluşturur) veya Vercel dashboard →
  önceki production deployment → "Promote to Production" (ekstra deploy
  harcamaz)

## 3. Yayın sonrası görünürlük (Casper hesabıyla)

1. **Google Search Console:** mülk ekle (Domain) → DNS doğrulama
2. `https://<üretim>/sitemap.xml` gönder
3. Bir hafta sonra "Sayfalar" raporundan dizine eklenmeyi izle
4. (İsteğe bağlı) Bing Webmaster Tools — aynı sitemap

## 4. Hukuk/vergi görevleri (ajandan hatırlatma — Casper'ın işi)

| Görev | Kime | Not |
|---|---|---|
| KVKK aydınlatma metni + çerez politikası onayı | Avukat | `web/gizlilik.html`, `web/cerez.html` TASLAK; kaynak: `docs/KVKK-ENVANTER.md` |
| Kullanım şartları + sorumluluk reddi onayı | Avukat | `web/sartlar.html`, `web/sorumluluk.html` TASLAK |
| Bağış/sponsor gelir modeli | Mali müşavir | vergi beyanı, makbuz düzeni |
| (Reklam açılırsa) reklam ağının çerez beyanı | Avukat | onay akışı zaten koda gömülü |

## 5. Yayın kararı kapısı

- [ ] Casper: 10 madde testi "olur"
- [ ] Casper: `BASAK_OTURUM_ANAHTARI` eklendi
- [ ] CI yeşil (lint + pytest + preview deploy) — **merge öncesi son kapı**
- [ ] Casper: "Üretime çık" onayı → PR merge edilir; production otomatik deploy olur
