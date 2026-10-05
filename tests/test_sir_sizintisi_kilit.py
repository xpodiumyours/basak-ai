"""tests/test_sir_sizintisi_kilit.py — Sır sızıntısı kalıcı testleri (P0).

İki senaryo kalıcı olarak kilitlenir:

A) TARAYAN ARAÇLAR YASAKLI YOLLARDAN OKUMAZ / SONUCUNA SIR SIZMAZ.
   Kaynak: ARAC-PLANI.md "İş 4 — SIR SIZINTISI" maddesi (2026-09-13,
   vixrex .env.local vakası: özyinelemeli tarama ücretsiz bulut
   modeline anahtar taşıyordu) + AGENTS.md §0 "Dokunulmaz istisna"
   (yol kara listesi: .env, .pem, .key, ayarlar.json — değiştirilemez).
   Kodda doğrulanan tarama araçları:
     - tools/olcum.py::icerik_ara  — klasör walk; _yasak_mi() → dosya
       HİÇ açılmaz (`if _yasak_mi(tam): continue`)
     - tools/olcum.py::belge_ara   — yalnız kök .md; .env ailesi filtrede
     - tools/file_ops.py::read_file — _guvenli_yolu_coz → _yasak_mi
   Kilit: sahte .env/.pem/.key/ayarlar.json oluşturulur; aracın bunları
   ATLADIĞI, sonucuna sırın GİRMEDİĞİ ve — sahte "bulunamadı" testi
   olmasın diye — kontrol aracının izinli dosyada ÇALIŞTIĞI birlikte
   doğrulanır.

B) data/_*.json SOHBET DÖKÜMÜ GIT'E GİREMEZ.
   Kaynak: .gitignore 2026-10-03 notu (_goz_gecmis.json vakası: gerçek
   kullanıcı mesajı `git add .` ile commit'e giriyordu).
   Kilit üç katman: (1) .gitignore kuralı yerinde, (2) git check-ignore
   yakalar + git add reddeder + izlenen dosyalarda yok, (3) döküm yine
   de izlenseye tools/sir_kapisi.py içindeki anahtar deseni yakalar.

YALNIZ TEST: kural katmanı / model çıktısına dokunan kod eklenmez.
"""

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from tools import calistir, file_ops, olcum  # noqa: E402
from tools import sir_kapisi as kap  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Sahte sır işaretleri — düz metin; hiçbiri sır_kapisi desenlerine
# (anahtar desenleri) uymaz, o yüzden bu dosya depo taramasını kırmızıya bozmaz.
ENV_ISARETI = "SIR_ENV_KILIT_7781"
PEM_ISARETI = "SIR_PEM_KILIT_7782"
KEY_ISARETI = "SIR_KEY_KILIT_7783"
AYAR_ISARETI = "SIR_AYARLAR_KILIT_7784"
KONTROL_ISARETI = "KONTROL_BULGU_KILIT_7785"

YASAKLI_ADLAR = (".env", "sir.pem", "anahtar.key", "ayarlar.json")


@pytest.fixture
def sahte_proje(tmp_path):
    """Yasaklı dosyalar + izinli kontrol dosyası içeren sahte proje."""
    kok = tmp_path / "proje"
    kok.mkdir()
    # Her yasaklı dosyada: işareti (sorgu) + dosyaya özgü gizli değer
    # (sorgu DEĞİL — hatanın yankılamayacağı tek kanıt parçası).
    (kok / ".env").write_text(
        "URETIM=1\nANAHTARDEGERI=%s\nSAHTE_ENV_DEGER_9911\n" % ENV_ISARETI,
        encoding="utf-8")
    (kok / "sir.pem").write_text(
        "SAHTE PEM BELGESI\n%s\nSAHTE_PEM_DEGER_9912\n" % PEM_ISARETI,
        encoding="utf-8")
    (kok / "anahtar.key").write_text(
        "SAHTE ANAHTAR\n%s\nSAHTE_KEY_DEGER_9913\n" % KEY_ISARETI,
        encoding="utf-8")
    (kok / "ayarlar.json").write_text(
        '{"sunucu": "%s", "gizli": "SAHTE_AYAR_DEGER_9914"}'
        % AYAR_ISARETI, encoding="utf-8")
    # İzinli kontrol: aracın ÇALIŞTIĞINI kanıtlar (sahte "bulunamadı"
    # testi olmasın diye).
    (kok / "not.md").write_text(
        "Kontrol notu %s\n" % KONTROL_ISARETI, encoding="utf-8")
    # İzinli adlı dosyada gömülü anahtar: ikinci savunma hattı (maskeleme).
    (kok / "gizli.txt").write_text(
        'baglanti token = "' + ("a" * 24) + '"\n', encoding="utf-8")
    olcum.PROJELER["sir-kilit"] = str(kok)
    yield kok
    del olcum.PROJELER["sir-kilit"]


