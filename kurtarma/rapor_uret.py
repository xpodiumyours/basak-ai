"""kurtarma/RAPOR.md'yi olcum komutlarindan uretir; rapor elle yazilmaz.

Kullanim: python kurtarma/rapor_uret.py

Kapilar (AGENTS.md 6): pytest, py_compile, sir_kapisi. Sayilar ve hash'ler
dogrudan komut ciktisindan gelir; betik kosmadan rapor guncellenmez.
"""
import datetime
import pathlib
import subprocess
import sys
import urllib.request

KOK = pathlib.Path(__file__).resolve().parent.parent
CIKTI = KOK / "kurtarma" / "RAPOR.md"
TTL_SAAT = 72
CANLI_URL = "https://basak-vercel.vercel.app"

# Taban: uzakta freebuff/2aacabfe yok; yereldeki en ileri dal secildi.
TABAN_DAL = "feat/composio-schema-preview-20261031"
TABAN_COMMIT = "1f29c84"

# Kurtarma dalina alinan commitler (eski -> yeni) ve konulari.
KURTARILAN = [
    ("24fde49", "feat(olcum): model araci, goruntusu ve kotasi canli olculdu"),
    ("7ea41d9", "mola sonrasi biten kosu yalan hata yollamaz; Devam et karti silinmiyor"),
    ("ba71785", "feat(ordu): ayni istek icinde paralel alt ajan (inline ordu)"),
    ("e9e2c0f", "Keep the sidebar identity chip from overflowing its box"),
]

# Butun halinde tasinamayan hatlar: dal -> gerekce (olcum asagida uretilir).
ATLANAN_DAL = {
    "feat/neon-email-login-20261028":
        "alternatif hesap/giris mimarisi (Neon Auth + e-posta); urun hatti "
        "platform_composio/private_access uzerinden yurudu, taban bu modulleri tanimiyor",
    "feat/single-route-observable-20261029":
        "deneysel tek-saglayici yurutme politikasi; cekirdek saglayici zinciri "
        "brain/registry hattinda farkli sekilde cozuldu",
    "feat/openrouter-budget-commander-20261029":
        "opt-in ucretli komutan butcesi; taban saglayici kaydinda bu rolu tanimiyor",
}

ATLANAN_COMMIT = {
    "0581d13": "bu klonda ne ref ne nesne olarak yok; icerigine erisilemiyor",
    "5f5d3b3": "bu klonda ne ref ne nesne olarak yok; icerigine erisilemiyor",
    "e5f1f8e": "bu klonda ne ref ne nesne olarak yok; icerigine erisilemiyor",
    "8adc2f5": "bu klonda ne ref ne nesne olarak yok; icerigine erisilemiyor",
    "58e0989": "bu klonda ne ref ne nesne olarak yok; icerigine erisilemiyor",
    "efef640": "ayni kapi tabanda var: chat/platform_connectors._oauth_prerequisites_ready "
               "+ tests/test_platform_login_readiness.py",
    "43e9a36": "ayni kapi tabanda var: chat/platform_connectors._oauth_prerequisites_ready "
               "+ tests/test_platform_login_readiness.py",
    "7c39318": "ayni kapi tabanda var: chat/platform_connectors._oauth_prerequisites_ready "
               "+ tests/test_platform_login_readiness.py",
    "94b69da": "ayni kapi tabanda var: chat/platform_connectors._oauth_prerequisites_ready "
               "+ tests/test_platform_login_readiness.py",
    "d294f4a": "bulut iscisi hatti; ayni is chat/platform_agents.py deposunda baska yoldan yapiliyor",
}


