"""Yuzey yetenek siniri — kimlik -> arac katalogu.

Neden bu modul: `/api/sohbet` kimlikli herkese ayni 87 araclik katalogu
veriyordu. Anonim web kimligi (u+16 rakam) kalici hesap degildir; yine de
dosya yazma, kod calistirma, tarayici, alt ajan, gorev/hatirlatma yazimi
ve hafiza araclari o kimlige aciktaydi. Katalog kisitlamasi olmadigi icin
sinir yalniz "arac calisirken patlarsa" fikrine dayaniyordu.

Kural (AGENTS.md §0): bu modul KULLANICI METNINE BAKMAZ, kelime
eslestirmez. Yalniz kimlik turu -> katalog secer. Kimlik turu kimligin
kendisinden okunur:

  casper / BASAK_SAHIP_KIMLIKLERI / platform hesabi (u + uuid)  -> sahip
  u<16 rakam> (anonim web), p<hex> (preview), bos/bilinmeyen      -> herkese acik

Herkese acik mod yalniz SALT-OKUNUR dis araclari gorur: arama, okuma,
hava, harita, hesap, saat. Yerel dosya sistemi, kod, tarayici, gorev,
hatirlatma ve hafiza YOKTUR. Ordu (alt ajan) alani da aciktir: alt
ajanlar ayni istek içinde paralel koşar ve salt okunur araçları kullanır
(bkz. chat.inline_ordu); kalıcı hesap gerektirmez.
"""

import os
import re

# Platform hesabi kimligi: "u" + uuid4().hex[:30] (chat.platform_identity).
_HESAP = re.compile(r"u[0-9a-f]{20,40}")
_ANONIM = re.compile(r"u[0-9]{16}|p[0-9a-f]{16}")

# Sahip gormeyen araclar: dis dunyaya salt okuma/yorumlama yapar, sunucuda
# durum degistirmez ve kisisel veri okumaz.
PUBLIC_TOOLS = frozenset((
    # Web / arastirma
    "web_search", "haber_ara", "zamanli_ara", "site_ara", "gorsel_ara",
    "kitap_ara", "derin_oku", "sayfa_oku", "sirket_ara",
    # Bilgi / hesap
    "hava_durumu", "adres_kontrol", "hesapla", "simdi",
    # Harita (okuma)
    "harita_goster", "konum_coz", "sube_bul", "poi_ara",
    "mesafe_hesapla", "rota_hesapla", "mesafe_sure",
))

# Ordu (alt ajan) alani: hesap/kayıt gerektirmez. Calisma bicime bagli
# sinir chat/inline_ordu modulundedir — alt ajanlar salt okunur.
ORDU_ARACLARI = frozenset((
    "ajan_modelleri", "alt_ajan", "alt_ajan_sonuclari",
))


def sahip_kimlikleri():
    """`BASAK_SAHIP_KIMLIKLERI` virgullu listesi (normalize)."""
    ham = os.environ.get("BASAK_SAHIP_KIMLIKLERI", "")
    return {parca.strip() for parca in ham.split(",") if parca.strip()}


def sahip_mi(kid):
    """Kalici sahip oturumu mu? (anonim/preview ASLA sahip degildir)"""
    ham = str(kid or "")
    if not ham:
        return False
    if ham == "casper":
        return True
    if ham in sahip_kimlikleri():
        return True
    if _ANONIM.fullmatch(ham):
        return False
    return bool(_HESAP.fullmatch(ham))


def arac_modu(kid):
    """Yanit ve kayit icin okunur mod adi."""
    return "sahip" if sahip_mi(kid) else "herkese_acik"


def katalog_sec(kid, tools):
    """Kimlige uygun katalog; sahip icin katalog AYNEN doner.

    Donen liste yeni bir listedir; cagiran tarafin elindeki TOOLS
    degismez.
    """
    katalog = list(tools or [])
    if sahip_mi(kid):
        return katalog
    herkese = PUBLIC_TOOLS | ORDU_ARACLARI
    return [
        arac for arac in katalog
        if (arac.get("function") or {}).get("name") in herkese
    ]
