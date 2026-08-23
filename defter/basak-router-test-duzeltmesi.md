---
kim:    opencode
tarih:  2026-08-22
konu:   router-test
tip:    olcum
omur:   30g
kaynak: pytest tests/ ciktisi (2026-08-22)
---

P3 katmaninda bayat test saptandi: `test_varsayilan_sirada_ucretli_sonda` DeepSeek'i
varsayilan zincirde bekliyordu ama registry zincirden cikarmisti (DeepSeek ucretli,
bakıye bekliyor) → 1 test kirik, 93 gecen. Test guclenerek duzeltildi: artik kural
"ucretli saglayici sonda degil, varsayilan zincirde HIC ucretli yok". Sonrasindan
94/94 yesil. Ders: model listesi guncellenirken router testlerinin de kosulmasi gerek.
