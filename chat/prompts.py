"""chat/prompts.py — Kimlik bloğu.

2026-09-13 (Casper kararı): modele verilen talimat blokları kaldırıldı.
Araç yönlendirmesi, dürüstlük ilkesi ve biçimlendirme kuralları burada
duruyordu; hepsi modelin işini kurallarla ezberletmeye çalışan
katmanlardı. Araç şemaları kendilerini anlatıyor, gerisini model bilir.

Geriye yalnız kimlik kaldı — onu model şemadan öğrenemez.
"""

# 2026-09-10: arastirma sonucu (arXiv 2411.10683 — LLM kimlik karisikligi
# modellerin %26'sinda gorulur ve guveni mantik hatasindan cok zedeler).
# Cozum: kimlik, kisilikten AYRI ve EN BASTA tek mesaj olsun. flow.py
# bunu mesajlar[0] yapar.
KIMLIK_BLOGU = (
    "Sen Başak'sın — bir yapay zeka asistanısın.\n"
    "Kullanıcının adı Casper.\n"
    "ASLA 'Ben Casper' deme, ASLA kullanıcının adını kendi adın gibi "
    "kullanma. Kim olduğunu soranlara: 'Ben Başak' de."
)
