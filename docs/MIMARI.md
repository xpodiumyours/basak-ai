# MIMARI — Başak × freetools Usta Planı

**Tarih:** 2026-09-28 · **Dal:** `feat/freetools-koprosu` · **Karar:** Casper (onaylı plan)

> Bu dosya `docs/MIMARI.md` ustam planının teknik özetidir. Günlük kod
> kuralları `AGENTS.md` ve `CHATBOT-YASAGI.md`'dedir; çelişki olursa onlar
> geçerlidir.

## 1. Vizyon (tek cümle)

Başak, tek bir ajan çekirdeği (beyin + yetenek alanı + araç disiplini) üzerinde
çalışan; üç çalışma yüzeyi (masaüstü, web, telegram), iki araç kaynağı (Başak
araçları, freetools köprüsü) ve üç gelir kaynağı (reklam, bağış/sponsor, SEO
trafiği) taşıyan; her katmanın ayrı sürüm, test ve yayın kapısı olan bir
platformdur.

## 2. Katmanlar

```
┌──────────────── SUNUM (Presentation) ────────────────┐
│ ui/ masaüstü (pywebview) · web/ (Vercel) · telegram  │
│ Hepsi tek HTTP kapısına (app.py) konuşur             │
├──────────────── AJAN ÇEKİRDEĞİ ──────────────────────┤
│ chat/flow.py → agent_protocol.py (yetenek_ac)        │
│ → tools.py (çağrı döngüsü)                           │
│ Yasak: kelime tetikleyici, cevaba dokunma, model     │
│ ayrımı (CHATBOT-YASAGI.md + bekçi testi)             │
├──────────────── ARAÇ KATMANI ────────────────────────┤
│ Başak araçları: tools/definitions.py + calistir()    │
│ (4 yer kuralı)                                       │
│ freetools köprüsü: tools/freetools_kopru.py          │
│ (Playwright, beyaz liste, fail-open)                 │
│ Web araçları: istemci JS (yerel-önce) + derin        │
│ bağlantı                                             │
├──────────────── BEYİN (Provider Chain) ──────────────┤
│ brain/registry.py VARSAYILAN_SIRA — ölçüme göre      │
│ dizilir; ücretsiz zincir korunur, yeni anahtar yok   │
├──────────────── VERİ & KİMLİK ───────────────────────┤
│ memory/ (SQLite/Postgres) · Basak ID (kayıtsız,      │
│ cihaza bağlı) · oturum geçmişi · KVKK envanteri      │
├──────────────── GELİR & TRAFİK ──────────────────────┤
│ /araclar/* SEO sayfaları · çerez onayı → reklam ·    │
│ bağış/sponsor · ölçüm sayacı                         │
├──────────────── KALİTE KAPISI ───────────────────────┤
│ pytest · test_chatbot_yasagi bekçisi · CI ·          │
│ tests/live · preview'da birlikte test → onay → main  │
└──────────────────────────────────────────────────────┘
```

## 3. Değiştirilemez mimari ilkeler

1. **Tek beyin, çok yüzey.** Yeni arayüz eklenirse mevcut HTTP kapısı
   (`app.py`) kullanılır; ikinci beyin, ikinci sohbet yolu kurulmaz.
2. **Araç = 4 yer.** Şema (`tools/definitions.py`) · dispatcher
   (`tools/__init__.py`) · yetenek alanı (`chat/agent_protocol.py`) · durum
   metni (`chat/tools.py`). Beşinci yer yok; kod tekrarı yok.
3. **Model seçer, kod yönlendirmez.** Kelimeye/tetikleyiciye dayalı araç
   açma yok (CHATBOT-YASAGI.md).
4. **Fail-open köprü.** freetools köprüsü düşerse sohbet kırılmaz; Başak
   kendi araçlarıyla devam eder. Köprü hiçbir zaman cevap yolunun tek
   bağımlılığı değildir.
5. **Yerel-önce.** Veri cihazdan çıkmayı gerektirmiyorsa çıkmaz. Web'de
   araç hesaplaması mümkün olduğunca kullanıcının tarayıcısında yapılır
   (freetools.org'un da uyguladığı model).
6. **Nazik otomatik erişim.** Üçüncü taraf sitelere yalnız robots.txt'nin
   izin verdiği ölçüde, timeout + önbellek + istek limitiyle erişilir.

## 4. freetools köprüsü — mimari kararlar (Faz 1)

| Karar | Değer | Gerekçe |
|---|---|---|
| Yürütme ortamı | Playwright headless (masaüstü) | Araçlar tarayıcıda (JS) çalışıyor; API yok |
| Web'de | Canlı köprü YOK → derin bağlantı + istemci JS | Vercel: 60 sn, ~500 MB sınır; Chromium sığmaz |
| Erişim alanı | Yalnız `*.freetools.org` beyaz listesi | SSRF savunması (`_guvenli_adres` ile aynı mantık) |
| Timeout | 20 sn | Kullanıcı bekletmez; zincir devam eder |
| Önbellek | Aynı girdi için sonuç önbelleği (kısa TTL) | Siteyi yormama + hız |
| İstek limiti | Günlük istek sınırı | Nazik erişim; kötüye kullanım kapalı |
| Hata modu | Fail-open (köprü yoksa araç açılmaz, sohbet bozulmaz) | 4. ilke |
| Kod lisansı | freetools kodu KOPYALANMAZ; standart algoritma kendi kodumuz | Telif |
| Marka | "freetools.org" yalnız kaynak/atıf olarak; ortaklık izlenimi yok | Marka hukuku |

## 5. Faz haritası ve kapılar

| Faz | İçerik | Çıkış kapısı |
|---|---|---|
| 0 | Bu doküman + KVKK envateri + test senaryoları | Commit, temel yeşil |
| 1 | freetools köprüsü (masaüstü) | pytest + canlı test + preview'da birlikte test |
| 2 | Web araçları (derin bağlantı + istemci JS + kota) | Preview'da gözle + konuşma testi |
| 3 | Gelir: SEO, çerez→reklam, bağış, hukuki taslak | Taslakların sana teslimi |
| 4 | Ortak kabul testi | 666+ test yeşil + senin "olur"un |
| 5 | Yayın | Senin açık onayın + avukat/mali müşavir notu |

Her faz ayrı dal, ayrı commit. Preview'da birlikte test edilmeden sıradakine
geçilmez; `main`'e sen onaylamadan hiçbir iş girmez.

## 6. Bilişsel yük haritası (kim ne yapar)

- **Casper:** kapsam, "olur/olmaz", hukuki taslak onayı, yayın onayı.
- **Ajan (Buffy):** kod, dal/PR, test, güvenlik, deploy, preview raporu
  (ekran görüntülü), ölçüm, taslak metinler.
- **Uzman (sonra):** avukat (KVKK/şartlar), mali müşavir (gelir vergisi).