def _sir_yok(r):
    """Sonuc metninde hiçbir sır işareti geçmiyor mu?"""
    metin = json.dumps(r, ensure_ascii=False)
    return all(i not in metin
               for i in (ENV_ISARETI, PEM_ISARETI, KEY_ISARETI,
                         AYAR_ISARETI))


class TestATaramaAracariYasakYollariOkumaz:
    def test_kara_liste_kaliplari_sabit(self):
        """AGENTS.md §5 Dokunulmaz istisna: dört kalıp da yerinde."""
        for kalipt in (".env", ".pem", ".key", "ayarlar.json"):
            assert kalipt in file_ops.YASAK_DOSYA_KALIPLARI, kalipt
        assert file_ops._yasak_mi(os.path.join("x", ".env"))
        assert file_ops._yasak_mi(os.path.join("x", "sir.pem"))
        assert file_ops._yasak_mi(os.path.join("x", "anahtar.key"))
        assert file_ops._yasak_mi(os.path.join("x", "ayarlar.json"))
        # Yanlış pozitif: normal dosyalar kara listede değil.
        assert not file_ops._yasak_mi(os.path.join("x", "not.md"))
        assert not file_ops._yasak_mi(
            os.path.join("x", "ayarlar.ornek.json"))

    def test_icerik_ara_yasakli_dosyalari_atlar(self, sahte_proje):
        """icerik_ara: dört yasaklı dosyanın hiçbiri sonuca girmez.

        Sorgu "bulunamadı" hatasında yankılanır (hata = aramanın kendisi);
        sızıntı `result` içinde görünür. Kilit: `result` yok + dosyaya
        özgü içerik (sorgu olmayan parça) hiçbir yerde geçmiyor.
        """
        for isaret, gizli_deger in (
                (ENV_ISARETI, "SAHTE_ENV_DEGER_9911"),
                (PEM_ISARETI, "SAHTE_PEM_DEGER_9912"),
                (KEY_ISARETI, "SAHTE_KEY_DEGER_9913"),
                (AYAR_ISARETI, "SAHTE_AYAR_DEGER_9914")):
            r = olcum.icerik_ara("sir-kilit", isaret)
            assert "result" not in r, (isaret, r)   # bulunamadı = açılmadı
            assert gizli_deger not in json.dumps(
                r, ensure_ascii=False), (isaret, r)

    def test_icerik_ara_kontrol_araci_calisir(self, sahte_proje):
        """Olumlu kanıt: arama kırılmadı, yasaklılar ATLANIYOR."""
        r = olcum.icerik_ara("sir-kilit", KONTROL_ISARETI)
        assert "result" in r, r
        assert "not.md" in r["result"]

    def test_belge_ara_yasakli_dosyaya_girmez(self, sahte_proje):
        """belge_ara yalnız kök .md okur; .env ailesi sonuca girmez.

        Kilit: `result` yok (kök .md olmayan dosya hiç okunmaz) + .env'ye
        özgü gizli değer hiçbir yerde geçmiyor.
        """
        r = olcum.belge_ara("sir-kilit", ENV_ISARETI)
        assert "result" not in r, r
        assert "SAHTE_ENV_DEGER_9911" not in json.dumps(
            r, ensure_ascii=False)
        # Kontrol: aynı klasörde arama çalışıyor.
        r2 = olcum.belge_ara("sir-kilit", KONTROL_ISARETI)
        assert "result" in r2, r2
        assert "not.md" in r2["result"]

    def test_read_file_dispatcher_yasakli_yolu_omez(self, sahte_proje):
        """Modelin gördüğü hat: calistir('read_file') — dört yol da kapalı."""
        sonuclar = {}
        for ad in YASAKLI_ADLAR:
            r = calistir("read_file", {"path": str(sahte_proje / ad)})
            assert "error" in r, (ad, r)
            sonuclar[ad] = r
        assert _sir_yok(sonuclar), "sır dispatcher sonucuna sızdı"

    def test_yazma_kara_listede_ve_dosya_olusmaz(self, tmp_path):
        """Yazma yolu da kapalı; kanıt DISKTE: dosya hiç oluşmamalı."""
        base = tmp_path / "base"
        (base / "knowledge").mkdir(parents=True)
        for yol in ("knowledge/.env", "knowledge/sir.pem",
                    "knowledge/ayarlar.json"):
            r = file_ops.write_file_ops(yol, "sir=deneme", str(base))
            assert "error" in r, (yol, r)
            assert not (base / yol).exists(), "DOSYA OLUŞTU: %s" % yol
        r2 = file_ops.write_knowledge(
            "knowledge/anahtar.key", "sir=deneme", str(base))
        assert "error" in r2, r2
        assert not (base / "knowledge" / "anahtar.key").exists()

    def test_gomulu_anahtar_maskelenir(self, sahte_proje):
        """İkinci savunma hattı (ARAC-PLANI İş 4, madde 3): izinli
        adlı dosyadaki gömülü anahtar çıktıya ham geçmez."""
        r = olcum.icerik_ara("sir-kilit", "baglanti")
        assert "result" in r, r
        assert ("a" * 24) not in r["result"], "anahtar değeri çıktıya sızdı"
        assert "***" in r["result"], "maskeleme uygulanmadı"


