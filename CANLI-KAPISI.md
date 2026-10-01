# CANLI KAPISI — gerçek model, gerçek ağ, gerçek kota

**Yazan:** ölçüm turu, 2026-10-01 · **Dayanak:** `conftest.py`,
`.github/workflows/test.yml`, `tests/live/`

Bu belge 4 dosyada anılıyordu (`conftest.py`, `tests/live/test_boot.py`,
`tests/live/test_memory_lifecycle.py`, `docs/MVP-PROFESYONEL-PLANI.md`) ama
**dosya hiç oluşmamıştı**. Kural kodda vardı, yazıda yoktu. Burada yazılıyor.

---

## 1. Kapı nedir

`tests/live/` altındaki testler **gerçek para değil ama gerçek kotayı**
 harcayan testlerdir: gerçek bir model çağrısı, gerçek HTTP, gerçek
Postgres. Normal `pytest` koşusunda **hiçbiri çalışmaz**.

Mekanizma (`conftest.py:20-28`):

```python
def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return
    skip = pytest.mark.skip(reason="canlı hat — --live gerekli")
    for item in items:
        yol = str(item.fspath).replace("\\", "/").lower()
        if "/tests/live/" in yol:
            item.add_marker(skip)
```

Yani: klasörün adına bakar. `--live` verilmezse oradaki **her** test
`canlı hat — --live gerekli` gerekçesiyle atlanır. Klasör yolunda geçen
her test, ismi ne olursa olsun atlanır.

**Normal koşu ölçülen sonuç (2026-10-01): 1108 geçti, 19 atlandı.** 19'un
tamamı budur. Dağılım:

| Dosya | Atlanan |
|---|---|
| `test_freetools_canli.py` | 5 |
| `test_memory_lifecycle.py` | 4 |
| `test_boot.py` | 3 |
| `test_agent_canli.py` | 2 |
| `test_goz_imtihani.py` | 1 |
| `test_katalog_canli.py` | 1 |
| `test_postgres_hafiza.py` | 1 |
| `test_seviye1_native.py` | 1 |
| `test_seviye2_pilot.py` | 1 |
| **Toplam** | **19** |

---

## 2. Neden kapı var — dört ölçülmüş sebep

1. **Kota.** Her canlı test gerçek bir sağlayıcı çağrısıdır. Groq'un
   günlük bütçesi 200.000 jeton; her `test_boot` çağrısı bunu yer.
   Normal koşu bunu istesek de yiyemez — her geliştirme turu sağlayıcı
   bütçesini tüketirdi.
2. **Anahtar gerekir.** Repo açık, anahtarlar commit'e girmez. CI'da
   sır yok; `test.yml:84` bunu açıkça yazıyor ("Sirlar CI'ya girmez").
   Anahtarsız koşan bir canlı test `SKIP` yazar — yani **sessizce geçer**.
3. **Ağ.** Gerçek HTTP çağrıları yerel koşuda kararsız. Bir sağlayıcı
   5 saniye gecikirse test kırmızıya döner ve bu bir **ürün hatası
   değildir**.
4. **Sahte kabul yasağı.** `knowledge/kabul-plani-web-gate.md` ve
   `tests/live/kosucu.py` bunu ayrıca yazıyor: yanıtın metni içinde
   JSON biçiminde `tool_call` yazması **geçerli kabul değildir**. Gerçek
   native protokol yanıtı olmalı. Bu denetimin sahte çıkmasını önlemek
   için izole ve kayıtlı koşu gerekir.

---

## 3. Kapıyı kim açar

```bash
python -m pytest tests/live --live -q
```

Gerekenler:

| Gereken | Neden |
|---|---|
| Sağlayıcı anahtarları (ortam değişkeni) | Gerçek çağrı |
| `tests/live/fixtures/` yazılabilir | Gerçek yanıt kalıbı kaydedilir |
| Postgres (`BASAK_OTURUM_ANAHTARI` değil, `test_postgres_hafiza.py` için DSN) | Gerçek kalıcı hafıza |

Çıktı: her test sonucu `data/canli-rapor/<zaman>_<test>.json` altına
yazılır (`tests/live/conftest.py:19-35`). Bu klasör **gitignore'dadır**
(`.gitignore:51`) — raporlar kalıcı değildir, her koşuda yeniden üretilir.

**Sonuç ne olursa olsun yazılır.** Atlanan hücre `SKIP` olarak rapora
düşer; tahminle doldurulmaz. Bu, kabul sözleşmesinin gereği: "anahtarı
olmayan sağlayıcının hücresi SKIP yazılır" (`tests/live/kosucu.py:11-12`).

---

## 4. CI'daki durum — dürüst kayıt (2026-10-01)

İki ayrı gerçek var ve ikisi de kayda geçti:

1. **Ana koşu canlı klasörü tamamen dışarıda bırakıyor.**
   `test.yml:89` ve `test.yml:118`:
   `python -m pytest tests -q --ignore=tests/live`.
   Yani CI **bu 19 testi hiç çalıştırmıyor** — atlamıyor, klasörü
   hiç toplamıyor.
2. **Sağlayıcı kabul işi ölü bir dal koşuluna bağlı.**
   `test.yml:96`:
   ```yaml
   if: github.event_name == 'pull_request' &&
       github.head_ref == 'preview/fatura-goz-cerrahi-20260927'
   ```
   Bu dal artık yok. Yani `provider-acceptance` işi **hiç koşmuyor**.

**Sonuç:** 19 canlı testin **hiçbir kaydı yok**. Bu bir tasarım kusuru
değil — kapının kendisi doğru. Kusur, kapının arkasındaki paketin
**hiç işletilmemiş** olması. Bu yüzden `docs/MVP-PROFESYONEL-PLANI.md`
P0.2'de bir kez kayıtlı koşu istiyor.

> **Dürüst sınır:** Bu turun yazımında canlı paket **koşmadı** —
> ortamda sağlayıcı anahtarı yok. Buradaki her sayı, kod okunarak
> ölçülmüştür; koşu çıktısı değildir.

---

## 5. Kapı kuralı — tek cümle

> Gerçek model, gerçek ağ veya gerçek kotaya dokunan hiçbir test
> `tests/live/` altında durur ve `--live` olmadan koşmaz.

Bu kuralın aracı yok; **düzen** yapar: yeni bir canlı test yazılırken
klasör koymak zorunlu kılınır (aksi halde sessizce anahtar ister ve
yoksayılır), CI'nin `--ignore` listesi onu zaten kapsar.

---

## 6. Bu belgeyi değiştirirken

- `--live` bayrağını `conftest.py`'den kaldırma: kuralın tek
  uygulaması orada, `pytest_collection_modifyitems` içinde.
- CI'daki `--ignore=tests/live` satırlarını (`test.yml:89`, `test.yml:118`)
  canlı koşuyu açmak için kaldırma — o zaman ana koşu 19 ek kotayı da
  yer. Ayrı bir iş gerekir.
- Bu belge bir **kural metnidir**, koşu raporu değildir. Rapor
  `data/canli-rapor/` altındadır ve kalıcı değildir.