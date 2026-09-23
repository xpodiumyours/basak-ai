"""tools — Başak'ın araçları. Elli iki tane.

2026-09-13: 21 araçlık katman söküldü; Casper'in seçtikleri geri geldi.
Okuyanlar serbesttir. Etkisi olanlar dardir: dosya yazma yalniz
knowledge/ alti, tablo/gorev yazma yalniz kendi dosyalari, komutlar
sabit tablodan, uygulamalar beyaz listeden. Bu yuzden izin tablosu,
onay kuyruğu, yetki tavanı yok. Tek kural beyaz liste + yol kara
listesi + sabit komutlar.
"""

import logging
import os

from tools.definitions import TOOLS, TANINMIS_TOOLLAR  # noqa: F401

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")

# None = durum kokunun gorevler.json dosyasi; test patch edebilir.
# Depo kokune yazilmiyor: dagitim klasoru yazilabilir degil.
GOREVLER_FILE = None


def gorevler_dosyasi():
    """Gorev listesi dosyasi: durum kokunun gorevler.json'u.

    chat.kimlik burada (modul seviyesinde degil) alinir: tools paketi
    chat paketinden once yuklenebiliyor, dairesel import riski var.
    """
    from chat.kimlik import durum_yolu
    if GOREVLER_FILE:
        return GOREVLER_FILE
    yeni_yol = os.path.join(durum_yolu(), "gorevler.json")
    _eski_gorevleri_tasi(yeni_yol)
    return yeni_yol


def _eski_gorevleri_tasi(yeni_yol):
    """Depo kokundeki eski gorevler.json'u bir kez yeni koke tasir.

    2026-09-23: gorev listesi depo kokune yaziliyordu; dagitimda o klasor
    salt okunur oldugu icin bulutta hic calismiyordu. Yol degisti ama eski
    dosyada kayit kalmis olabilir — SILINMEZ, tasinir. Yeni dosya varsa
    dokunulmaz (eskisi zaten tasinmis demektir).
    """
    eski_yol = os.path.join(BASE, "gorevler.json")
    if not os.path.exists(eski_yol) or os.path.exists(yeni_yol):
        return
    try:
        os.makedirs(os.path.dirname(yeni_yol), exist_ok=True)
        # KOPYALANIR, TASINMAZ. Tasima denendi ve zararli cikti: test
        # paketi kostugunda gercek depo dosyasi gecici klasore tasinip
        # silindi (2026-09-23). Kopya guvenli: eski dosya yerinde kalir,
        # yalnizca artik okunmaz.
        import shutil
        shutil.copy2(eski_yol, yeni_yol)
    except OSError:
        pass  # kopya basarisizsa eski dosya yerinde kalir, veri kaybi yok


