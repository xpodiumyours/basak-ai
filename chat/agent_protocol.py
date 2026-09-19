"""chat/agent_protocol.py — Basak'in model-yonetimli ajan protokolu.

Bu katman kullanici metnini siniflandirmaz, kelime aramaz ve hangi gercek
aracin calisacagina karar vermez. Karar modele aittir. Kod yalniz iki seyi
garanti eder:
- ajan turu bir function call ile ilerler;
- gercek is bittiginde model nihai cevabi `son_cevap` ile teslim eder.

Boylece normal duz metin, arac gerektiren bir isi yapilmis gibi gosteren
sessiz chatbot kacis yolu olamaz.
"""

SON_CEVAP_ADI = "son_cevap"

SON_CEVAP_ARACI = {
    "type": "function",
    "function": {
        "name": SON_CEVAP_ADI,
        "description": (
            "Kullaniciya verilecek nihai cevabi teslim eder. Gercek veri, "
            "dosya, web, proje, gorev, hafiza veya baska bir arac sonucu "
            "gereken istekte gerekli araclar calisip sonuclari gorulmeden "
            "kullanma. Yalniz sohbet/aciklama isteginde dogrudan kullanilabilir."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "metin": {
                    "type": "string",
                    "description": "Kullaniciya gosterilecek nihai cevap",
                }
            },
            "required": ["metin"],
        },
    },
}

AJAN_SOZLESMESI = (
    "AJAN CALISMA SOZLESMESI:\n"
    "- Kullanilabilir araclar gercek yeteneklerindir; hangi aracin gerekli "
    "olduguna kullanicinin amacini anlayarak sen karar ver.\n"
    "- Kelime eslestirmesi veya sabit gorev akisi yoktur.\n"
    "- Istek gercek dosya, web, proje, gorev, hafiza, gorsel veya baska "
    "dis veri/eylem gerektiriyorsa yalniz anlatma; uygun araci cagir.\n"
    "- Arac sonucu yeterli degilse sonucu degerlendir ve gereken sonraki "
    "araci kendin sec.\n"
    "- Bir eylem basarili arac sonucu olmadan yapilmis gibi soylenemez.\n"
    "- Is tamamlandiginda son_cevap aracini cagir. Sadece sohbet veya "
    "aciklama isteyen istekte son_cevap dogrudan kullanilabilir."
)


def ajan_araclari(tools):
    """Gercek araclari final-cevap kontrol araci ile birlikte dondurur."""
    mevcut = list(tools or [])
    adlar = {
        (t.get("function") or {}).get("name")
        for t in mevcut if isinstance(t, dict)
    }
    if SON_CEVAP_ADI not in adlar:
        mevcut.append(SON_CEVAP_ARACI)
    return mevcut
