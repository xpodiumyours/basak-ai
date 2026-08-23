---
kim:    opencode
tarih:  2026-08-24
konu:   Ollama bagimsizlik — bulut ayaktayken sohbet kesilmiyor
tip:    karar
omur:   sonsuz
kaynak: kod incelemesi + tests/test_ollama_bagimsizlik.py
---

Casper'in buldugu mimari celiski: zincirde Ollama "SON CARE" olarak
tanimliydi ama mesaj_isle() onu ON KOSUL gibi kontrol ediyordu —
brain.yerel_modeller() bos ise (Ollama kapali) Groq/GLM/NVIDIA/Kilo hazir
olsa bile hata donup cikiyordu. boot() da ok'u yalniz yerel modele bagladi;
uygulama "hazir degil" gorunuyordu.

Cozum:
- `chat.py`: dur kosulu artik `modeller YOK ve brain.bulut_musait() False`
  (ikisi de yok). Bulutlu tam turda model=None gecer; son care Ollama'ya
  ulasilirsa zaten RuntimeError ile zarif dusus var.
- `basak_app.py` boot(): ok = yerel model VAR VEYA bulut VAR.

KANIT: 4 yeni test (tests/test_ollama_bagimsizlik.py): yerel modelsiz +
bulutlu beyinle sohbet tamamlaniyor ve cevap geliyor; iki beyin de yokken
"beyin yok" hatasi; boot ok bulutla True, ikisi de yoksa False.
Toplam 350/350 yesil.

Not: UI'daki model secici listesi Ollama kapaliyken bos kalir — bu dogru
durum gostergesidir; cevap kaynagi UI'da zaten "groq/glm/..." olarak
gorunur. Bilinen sinir: bulut da duserse hata mesaji "Beyin hatasi..."
olarak aynen akar (failover zinciri dokunulmadi).
