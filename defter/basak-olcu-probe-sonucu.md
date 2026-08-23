---
kim:    opencode
tarih:  2026-08-22
konu:   olcu-probe
tip:    olcum
omur:   30g
kaynak: _olcu_probe_sonuc.json
---

Ö-0 kabul provası (10 zor soru, başsız gerçek zincir): 7 [A] alıntısının 7'si
bağımsız birebir doğrulamadan geçti — uydurma sıfır. Hayatta kalan işaretsiz
satır sıfır. Kaynağı olmayan sorular [B] ile döndü. İki sınır ölçüldü:
(1) 5.000 karakter bağlam sınırı GOREV_LISTESI+AGENTS bloklarını kırpiyor;
model dosyaları göremeyince uydurmak yerine [B] dedi (istenen davranış).
(2) Hafıza kaynaklı cevaplar [B] etiketiyle geçiyor — hafıza metni kapıda
doğrulanamıyor. Not: Groq günlük token limiti 194383/200000 ile neredeyse
dolmuştu; zincir glm'ye yaslandı — failover canlı kanıtlandı.