class TestBSohbetDokumuGitGiremez:
    def test_gitignore_kurali_yerinde(self):
        """.gitignore 2026-10-03 kuralı (data/_*.json) silinmemiş."""
        with open(os.path.join(REPO, ".gitignore"), encoding="utf-8") as f:
            satirlar = [s.strip() for s in f]
        assert "data/_*.json" in satirlar, \
            ".gitignore kuralı data/_*.json yok oldu"

    def test_git_check_ignore_dokumu_yakalar(self):
        """git, döküm dosyasını ignore eder (kural aktif, teorik değil)."""
        for ad in ("data/_goz_gecmis.json", "data/_sir_kilit_ornek.json"):
            r = subprocess.run(
                ["git", "check-ignore", ad],
                cwd=REPO, capture_output=True, text=True)
            assert r.returncode == 0, (ad, r.stdout, r.stderr)
        # Yanlış pozitif: normal data dosyası ignore edilmez — kural
        # "data/ hepsi" değil, yalnız _*.json ailesi.
        r = subprocess.run(
            ["git", "check-ignore", "data/rapor.json"],
            cwd=REPO, capture_output=True, text=True)
        assert r.returncode == 1, "data/ klasörü tamamen ignore ediliyor"

    def test_git_add_dokumu_almaz(self):
        """Kabul kanıtı: dosya diskte olsa bile git add onu almaz."""
        ad = "data/_sir_kilit_test_%d.json" % os.getpid()
        tam = os.path.join(REPO, ad)
        assert not os.path.exists(tam), "önceden kalmış test dosyası var"
        try:
            with open(tam, "w", encoding="utf-8") as f:
                f.write('{"kullanici": "sahte sohbet dumuyu"}')
            r = subprocess.run(
                ["git", "add", "-n", ad],
                cwd=REPO, capture_output=True, text=True)
            assert r.returncode != 0, "git add dökümü kabul etti!"
            assert "ignored" in (r.stderr or "").lower(), r.stderr
            s = subprocess.run(
                ["git", "status", "--porcelain", "--", ad],
                cwd=REPO, capture_output=True, text=True)
            assert s.stdout.strip() == "", \
                "döküm status'te görünüyor: %r" % s.stdout
        finally:
            if os.path.exists(tam):
                os.remove(tam)

    def test_izlenenlerde_dokum_yok(self):
        """Anlık zincir: hiçbir data/_*.json izlenen (tracked) dosya değil."""
        r = subprocess.run(
            ["git", "ls-files", "data/"],
            cwd=REPO, capture_output=True, text=True, check=True)
        izlenen = [s for s in r.stdout.splitlines() if s]
        ihlal = [s for s in izlenen
                 if re.match(r"^data/_.*\.json$", s)]
        assert ihlal == [], "izlenen döküm dosyası: %r" % ihlal

    def test_kapu_dokum_icerigindeki_anahtari_yakalar(self, tmp_path,
                                                      monkeypatch):
        """Sır kapısı katmanı: döküm yine de izlense bile (git add -f
        gibi bir yolla) içeriğindeki anahtar deseni kırmızı olur."""
        anahtar = "sk-" + ("A" * 32)
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "_goz_gecmis.json").write_text(
            '{"kullanici": "merhaba", "sir": "' + anahtar + '"}',
            encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            kap, "izlenenler", lambda: ["data/_goz_gecmis.json"])
        bulgular = kap.tara()
        kirmizi = [(tur, yol) for tur, yol, _ in bulgular
                   if yol == "data/_goz_gecmis.json"]
        assert kirmizi, \
            "döküm içeriğindeki anahtar yakalanmadı: %r" % (bulgular,)
        assert kirmizi[0][0] == "ICERIK"
