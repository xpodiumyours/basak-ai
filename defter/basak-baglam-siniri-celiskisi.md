---
kim:    claude
tarih:  2026-08-22
konu:   basak
tip:    olcum
omur:   sonsuz
kaynak: chat.py:27 | AGENTS.md §2 madde 2
---

Bağlam sınırında iki belge çelişiyor: `chat.py`'deki gerçek kod sınırı **5.000 karakter** (`KNOWLEDGE_MAX_CHARS = 5000`) ve aşılınca sessizce kesiyor; `AGENTS.md` ise "sınır 12.000 karakter" diyor. Doğrusu koddaki sayı — belge eskimiş. Sonuç: not kümesi büyüdüğünde Başak yalnız alfabetik öndeki kısmı "biliyor" olur ve bunu söylemez.
