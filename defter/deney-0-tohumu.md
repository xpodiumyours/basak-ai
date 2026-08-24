---
kim:    opencode
tarih:  2026-08-24
konu:   DENEY-0 tamamlandi — deney motoru tohumu
tip:    karar
omur:   sonsuz
kaynak: tools/deney.py + tests/test_deney.py
---

Kilitli hedefin "Deney Motoru" organinin ilk halkasi kuruldu.

Felsefe: LLM "bence X daha iyi" dediginde bunun degeri yoktur. Hipotez
OLCULEBILIR deneye donusur; arac gercekten kosturulur; KURAL karar verir.
LLM karar vermez.

Arayuz (`tools/deney.py`):
- Deney = {iddia, arac, arguman, kural, beklenen}
- Kurallar: icerir / yok / esik_ust / esik_alt (ciktadan sayi cikarimi)
- Guvenlik: yalnizca beyaz listeli SALT-OKUNUR olcum araclarina izin
  (git_durum, belge_ara, dosya_bilgi, web_search, sayfa_oku, list_files,
  read_file, list_tasks, get_reminders, model_stats); liste disi araca
  cagri HIC ulasmaz; executor permission katmani ustune ekstra kilit
- Rapor: her hipotez icin desteklendi | elenmis | hata | reddedildi +
  kanit metni (ilk 200 kr)

KANIT: 8 yeni test (tests/test_deney.py): iki kuralin destek/elenme
yollari, esik sayi cikarimi (%87.3 >= 80), sayisiz ciktida hata,
beyaz-liste disi araca ulasilamadigi monkeypatch ile kanitlandi, arac
hatasinin rapora dustugu. Toplam 411/411 yesil.

Sonraki dilimler (kilitli sira): bu tohumun ORKESTRA-0'da hipotez havuzuna
baglanmasi; EVRIM-0'in bunu arsiv+ kombinasyona cevirmesi. B2 borc
provalari taze kotalarda beklemekte.
