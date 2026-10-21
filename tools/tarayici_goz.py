"""tools/tarayici_goz.py — acik sayfayi Basak'in gordugu hale cevirir.

Kural (AGENTS.md S0): bu modul kullanici metnini okumaz, site adi bilmez,
kelime tetikleyicisi tasimaz. Girdi eklentiden gelen HAM gozlemdir
(url, baslik, ogeler); cikti numarali, sayfalanabilir, nesle bagli oge
listesidir. Hangi sitede ne yapilacagina model karar verir; burada yalniz
sayfanin kendisi okunur hale getirilir.

Neden nesil (generation): ref'ler "<nesil>-<sira>" bicimindedir. Sayfa
degisince nesil degisir ve eski ref gecersiz olur. Boylece "okuduk, sayfa
kaydi, yanlis dugmeye basildi" hatasi olusmaz.

Neden sayfalama: sessiz kirpma yok. Donen listede
sayfalama.sonraki_baslangic varsa ayni cagri o degerle surdurulur; oge
sayisinda tavan yoktur (sayfa_oku ile ayni desen). Tek bir ogenin metni
de kirpilmaz; boylece model eksik bilgiyle karar vermez.
"""

import hashlib
import json

VARSAYILAN_ADET = 60
AZAMI_ADET = 200
BILINMEYEN_ROL = "diger"


def _metin(deger):
    """Bosluklari tek bosluga indirir; None/eksik alan bos metin olur."""
    if deger is None:
        return ""
    return " ".join(str(deger).split())


def _nesil(url, ogeler):
    """Sayfanin parmak izi: url + gorunen ogeler. Icerik degisirse degisir."""
    imza = json.dumps([url, ogeler], ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(imza.encode("utf-8")).hexdigest()[:10]


def ogeleri_coz(ham_ogeler):
    """Ham oge listesini temizler.

    - Gorunmeyen oge (gorunur=False) atilir: kullanici gormedigi seye
      basilamaz.
    - Rolu taninmayan oge SILINMEZ; "diger" olarak korunur. Sessiz kayip
      modelin sayfayi eksik gormesine yol acar.
    - Adi ve degeri bos olan oge atilir: tiklanacak ya da okunacak bir sey
      yoktur.
    """
    temiz = []
    for oge in ham_ogeler or ():
        if not isinstance(oge, dict):
            continue
        if oge.get("gorunur") is False:
            continue
        rol = _metin(oge.get("rol")).lower() or BILINMEYEN_ROL
        ad = _metin(oge.get("ad") or oge.get("etiket"))
        deger = _metin(oge.get("deger"))
        if not ad and not deger:
            continue
        # Kimlik eklentiden gelir (sayfa omru boyunca ayni oge ayni numara).
        # Sekme surulmeden once uretir; burada yalniz tasinir. Gozlemde
        # kimlik yoksa eski davranis (konum) gecerlidir.
        try:
            sira = int(oge.get("sira"))
        except (TypeError, ValueError):
            sira = None
        temiz.append({
            "rol": rol,
            "ad": ad,
            "deger": deger,
            "kapali": bool(oge.get("kapali")),
            "sira": sira,
        })
    return temiz


def ref_coz(ref, nesil):
    """Ref'i global siraya cevirir; bayat ya da bozuk ref hata verir.

    Bu fonksiyon tiklama/yazma araclarinin onunde duracak kapi: eski
    gozleme ait ref ile eylem YAPILMAZ.
    """
    parca = str(ref or "").strip().split("-")
    if len(parca) != 2 or not parca[1].isdigit():
        raise ValueError("Gecersiz oge referansi: %r" % (ref,))
    if parca[0] != str(nesil or ""):
        raise ValueError(
            "Bayat oge referansi: sayfa degisti, yeniden bakilmali.")
    return int(parca[1])


def modelle(ham, baslangic=0, adet=VARSAYILAN_ADET):
    """Ham gozlemi modele verilecek yapiya cevirir.

    Doner: {"sayfa": {url, baslik, nesil},
            "ogeler": [{ref, rol, ad, deger, kapali}, ...],
            "sayfalama": {toplam, baslangic, donen, sonraki_baslangic}}
    Cozulemeyen girdi: {"error": ...} — uydurma sayfa uretilmez.
    """
    if not isinstance(ham, dict):
        return {"error": "Tarayici gozlemi cozulemedi (beklenen nesne)."}

    url = _metin(ham.get("url"))
    baslik = _metin(ham.get("baslik"))
    ogeler = ogeleri_coz(ham.get("ogeler"))
    nesil = _nesil(url, ogeler)

    try:
        baslangic = int(baslangic)
    except (TypeError, ValueError):
        baslangic = 0
    try:
        adet = int(adet)
    except (TypeError, ValueError):
        adet = VARSAYILAN_ADET
    baslangic = max(0, baslangic)
    adet = max(1, min(AZAMI_ADET, adet))

    toplam = len(ogeler)
    dilim = ogeler[baslangic:baslangic + adet]
    satirlar = []
    for i, oge in enumerate(dilim):
        # Ref'in sayi kismi OGENIN KALICI KIMLIGIDIR, listedeki yeri degil:
        # liste suzulup sayfalandigi icin konum kayar, kimlik kaymaz.
        kimlik = oge.get("sira")
        sira = kimlik if kimlik is not None else baslangic + i
        satirlar.append({
            "ref": "%s-%d" % (nesil, sira),
            "rol": oge["rol"],
            "ad": oge["ad"],
            "deger": oge["deger"],
            "kapali": oge["kapali"],
        })
    sonraki = baslangic + len(satirlar)
    return {
        "sayfa": {"url": url, "baslik": baslik, "nesil": nesil},
        "ogeler": satirlar,
        "sayfalama": {
            "toplam": toplam,
            "baslangic": baslangic,
            "donen": len(satirlar),
            "sonraki_baslangic": sonraki if sonraki < toplam else None,
        },
    }
