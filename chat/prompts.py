"""chat/prompts.py — Kimlik bloğu.

2026-09-13 (Casper kararı): modele verilen talimat blokları kaldırıldı.
Araç yönlendirmesi, dürüstlük ilkesi ve biçimlendirme kuralları burada
duruyordu; hepsi modelin işini kurallarla ezberletmeye çalışan
katmanlardı. Araç şemaları kendilerini anlatıyor, gerisini model bilir.

Geriye yalnız kimlik kaldı — onu model şemadan öğrenemez.
2026-09-23: web'de giriş yapanın adıyla; yerelde Casper.
"""

# 2026-09-10: arastirma sonucu (arXiv 2411.10683 — LLM kimlik karisikligi
# modellerin %26'sinda gorulur ve guveni mantik hatasindan cok zedeler).
# Cozum: kimlik, kisilikten AYRI ve EN BASTA tek mesaj olsun. flow.py
# bunu mesajlar[0] yapar.
def kimlik_blogu(kullanici_adi="Casper"):
    """Kişiye özel kimlik bloğu (web: giriş yapanın adı, yerel: Casper)."""
    ad = str(kullanici_adi or "Casper").strip() or "Casper"
    return (
        "Sen Başak'sın — bir yapay zeka asistanısın.\n"
        "Kullanıcının adı %s.\n"
        "ASLA 'Ben %s' deme, ASLA kullanıcının adını kendi adın gibi "
        "kullanma. Kim olduğunu soranlara: 'Ben Başak' de." % (ad, ad)
    )


# Geriye uyumluluk: sabit (yerel Casper). flow kimlik_blogu() kullanır.
KIMLIK_BLOGU = kimlik_blogu("Casper")


# Cevap dili (2026-09-25): Anthropic cok dilli destek belgesi, uretimde hedef
# dilin sistem talimatinda ACIKCA soylenmesini onerir ("Always respond in
# French, regardless of the language the user writes in"). Eski kisa
# "Turkce konus." P2 onizlemede gpt-oss'u Turkce'de tutamadi. Bu satir arac
# veya niyet secmez; yalniz cevap dilini soyler.
DIL_SATIRI = "Kullanıcı hangi dilde yazarsa yazsın her zaman Türkçe cevap ver."


def kisilik_blogu(kid=None, misafir=False):
    """Kişiye özel kişilik bloğu — yabancıya Casper adı sızmaz.

    Yerel/casper: "Casper'in kisisel asistanisin" (eskisi gibi).
    Diğer web kullanıcıları: kendi adıyla.
    Misafir: isimsiz, nötr.
    """
    if misafir:
        return "Sen Basak'sin. " + DIL_SATIRI
    from chat.kimlik import VARSAYILAN_KULLANICI, aktif_kullanici, gorunur_ad
    kid = kid or aktif_kullanici()
    ad = gorunur_ad(kid)
    if kid == VARSAYILAN_KULLANICI:
        return "Sen Basak'sin, Casper'in kisisel asistanisin. " + DIL_SATIRI
    ham = str(kid or "")
    if ham.startswith("u") and ham[1:].isdigit():
        return ("Sen Basak'sin. Bu kullaniciya ait ayri oturumdasin. "
                + DIL_SATIRI)
    return ("Sen Basak'sin, %s adli kullanicinin kisisel asistanisin. " % ad
            + DIL_SATIRI)


# Misafir kimligi: yabanci ziyaretciye Casper'in adi verilmez,
# hicbir sey varsayilmaz. Yalniz kimliktir, davranis talimati degildir.
MISAFIR_BLOGU = (
    "Sen Başak'sın — bir yapay zeka asistanısın.\n"
    "Karşındaki misafir; adını bilmiyorsun, tahmin etme, sorma. "
    "Kim olduğunu soranlara: 'Ben Başak' de."
)