def calistir(tool_name, args):
    """Aracı çalıştırır. Beyaz liste dışı ad ASLA koşmaz.

    Dönüş: dict — {"result": ...} veya {"error": ...}
    """
    if tool_name not in TANINMIS_TOOLLAR:
        logger.info("Taninmayan arac reddedildi: %s", tool_name)
        return {"error": "'%s' diye bir arac yok." % tool_name}

    args = args or {}
    try:
        if tool_name == "web_search":
            from tools import web_search as ws
            return ws.web_search(str(args.get("query", "")),
                                 adet=args.get("adet", 20))

        if tool_name == "haber_ara":
            from tools import web_search as ws
            return ws.haber_ara(str(args.get("query", "")),
                                adet=args.get("adet", 10))

        if tool_name == "zamanli_ara":
            from tools import web_search as ws
            return ws.zamanli_ara(str(args.get("query", "")),
                                  str(args.get("aralik", "") or ""),
                                  adet=args.get("adet", 10))

        if tool_name == "site_ara":
            from tools import web_search as ws
            return ws.site_ara(str(args.get("site", "")),
                               str(args.get("sorgu", "")),
                               adet=args.get("adet", 10))

        if tool_name == "gorsel_ara":
            from tools import web_search as ws
            return ws.gorsel_ara(str(args.get("query", "")),
                                 adet=args.get("adet", 10))

        if tool_name == "kitap_ara":
            from tools import web_search as ws
            return ws.kitap_ara(str(args.get("query", "")),
                                adet=args.get("adet", 10))

        if tool_name == "derin_oku":
            from tools import web_search as ws
            return ws.derin_oku(str(args.get("url", "")))

        if tool_name == "sayfa_oku":
            from tools import web_search as ws
            return ws.sayfa_oku(str(args.get("url", "")))

        if tool_name == "read_file":
            from tools import file_ops
            return file_ops.read_file(str(args.get("path", "")), BASE)

        if tool_name == "list_files":
            from tools import file_ops
            return file_ops.list_files(str(args.get("folder", "")), BASE)

        if tool_name == "git_durum":
            from tools import olcum
            return olcum.git_durum(str(args.get("proje", "")))

        if tool_name == "belge_ara":
            from tools import olcum
            return olcum.belge_ara(
                str(args.get("proje", "")),
                str(args.get("sorgu", "")))

        if tool_name == "dosya_bilgi":
            from tools import olcum
            return olcum.dosya_bilgi(
                str(args.get("proje", "")),
                str(args.get("yol", "")))

        if tool_name == "image_analyze":
            from tools import image_analyzer
            return image_analyzer.image_analyze(
                str(args.get("path", "")),
                str(args.get("soru", "") or "") or None)

        if tool_name == "write_file_tool":
            from tools import file_ops
            return file_ops.write_knowledge(
                str(args.get("path", "")),
                str(args.get("content", "") or ""),
                BASE)

        if tool_name == "get_reminders":
            from tools import reminders
            return reminders.bugunku_hatirlatmalar(
                KNOWLEDGE_DIR, gorevler_dosyasi())

        if tool_name == "add_task":
            from tools import tasks
            return tasks.add_task(
                str(args.get("text", "")), gorevler_dosyasi(),
                date=args.get("date"))

        if tool_name == "list_tasks":
            from tools import tasks
            return tasks.list_tasks(gorevler_dosyasi())

        if tool_name == "complete_task":
            from tools import tasks
            try:
                task_id = int(args.get("task_id", 0))
            except (TypeError, ValueError):
                return {"error": "Gorev no sayi olmali."}
            return tasks.complete_task(task_id, gorevler_dosyasi())

        if tool_name == "ac_uygulama":
            from tools import app_launcher
            return app_launcher.ac_uygulama(
                str(args.get("uygulama", "")),
                str(args.get("parametre", "") or ""))

        if tool_name == "icerik_ara":
            from tools import olcum
            return olcum.icerik_ara(
                str(args.get("proje", "")),
                str(args.get("sorgu", "")),
                str(args.get("uzanti", "") or "") or None)

        if tool_name == "github_durum":
            from tools import github
            return github.github_durum(
                str(args.get("islem", "")),
                str(args.get("proje", "")),
                no=args.get("no"),
                durum=str(args.get("durum", "") or "open"))

        if tool_name == "git_gecmis":
            from tools import olcum
            return olcum.git_gecmis(
                str(args.get("proje", "")),
                dosya=str(args.get("dosya", "") or "") or None,
                adet=args.get("adet", 10))

        if tool_name == "git_degisenler":
            from tools import olcum
            return olcum.git_degisenler(
                str(args.get("proje", "")),
                taban=str(args.get("taban", "") or "origin/master"))

        if tool_name == "adres_kontrol":
            from tools import web_search as ws
            return ws.adres_kontrol(str(args.get("url", "")))

        if tool_name == "testleri_kos":
            from tools import testkos
            return testkos.testleri_kos(str(args.get("proje", "")))

        if tool_name == "matris_ac":
            from tools import matris
            return matris.matris_ac(
                str(args.get("baslik", "")),
                str(args.get("fikir", "") or ""))

        if tool_name == "matris_liste":
            from tools import matris
            return matris.matris_liste()

        if tool_name == "satir_ekle":
            from tools import matris
            bagli = args.get("bagli", []) or []
            if not isinstance(bagli, list):
                bagli = [bagli]
            return matris.satir_ekle(
                args.get("matris"), str(args.get("tur", "")),
                str(args.get("metin", "")),
                ust=args.get("ust"), neden=str(args.get("neden", "") or ""),
                bagli=bagli)

        if tool_name == "kanit_ekle":
            from tools import matris
            return matris.kanit_ekle(
                args.get("matris"), args.get("satir"),
                str(args.get("kanit", "")))

        if tool_name == "satir_kapat":
            from tools import matris
            return matris.satir_kapat(args.get("matris"), args.get("satir"))

        if tool_name == "satir_ac":
            from tools import matris
            return matris.satir_ac(args.get("matris"), args.get("satir"))

        if tool_name == "satir_sil":
            from tools import matris
            return matris.satir_sil(args.get("matris"), args.get("satir"))

        if tool_name == "satir_tasi":
            from tools import matris
            return matris.satir_tasi(
                args.get("matris"), args.get("satir"),
                args.get("yeni_ust"))

        if tool_name == "matris_durum":
            from tools import matris
            return matris.matris_durum(args.get("matris"))

        if tool_name == "gorsel_uret":
            from tools import gorsel
            return gorsel.gorsel_uret(
                str(args.get("aciklama", "")),
                genislik=args.get("genislik", 1024),
                yukseklik=args.get("yukseklik", 1024))

        if tool_name == "saglik_raporu":
            from tools import saglik
            return saglik.saglik_raporu()

        if tool_name == "satir_duzenle":
            from tools import matris
            return matris.satir_duzenle(
                args.get("matris"), args.get("satir"),
                metin=args.get("metin"), neden=args.get("neden"))

        if tool_name == "simdi":
            from tools import hesap
            return hesap.simdi()

        if tool_name == "hesapla":
            from tools import hesap
            return hesap.hesapla(str(args.get("ifade", "")))

        if tool_name == "hafiza_ara":
            from tools import hafiza
            return hafiza.hafiza_ara(str(args.get("sorgu", "")))

        if tool_name == "fatura_oku":
            from tools import katalog
            return katalog.fatura_oku(str(args.get("fatura_id", "")))

        if tool_name == "katalog_kur":
            from tools import katalog
            return katalog.katalog_kur(
                str(args.get("fatura_id", "")),
                args.get("satirlar", []) or [],
                ustbilgi=args.get("ustbilgi"))

        if tool_name == "katalog_getir":
            from tools import katalog
            return katalog.katalog_getir(str(args.get("is_id", "")))

        if tool_name == "katalog_liste":
            from tools import katalog
            return katalog.katalog_listele()

        if tool_name == "katalog_fiyat_guncelle":
            from tools import katalog
            return katalog.katalog_fiyat_guncelle(
                str(args.get("is_id", "")),
                str(args.get("kart_id", "")),
                args.get("satis_fiyat", ""))

        if tool_name == "katalog_onayla":
            from tools import katalog
            return katalog.katalog_onayla(str(args.get("is_id", "")))

        if tool_name == "yetki_belgesi_ekle":
            from tools import katalog
            return katalog.yetki_belgesi_ekle(
                str(args.get("is_id", "") or ""),
                str(args.get("b64", "") or ""),
                str(args.get("ad", "") or ""),
                str(args.get("marka", "") or ""))

        if tool_name == "urun_eslestir":
            from tools import katalog
            return katalog.urun_eslestir(
                str(args.get("is_id", "")),
                str(args.get("kart_id", "")))

        if tool_name == "yayin_paketi":
            from tools import katalog
            return katalog.yayin_paketi(
                str(args.get("is_id", "")),
                str(args.get("platform", "") or "vixrex"))

        if tool_name == "cikti_oku":
            from tools import katalog
            return katalog.cikti_oku(
                str(args.get("is_id", "")),
                str(args.get("dosya", "")))

        if tool_name == "sirket_ara":
            from tools import katalog
            return katalog.sirket_ara(str(args.get("marka", "")))
    except Exception as e:
        logger.warning("Arac hatasi (%s): %s", tool_name, e)
        return {"error": "Arac calismadi: %s" % str(e)}

    return {"error": "'%s' calistirilamadi." % tool_name}
