---
kim:    opencode
tarih:  2026-08-24
konu:   Faz 1 — canary modu + savunma test paketi + canlı geçiş kapısı
tip:    karar
omur:   sonsuz
kaynak: tools/permissions.py + tools/file_ops.py + tools/tool_logger.py + tests/test_savunma.py + tests/test_canary.py + CANLI-KAPISI.md
---

Yeni beyin organı eklemek DURDURULDU; önce dayanıklılık kanıtı hattı
kuruluyor (Casper kararı, CANLI-KAPISI.md).

FAZ 1 TAMAMLANDI:
1. **Canary modu** ("calisma_modu"): yazma+sistem araçları kodla tamamen
   kapalı (onay kuyusu yokken 'onay iste' yerine TAM ENGEL seçildi);
   dış projeler izinli_projeler listesine mahkum; geçersiz mod değeri
   normale düşer. Executor mesajları eski sözleşmeyi korur.
2. **Savunma paketi** (19 test): ../ kaçışı, mutlak yol, GERÇEK junction
   üzerinden kaçış (mklink /J), silme/shell/git-reset enjeksiyonu,
   dosya_bilgi gezinmesi, "model izni değiştiremez", prompt enjeksiyonu,
   log sızıntısı taraması.
3. **Gerçek zafiyat kapatıldı:** _kirmala gsk_/hf_/nvapi-/sk-or-v1-
   öneklerini tanımıyordu — Groq/HF/NVIDIA/OpenRouter anahtar biçimleri
   loga HAM girebiliyordu. Genişletildi + testle kilitlendi.

KANIT: 516+ test yesil; savunma/canary paketi 23 yeni test.