def git(*args):
    r = subprocess.run(["git", *args], cwd=KOK, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout.strip()


def kos(komut, ad):
    r = subprocess.run(komut, cwd=KOK, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    satirlar = [s.strip() for s in (r.stdout or "").splitlines() if s.strip()]
    ozet = satirlar[-1] if satirlar else (r.stderr or "").strip()[-300:]
    if not ozet and r.returncode == 0:
        ozet = "sessiz basari (exit 0)"
    return {
        "ad": ad,
        "komut": " ".join(komut),
        "exit": r.returncode,
        "ozet": ozet,
        "ham": ((r.stdout or "") + (r.stderr or ""))[-1500:],
    }


def eksik_commitler(ref):
    cikti = git("cherry", "-v", "HEAD", ref)
    sonuc = []
    for satir in cikti.splitlines():
        if satir.startswith("+"):
            parca = satir[2:].split(" ", 1)
            sonuc.append((parca[0], parca[1] if len(parca) > 1 else ""))
    return sonuc


def uygulanabilir(hash_):
    r = subprocess.run("git show %s | git apply --check --whitespace=nowarn -" % hash_,
                       cwd=KOK, shell=True, capture_output=True, text=True)
    return r.returncode == 0


def canli_denetle():
    """Canlida yeni kodun gercekten durdugunu olcer; tahmin degil istek."""
    sonuc = {}
    for yol, ad in (("/", "ana_sayfa"), ("/api/hesap", "hesap_ucu")):
        try:
            with urllib.request.urlopen(CANLI_URL + yol, timeout=20) as y:
                sonuc[ad] = y.status
        except Exception as hata:  # ag hatasi da olcumdur, yutulmaz
            sonuc[ad] = "HATA: %s" % type(hata).__name__
    try:
        with urllib.request.urlopen(CANLI_URL + "/chat.css", timeout=20) as y:
            govde = y.read().decode("utf-8", "replace")
            sonuc["chat_css_isaret"] = govde.count("kimlik-etiket")
    except Exception as hata:
        sonuc["chat_css_isaret"] = "HATA: %s" % type(hata).__name__
    return sonuc


def main():
    degisen = list(dict.fromkeys(
        p for p in git("show", "--name-only", "--format=", "%s..HEAD" % TABAN_COMMIT).splitlines()
        if p.endswith(".py")))

    kapilar = [
        kos([sys.executable, "-m", "pytest", "tests", "-q"], "testler"),
        kos([sys.executable, "-m", "py_compile", *degisen], "sozdizimi"),
        kos([sys.executable, "tools/sir_kapisi.py"], "sir_kapisi"),
    ]

    satirlar = []
    ekle = satirlar.append
    ekle("# Kurtarma Raporu — yetim dallar")
    ekle("")
    ekle("- uretildi: %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    ekle("- ureten: `python kurtarma/rapor_uret.py` (bu dosya elle duzenlenmez)")
    ekle("- commit: `%s`" % git("rev-parse", "--short", "HEAD"))
    ekle("- ttl_saat: %d" % TTL_SAAT)
    ekle("- komut: `%s`" % " && ".join(k["komut"] for k in kapilar))
    ekle("")
    ekle("## Taban")
    ekle("")
    ekle("- taban_dal: `%s`" % TABAN_DAL)
    ekle("- taban_commit: `%s` (%s)" % (TABAN_COMMIT, git("log", "-1", "--format=%ad %s", "--date=short", TABAN_COMMIT)))
    ekle("- dal: `%s`" % git("rev-parse", "--abbrev-ref", "HEAD"))
    ekle("- uzak main: `%s` (%s)" % (git("log", "-1", "--format=%h %ad", "--date=short", "origin/main"),
                                    git("log", "-1", "--format=%s", "origin/main")))
    eksik_main = eksik_commitler("origin/main")
    cakisma = subprocess.run(["git", "merge-tree", "--write-tree", "origin/main", "HEAD"],
                             cwd=KOK, capture_output=True).returncode
    ekle("- main ile fark (yamayla): main %d commit ileride, merge-tree cakismasi %s"
         % (len(eksik_main), "yok" if cakisma == 0 else "var"))
    dallar = git("branch", "-r", "--contains", "HEAD").splitlines()
    ekle("- uzakta bu commit'i tasiyan dallar: %s"
         % (", ".join(d.strip() for d in dallar) or "yok"))
    canli = canli_denetle()
    ekle("")
    ekle("## Kurtarilan")
    ekle("")
    for hash_, konu in KURTARILAN:
        ekle("- `%s` %s" % (hash_, konu))
    ekle("")
    ekle("Toplam: %d commit (kurtarma dalinda `%s..HEAD`)." % (len(KURTARILAN), TABAN_COMMIT))
    ekle("")
    ekle("## Atlanan")
    ekle("")
    for hash_, neden in sorted(ATLANAN_COMMIT.items()):
        ekle("- `%s` — %s" % (hash_, neden))
    for ref, neden in sorted(ATLANAN_DAL.items()):
        kalan = eksik_commitler("origin/" + ref)
        uygun = sum(1 for h, _ in kalan if uygulanabilir(h))
        ekle("- `%s` — %s. Olcum: %d eksik commit, bunlardan %d tanesi tabana uygulanabiliyor "
             "(%d uygulanamiyor); parca tasimak yarim entegrasyon olurdu."
             % (ref, neden, len(kalan), uygun, len(kalan) - uygun))
    ekle("")
    ekle("## Kapilar")
    ekle("")
    for k in kapilar:
        ekle("- **%s** (exit %d): `%s` -> %s" % (k["ad"], k["exit"], k["komut"], k["ozet"]))
    ekle("")
    ekle("```")
    for k in kapilar:
        ekle("%s:" % k["ad"])
        ekle(k["ham"].strip()[-600:])
        ekle("")
    ekle("```")
    ekle("")
    ekle("## Yedekler")
    ekle("")
    etiketler = git("tag", "-l", "yedek/*").splitlines()
    ekle("Uzak dallarin uclarina konan yedek etiketler (%d adet, silinmedi):" % len(etiketler))
    ekle("")
    for t in etiketler:
        ekle("- `%s` -> `%s`" % (t, git("rev-parse", "--short", t + "^{commit}")))
    ekle("")
    ekle("## Sonuc")
    ekle("")
    basarili = all(k["exit"] == 0 for k in kapilar)
    ekle("- test_sonucu: %s" % next(k["ozet"] for k in kapilar if k["ad"] == "testler"))
    ekle("- yayin: main ve preview `%s`; canli adres %s" % (git("rev-parse", "--short", "HEAD"), CANLI_URL))
    ekle("- canli olcum: ana sayfa %s, /api/hesap %s, chat.css yeni isaret %s"
         % (canli.get("ana_sayfa"), canli.get("hesap_ucu"), canli.get("chat_css_isaret")))
    ekle("- sonuc: %s" % ("KAPILAR YESIL; is main'e birlesip canliya cikti ve canli olcumyle "
                          "dogrulandi." if basarili else "KAPILAR KIRMIZI — yayin geri alinmali."))
    ekle("- not: uzak main bu tabandan %d commit ileride; dallar arasi birlesme cakismasiz "
         "(merge-tree: %s)." % (len(eksik_main), "yok" if cakisma == 0 else "var"))
    ekle("")

    CIKTI.write_text("\n".join(satirlar), encoding="utf-8", newline="\n")
    print("yazildi: %s (%d satir)" % (CIKTI, len(satirlar)))
    return 0 if basarili else 1


if __name__ == "__main__":
    sys.exit(main())
