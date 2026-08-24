"""tools/aktarici.py — FAY-3: Mekanizma aktarıcı (kilitli hedef).

Organ 4: En yüksek gerilimli çatlak sadece raporlanmaz — ÇÖZÜLMELİ.
Önce Casper'ın KENDİ külliyatına bakılır: aynı ŞEKLE sahip ama farklı
konuda, daha önce çözülmüş bir çelişki var mı? İçerik değil MEKANİZMA
aktarılır. Kendi külliyatında eşleşme yoksa ancak o zaman dışarı çıkılır.

Çözülmüş çelişki havuzu = defter/'de tip=karar olan kayıtlar
(Casper'ın verdiği kararlar = kanıtlanmış mekanizmalar).

Eşleştirme v0'da deterministiktir: Jaccard kelime benzerliği.
(LLM destekli şekil-eşleştirme sonraki dilim — bu hali bile çalışır.)
"""

import os

from tools import bayat


def _kelimeler(metin):
    """Anlam taşıyan kelimeler (durak ve kısa parçalar hariç)."""
    durak = {"ve", "ile", "icin", "icin", "bir", "bu", "su", "ama",
             "gibi", "daha", "en", "var", "yok", "the", "and", "of"}
    return {w for w in "".join(
        c if c.isalnum() or c == " " else " "
        for c in (metin or "").lower()).split()
        if len(w) >= 3 and w not in durak}


def cozumlu_kayitlari(defter_dir):
    """Defterdeki tip=karar kayıtları — kanıtlanmış mekanizma havuzu."""
    cozumler = []
    if not os.path.isdir(defter_dir):
        return cozumler
    for ad in sorted(os.listdir(defter_dir)):
        if not ad.endswith(".md") or ad == "INDEX.md":
            continue
        yol = os.path.join(defter_dir, ad)
        try:
            with open(yol, "r", encoding="utf-8-sig") as f:
                ham = f.read()
        except OSError:
            continue
        fm = bayat._frontmatter_oku(ham)
        if fm.get("tip", "").lower() != "karar":
            continue
        parcalar = ham.split("---", 2)
        icerik = parcalar[2].strip()[:400] if len(parcalar) >= 3 else ""
        cozumler.append({
            "dosya": ad,
            "konu": fm.get("konu", ad[:-3]),
            "kim": fm.get("kim", ""),
            "tarih": fm.get("tarih", ""),
            "mekanizma": icerik,
        })
    return cozumler


def _jaccard(a_kume, b_kume):
    if not a_kume or not b_kume:
        return 0.0
    kesisme = len(a_kume & b_kume)
    bileske = len(a_kume | b_kume)
    return kesisme / bileske if bileske else 0.0


def aktarim_onerisi(catlak, cozumlu_kayitlar, min_benzerlik=0.10,
                    limit=3):
    """Çatlağa benzeyen ŞEKİLDEKI eski çözümleri önerir.

    catlak: {"konu","gerekce","cift"} içeren sözlük.
    Dönüş: {"adaylar":[{dosya,konu,mekanizma,benzerlik}], "not": str}
    Aday yoksa adaylar=[] döner (dış arama kararı Casper'in).
    """
    sorgu_metni = "%s %s %s" % (
        catlak.get("konu", ""),
        catlak.get("gerekce", ""),
        " ".join(catlak.get("cift", ()) or ()),
    )
    sorgu_kume = _kelimeler(sorgu_metni)

    adaylar = []
    for kayit in cozumlu_kayitlar:
        k_kume = _kelimeler(kayit["konu"] + " " + kayit["mekanizma"])
        benzerlik = round(_jaccard(sorgu_kume, k_kume), 2)
        if benzerlik >= min_benzerlik:
            adaylar.append({
                "dosya": kayit["dosya"],
                "konu": kayit["konu"],
                "mekanizma": kayit["mekanizma"][:200],
                "benzerlik": benzerlik,
            })

    adaylar.sort(key=lambda a: -a["benzerlik"])
    adaylar = adaylar[:limit]

    not_metni = ("kendi kulliyatindan %d aday bulundu" % len(adaylar)
                 if adaylar else
                 "kendi kulliyatta benzer sekil yok — dis arama "
                 "(web/literatur) karari Casper'e ait")
    return {"adaylar": adaylar, "not": not_metni}
