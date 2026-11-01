# Kurtarma Raporu — yetim dallar

- uretildi: 2026-11-01 11:04
- ureten: `python kurtarma/rapor_uret.py` (bu dosya elle duzenlenmez)
- commit: `85d5fe4`
- ttl_saat: 72
- komut: `C:\Users\Casper\AppData\Local\Programs\Python\Python312\python.exe -m pytest tests -q && C:\Users\Casper\AppData\Local\Programs\Python\Python312\python.exe -m py_compile app.py chat/capabilities.py chat/flow.py chat/inline_ordu.py chat/platform_context.py chat/tools.py tests/test_inline_ordu.py tests/test_yetenek_siniri.py tests/test_vercel_stream.py scripts/olcum/model_yetenek_olcumu.py && C:\Users\Casper\AppData\Local\Programs\Python\Python312\python.exe tools/sir_kapisi.py`

## Taban

- taban_dal: `feat/composio-schema-preview-20261031`
- taban_commit: `1f29c84` (2026-10-31 Validate Composio tool schemas against their documented shape and pin pre-verifier connections)
- dal: `kurtarma/yetim-dallar`
- uzak main: `f5a395a 2026-10-31` (Keep the browser identity stable when the session store is unreadable)
- main ile fark (yamayla): main 2 commit ileride, merge-tree cakismasi yok

## Kurtarilan

- `24fde49` feat(olcum): model araci, goruntusu ve kotasi canli olculdu
- `7ea41d9` mola sonrasi biten kosu yalan hata yollamaz; Devam et karti silinmiyor
- `ba71785` feat(ordu): ayni istek icinde paralel alt ajan (inline ordu)
- `e9e2c0f` Keep the sidebar identity chip from overflowing its box

Toplam: 4 commit (kurtarma dalinda `1f29c84..HEAD`).

## Atlanan

- `0581d13` — bu klonda ne ref ne nesne olarak yok; icerigine erisilemiyor
- `43e9a36` — ayni kapi tabanda var: chat/platform_connectors._oauth_prerequisites_ready + tests/test_platform_login_readiness.py
- `58e0989` — bu klonda ne ref ne nesne olarak yok; icerigine erisilemiyor
- `5f5d3b3` — bu klonda ne ref ne nesne olarak yok; icerigine erisilemiyor
- `7c39318` — ayni kapi tabanda var: chat/platform_connectors._oauth_prerequisites_ready + tests/test_platform_login_readiness.py
- `8adc2f5` — bu klonda ne ref ne nesne olarak yok; icerigine erisilemiyor
- `94b69da` — ayni kapi tabanda var: chat/platform_connectors._oauth_prerequisites_ready + tests/test_platform_login_readiness.py
- `d294f4a` — bulut iscisi hatti; ayni is chat/platform_agents.py deposunda baska yoldan yapiliyor
- `e5f1f8e` — bu klonda ne ref ne nesne olarak yok; icerigine erisilemiyor
- `efef640` — ayni kapi tabanda var: chat/platform_connectors._oauth_prerequisites_ready + tests/test_platform_login_readiness.py
- `feat/neon-email-login-20261028` — alternatif hesap/giris mimarisi (Neon Auth + e-posta); urun hatti platform_composio/private_access uzerinden yurudu, taban bu modulleri tanimiyor. Olcum: 15 eksik commit, bunlardan 4 tanesi tabana uygulanabiliyor (11 uygulanamiyor); parca tasimak yarim entegrasyon olurdu.
- `feat/openrouter-budget-commander-20261029` — opt-in ucretli komutan butcesi; taban saglayici kaydinda bu rolu tanimiyor. Olcum: 8 eksik commit, bunlardan 5 tanesi tabana uygulanabiliyor (3 uygulanamiyor); parca tasimak yarim entegrasyon olurdu.
- `feat/single-route-observable-20261029` — deneysel tek-saglayici yurutme politikasi; cekirdek saglayici zinciri brain/registry hattinda farkli sekilde cozuldu. Olcum: 9 eksik commit, bunlardan 6 tanesi tabana uygulanabiliyor (3 uygulanamiyor); parca tasimak yarim entegrasyon olurdu.

## Kapilar

- **testler** (exit 0): `C:\Users\Casper\AppData\Local\Programs\Python\Python312\python.exe -m pytest tests -q` -> 2429 passed, 42 skipped, 1 warning in 204.79s (0:03:24)
- **sozdizimi** (exit 0): `C:\Users\Casper\AppData\Local\Programs\Python\Python312\python.exe -m py_compile app.py chat/capabilities.py chat/flow.py chat/inline_ordu.py chat/platform_context.py chat/tools.py tests/test_inline_ordu.py tests/test_yetenek_siniri.py tests/test_vercel_stream.py scripts/olcum/model_yetenek_olcumu.py` -> sessiz basari (exit 0)
- **sir_kapisi** (exit 0): `C:\Users\Casper\AppData\Local\Programs\Python\Python312\python.exe tools/sir_kapisi.py` -> SIR KAPISI: temiz.

```
testler:
apanis.<locals>.yut' was never awaited
    def tell(self):
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2429 passed, 42 skipped, 1 warning in 204.79s (0:03:24)
C:\Users\Casper\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (7.4.3)/charset_normalizer (3.4.4) doesn't match a supported version!
  warnings.warn(

sozdizimi:


sir_kapisi:
Taranan izlenen dosya: 702
SIR KAPISI: temiz.

```

## Yedekler

Uzak dallarin uclarina konan yedek etiketler (15 adet, silinmedi):

- `yedek/dal/harita-yakin-mesafe-20261031` -> `ca43838`
- `yedek/feat/bulut-iscisi-20261031` -> `24fde49`
- `yedek/feat/neon-email-login-20261028-20261031` -> `d4882e6`
- `yedek/feat/openrouter-budget-commander-20261029-20261031` -> `eff0a1b`
- `yedek/feat/ordu-ayni-istek-20261031` -> `7ea41d9`
- `yedek/feat/single-route-observable-20261029-20261031` -> `2584e6a`
- `yedek/feat/uzun-kosu-deposu-20261031` -> `66eb234`
- `yedek/feat/uzun-kosu-deposu-live-20261031` -> `6064428`
- `yedek/fix/account-login-readiness-20261028-20261031` -> `7c39318`
- `yedek/fix/live-provider-timing-evidence-20261029-20261031` -> `d0742f3`
- `yedek/fix/remove-startup-overlay-20261028-20261031` -> `5d49bc2`
- `yedek/fix/remove-startup-private-dialog-20261028-20261031` -> `4023355`
- `yedek/freebuff/5844f7ea4995cb5e860c96a2-20261031` -> `e9e2c0f`
- `yedek/freebuff/belge-temizligi-20261030-20261031` -> `5ca829e`
- `yedek/plan/basak-mimari-master-20261029-20261031` -> `28353ca`

## Sonuc

- test_sonucu: 2429 passed, 42 skipped, 1 warning in 204.79s (0:03:24)
- sonuc: KAPILAR YESIL; kurtarma dali yalniz kendisi push edildi, main/preview'a dokunulmadi.
- not: uzak main bu tabandan 2 commit ileride; dallar arasi birlesme cakismasiz (merge-tree: yok), yani kurtarma dali main'e temiz birlesir. Main'e merge yetkisi Casper'da (AGENTS.md 10).
