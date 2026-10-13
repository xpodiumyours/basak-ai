"""fatura_rapor.py — Fatura okuma çıktısını rapora çeviren sunum katmanı.

Tek kaynak: hem canlı uygulama (`app.py` → /api/fatura-oku) hem önizleme
sunucusu (`preview_fatura.py`) buradan beslenir; iki yerde ayrı mantık
tutulmaz.

Burada karar verilmez, ölçüm yapılmaz: alanlar `tools.katalog`'dan gelir,
burada yalnız "hangi alan çıkmadı" ve "belgenin aritmetiği tutuyor mu"
soruları rapora dökülür. Ölçülemeyen şey `None` kalır — "tutuyor"
sayılmaz.
"""

# Kullanıcıya "şu alanlar belgede yok" demek için beklenen alanlar.
BEKLENEN_ALANLAR = (
    ("fis_no", "Belge/Fatura No"),
    ("tarih", "Tarih"),
    ("firma", "Satıcı"),
    ("alici", "Alıcı"),
    ("vkn", "Satıcı VKN"),
    ("vergi_dairesi", "Satıcı vergi dairesi"),
    ("alici_vkn", "Alıcı VKN"),
    ("kdv_oran", "KDV oranı"),
    ("ara_toplam", "Matrah / ara toplam"),
    ("kdv_tutar", "KDV tutarı"),
    ("toplam", "Genel toplam"),
    ("para_birimi", "Para birimi"),
)


def eksik_alanlar(ust):
    """Çıkmayan alanların etiketleri (uydurma yok, eksik açık)."""
    ust = ust or {}
    return [etiket for ad, etiket in BEKLENEN_ALANLAR
            if ust.get(ad) in (None, "", 0)]


def denetimler(ust, satirlar):
    """Belgenin kendi aritmetiği tutuyor mu? None = ölçülemedi."""
    ust = ust or {}
    satirlar = satirlar or []
    sonuc = []
    matrah, kdv = ust.get("ara_toplam"), ust.get("kdv_tutar")
    toplam = ust.get("toplam")
    if matrah is not None and kdv is not None and toplam is not None:
        sonuc.append({
            "ad": "Matrah + KDV = genel toplam",
            "durum": abs(round(matrah + kdv, 2) - toplam) <= 0.05,
            "ayrinti": "%s + %s = %s (basılı: %s)"
                       % (matrah, kdv, round(matrah + kdv, 2), toplam),
        })
    # Satırlar KDV dahil ya da hariç listelenebilir; satır toplamı bu
    # yüzden genel toplama VEYA matraha uyabilir. İkisi de tutmuyorsa
    # uyuşmazlık gerçektir. Ölçülemiyorsa (basılı toplam yoksa) denetim
    # hiç yazılmaz.
    basili = [d for d in (toplam, matrah) if d is not None]
    if satirlar and basili:
        hesap = round(sum(s["tutar"] for s in satirlar
                          if s.get("tutar") is not None), 2)
        sonuc.append({
            "ad": "Satır tutarları toplamı = genel toplam ya da matrah",
            "durum": any(abs(hesap - d) <= 0.05 for d in basili),
            "ayrinti": "%s (basılı: %s)"
                       % (hesap, " / ".join(str(d) for d in basili)),
        })
    denetimli = [s for s in satirlar if s.get("tutar_tutarli") is not None]
    if denetimli:
        bozuk = [s["sira"] for s in denetimli if not s["tutar_tutarli"]]
        sonuc.append({
            "ad": "Her satırda miktar × birim fiyat = tutar",
            "durum": not bozuk,
            "ayrinti": ("%d satır denetlendi" % len(denetimli)) if not bozuk
                       else "uyuşmayan satır: %s" % ", ".join(map(str, bozuk)),
        })
    return sonuc


def govde(kaynak, yazi, ust, satirlar, okuma=None, fatura_id=""):
    """İstemciye giden tek rapor gövdesi (iki uç da bunu döner)."""
    return {
        "kaynak": kaynak,
        "fatura_id": fatura_id,
        "okuma": okuma or {},
        "yazi": yazi or "",
        "ustbilgi": ust or {},
        "satirlar": satirlar or [],
        "eksik": eksik_alanlar(ust),
        "denetim": denetimler(ust, satirlar),
    }
