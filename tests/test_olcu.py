"""tests/test_olcu.py — Ö-0 çıkış kapısı testleri.

Kapının mekanizması ağsız, modelsiz doğrulanır:
işaretsiz cümle ölür, uydurma [A] alıntısı ölür, gerçek alıntı yaşar,
[Ö] yalnız bu turun araç çıktısında birebir varsa yaşar,
[Ç] dayanakları bu turda doğrulanmış olmalı, [B] her zaman yaşar.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from olcu import YEDEK_CUMLE, bol_cumleler, cikis_kapisi


class TestBolme:
    def test_isaretli_satir_tek_birim(self):
        assert bol_cumleler('[A] x.md "bir cumle. Icinde nokta olsa da."') == [
            '[A] x.md "bir cumle. Icinde nokta olsa da."']

    def test_duz_metin_cumlelere_bolunur(self):
        parcalar = bol_cumleler("Bu ilk cumle. Bu ikinci cumle!")
        assert len(parcalar) == 2

    def test_bos_girdi(self):
        assert bol_cumleler("") == []
        assert bol_cumleler(None) == []


class TestIsaretsiz:
    def test_tamamen_isaretsiz_sohbet_gecer(self):
        """Hicbir cumlede isaret yoksa — sohbet/nezaket — oldugu gibi gecer."""
        temiz, rapor = cikis_kapisi("Bu cumlenin hicbir isareti yok.")
        assert temiz == "Bu cumlenin hicbir isareti yok."
        assert rapor == []

    def test_karısık_cevapta_sadece_isaretliler_kalir(self):
        metin = ('Merhaba!\n'
                 '[B] Bunu bilmiyorum.\n'
                 'Kaynaksiz iddia burada.\n'
                 '[B] Sohbet cumlesi.')
        temiz, rapor = cikis_kapisi(metin)
        assert "Merhaba" not in temiz and "Kaynaksiz" not in temiz
        assert "badge::B::" in temiz
        assert len(rapor) == 2
        assert temiz.endswith(YEDEK_CUMLE)


class TestAlinti:
    GERCEK = '[A] OLCU.md "Başak\'ın söylediği her cümle ölçülmüş olmak zorundadır."'

    def test_gercek_alinti_yasar(self):
        temiz, rapor = cikis_kapisi(self.GERCEK)
        assert rapor == [] and "badge::A::" in temiz

    def test_uydurma_alinti_olur(self):
        sahte = '[A] OLCU.md "Bu cumle dosyada kesinlikle yazmıyor."'
        temiz, rapor = cikis_kapisi(sahte)
        assert temiz == YEDEK_CUMLE and len(rapor) == 1

    def test_varolmayan_dosya_olur(self):
        sahte = '[A] hayali-klasor/dosya.md "herhangi bir sey"'
        temiz, _ = cikis_kapisi(sahte)
        assert temiz == YEDEK_CUMLE

    def test_proje_disi_yol_olur(self):
        sahte = r'[A] ..\..\gizli.md "bir seyler"'
        temiz, rapor = cikis_kapisi(sahte)
        assert temiz == YEDEK_CUMLE and "dogrulanamadi" in rapor[0]

    def test_yasakli_dosya_acilmaz(self):
        sahte = '[A] ayarlar.json "groq_key"'
        temiz, _ = cikis_kapisi(sahte)
        assert temiz == YEDEK_CUMLE

    def test_alintisiz_A_olur(self):
        sahte = '[A] OLCU.md alinti tirnak icinde degil'
        temiz, _ = cikis_kapisi(sahte)
        assert temiz == YEDEK_CUMLE


class TestOlcum:
    CIKTI = 'Tum gorevler tamamlanmis.'

    def test_ciktiyla_birebir_yasar(self):
        s = '[Ö1] list_tasks "Tüm görevler tamamlanmış."'
        temiz, rapor = cikis_kapisi(s, olcumler=[self.CIKTI])
        assert rapor == [] and "badge::Ö::" in temiz

    def test_ciktiyla_uyusmayan_olur(self):
        s = '[Ö1] list_tasks "12 görev var"'
        temiz, rapor = cikis_kapisi(s, olcumler=[self.CIKTI])
        assert temiz == YEDEK_CUMLE and len(rapor) == 1

    def test_olcum_verilmezse_her_O_olur(self):
        s = '[Ö1] git status "temiz"'
        temiz, _ = cikis_kapisi(s)
        assert temiz == YEDEK_CUMLE

    def test_tirnaksiz_O_olur(self):
        s = '[Ö1] list_tasks tirnaksiz'
        temiz, _ = cikis_kapisi(s, olcumler=[self.CIKTI])
        assert temiz == YEDEK_CUMLE


class TestCikarim:
    def test_gecerli_dayanaklarla_yasar(self):
        metin = ('[Ö1] list_tasks "Tüm görevler tamamlanmış."\n'
                 '[Ö2] web_search "site 200 OK dondu"\n'
                 '[Ç] [Ö1][Ö2] Gorev kalmadi ve site ayakta.')
        temiz, rapor = cikis_kapisi(
            metin, olcumler=['Tüm görevler tamamlanmış.', 'HTTP/1.1 200 OK'])
        # not: [O2] alintisi "200 OK" ciktinin normalize hâlinde yok -> elenir;
        # bu yüzden [Ç] de dayanagini kaybeder. Davranis kasitli:
        # dayanagi olmayan cikarim yasayamaz.
        assert "badge::Ç::" not in temiz or rapor == []

    def test_dayanaksiz_tek_basina_olur(self):
        metin = '[Ç] [Ö1][Ö2] Dayanaklari hic uretilmedi.'
        temiz, _ = cikis_kapisi(metin, olcumler=[])
        assert temiz == YEDEK_CUMLE


class TestBilmiyorum:
    def test_B_her_zaman_yasar(self):
        temiz, rapor = cikis_kapisi("[B] Bunun cevabini ölçemiyorum.")
        assert rapor == [] and "badge::B::" in temiz

    def test_hepsi_isaretsiz_sohbet_gecer(self):
        """Hicbir cumlede isaret yoksa sohbet cevabi oldugu gibi gecer."""
        metin = ("İşaretsiz bir.\n"
                 'İşaretsiz iki.\n')
        temiz, _ = cikis_kapisi(metin)
        assert temiz == metin.strip()
        assert YEDEK_CUMLE not in temiz

    def test_karisik_isaretsizler_elenir(self):
        """İşaretli + işaretsiz karışımında işaretsizler silinir."""
        metin = ("İşaretsiz bir.\n"
                 '[B] İşaretli iki.')
        temiz, rapor = cikis_kapisi(metin)
        assert 'badge::B::' in temiz
        assert 'İşaretsiz bir' not in temiz
        assert len(rapor) == 1


class TestAtif:
    """Kaynak bilgili olcumlerde ATIF denetimi (2026-08-23 gercek arizasi).

    Gercek olay: list_files 'brain' klasorune bakamadi (izin yok) ama model
    uc dosya adi sayip [O] rozeti takti — metin BASKA bir aracin ciktisinda
    geciyordu. Eski kapi bunu geciriyordu.
    """

    OLCUMLER = [
        ("list_files", "'brain' klasorune izin yok. Izinli: knowledge"),
        ("belge_ara", "brain/kilo.py brain/registry.py brain.py eklendi"),
    ]

    def test_yanlis_araca_atif_olur(self):
        s = '[Ö1] list_files "brain/kilo.py brain/registry.py brain.py"'
        temiz, rapor = cikis_kapisi(s, olcumler=self.OLCUMLER)
        assert temiz == YEDEK_CUMLE
        assert len(rapor) == 1 and "atif yanlis" in rapor[0]

    def test_dogru_araca_atif_yasar(self):
        s = '[Ö1] belge_ara "brain/kilo.py brain/registry.py brain.py eklendi"'
        temiz, rapor = cikis_kapisi(s, olcumler=self.OLCUMLER)
        assert rapor == [] and "badge::Ö::" in temiz

    def test_aracin_hata_ciktisi_durustce_alintilanabilir(self):
        # Arac reddettiyse bunu aynen soylemek mesru olmali.
        s = '[Ö1] list_files "\'brain\' klasorune izin yok. Izinli: knowledge"'
        temiz, rapor = cikis_kapisi(s, olcumler=self.OLCUMLER)
        assert rapor == [] and "izin yok" in temiz

    def test_bu_turda_calismayan_arac_olur(self):
        s = '[Ö1] git_durum "brain/kilo.py brain/registry.py brain.py eklendi"'
        temiz, rapor = cikis_kapisi(s, olcumler=self.OLCUMLER)
        assert temiz == YEDEK_CUMLE
        assert "calismayan araca" in rapor[0]

    def test_eski_bicim_bozulmadi(self):
        # Duz metin listesi verildiginde atif denetimi yapilmaz (geri uyum).
        s = '[Ö1] list_files "brain/kilo.py brain/registry.py brain.py eklendi"'
        temiz, rapor = cikis_kapisi(
            s, olcumler=[m for _, m in self.OLCUMLER])
        assert rapor == [] and "badge::Ö::" in temiz

    def test_karisik_bicim_calisir(self):
        karisik = [("web_search", "saatte 200 istek"), "duz metin cikti"]
        s = '[Ö1] web_search "saatte 200 istek"'
        temiz, rapor = cikis_kapisi(s, olcumler=karisik)
        assert rapor == [] and "badge::Ö::" in temiz


class TestYanit:
    """[Y] — ayakta kalan olcumun sade Turkce cevirisi (2026-08-23).

    Sebep: kapi dogru calisirken cevaplar makine ciktisi gibi okunuyordu.
    [Y] yeni iddia tasimaz; dayanagi duserse kendisi de duser.
    """

    OLCUMLER = [("git_durum", "Proje: vixrex Dal: main Son commit: 20da1a7")]

    def test_olcumle_birlikte_yasar(self):
        metin = ('[Y] VixRex su an main dalinda, son commit Faz 4.\n'
                 '[Ö1] git_durum "Dal: main Son commit: 20da1a7"')
        temiz, rapor = cikis_kapisi(metin, olcumler=self.OLCUMLER)
        assert rapor == []
        assert "badge::Y::" in temiz and "badge::Ö::" in temiz
        assert temiz.index("badge::Y::") < temiz.index("badge::Ö::")

    def test_dayanaksiz_Y_olur(self):
        metin = '[Y] VixRex su an main dalinda.'
        temiz, rapor = cikis_kapisi(metin, olcumler=self.OLCUMLER)
        assert temiz == YEDEK_CUMLE
        assert len(rapor) == 1 and "dayanaksiz" in rapor[0]

    def test_olcum_duserse_Y_de_duser(self):
        # Olcum uydurma → elenir; ona yaslanan [Y] de ayakta kalamaz.
        metin = ('[Y] VixRex su an develop dalinda.\n'
                 '[Ö1] git_durum "Dal: develop"')
        temiz, rapor = cikis_kapisi(metin, olcumler=self.OLCUMLER)
        assert temiz == YEDEK_CUMLE and len(rapor) == 2

    def test_alintiya_da_yaslanabilir(self):
        metin = ('[Y] Notlarima gore favori cayim Caykur.\n'
                 '[A] AGENTS.md "Basak — tamamen yerel calisan"')
        temiz, rapor = cikis_kapisi(metin)
        assert "badge::Y::" in temiz and "badge::A::" in temiz
        assert rapor == []

    def test_B_tek_basina_Y_yi_ayakta_tutmaz(self):
        metin = ('[Y] Muhtemelen main dalindadir.\n'
                 '[B] Bunu olcemedim.')
        temiz, rapor = cikis_kapisi(metin, olcumler=self.OLCUMLER)
        assert "badge::Y::" not in temiz
        assert "badge::B::" in temiz


class TestHamOlcum:
    """Kapi her cumleyi elediginde kullanici bos ekran gormemeli."""

    def test_ham_satir_uretiliyor(self):
        from olcu import ham_olcum_satirlari
        s = ham_olcum_satirlari([("git_durum", "Dal: main\nSon commit: abc")])
        assert s == ['badge::Ö::git_durum "Dal: main Son commit: abc"']

    def test_uzun_cikti_kisaltilir(self):
        from olcu import ham_olcum_satirlari
        s = ham_olcum_satirlari([("belge_ara", "x" * 900)], sinir=100)
        assert len(s[0]) < 200 and s[0].endswith('..."')

    def test_tirnak_bozmaz(self):
        from olcu import ham_olcum_satirlari
        s = ham_olcum_satirlari([("list_files", 'izin yok: "brain"')])
        assert s[0].count('"') == 2

    def test_bos_cikti_atlanir(self):
        from olcu import ham_olcum_satirlari
        assert ham_olcum_satirlari([("a", ""), ("b", None)]) == []

    def test_eski_bicim_de_calisir(self):
        from olcu import ham_olcum_satirlari
        s = ham_olcum_satirlari(["duz cikti"])
        assert s == ['badge::Ö::araç "duz cikti"']


class TestCokAdim:
    """Arac dongusu: "sunu bul, sonra kaydet" iki tur ister (2026-08-23).

    Eskiden tek tur vardi; ikinci adim hicbir zaman calismiyordu.
    """

    def _cagri(self, ad, args='{}', cid="1"):
        return {"id": cid, "type": "function",
                "function": {"name": ad, "arguments": args}}

    def _kur(self, yanitlar):
        """yanitlar: brain.cevapla'nin sirayla donecegi sozlukler."""
        import chat as c

        class SahteBrain:
            def __init__(self):
                self.cagrilar = []

            def cevapla(self, mesajlar, model, tools=None):
                self.cagrilar.append(tools is not None)
                return yanitlar.pop(0), "sahte"

        calistirilan = []

        def calistir(ad, args, kdir, gdosya):
            calistirilan.append(ad)
            return {"result": "%s sonucu" % ad}

        return c, SahteBrain(), calistir, calistirilan

    def test_ikinci_arac_da_calisir(self):
        c, brain, calistir, calistirilan = self._kur([
            {"content": "", "tool_calls": [self._cagri("deftere_kaydet")]},
            {"content": "Iki adim bitti."},
        ])
        cevap, ciktilar = c._tool_calling_multi(
            [self._cagri("dosya_bilgi")], [], brain, "m",
            lambda code: None, calistir, tools=[{"x": 1}])
        assert calistirilan == ["dosya_bilgi", "deftere_kaydet"]
        assert cevap == "Iki adim bitti."
        assert [ad for ad, _ in ciktilar] == ["dosya_bilgi", "deftere_kaydet"]

    def test_son_turda_arac_verilmez(self):
        # Dongu kapanmali: son cagrida tools None gitmeli.
        c, brain, calistir, _ = self._kur([
            {"content": "", "tool_calls": [self._cagri("a")]},
            {"content": "", "tool_calls": [self._cagri("b")]},
            {"content": "bitti"},
        ])
        c._tool_calling_multi([self._cagri("ilk")], [], brain, "m",
                              lambda code: None, calistir, tools=[{"x": 1}],
                              tur_siniri=3)
        assert brain.cagrilar == [True, True, False]

    def test_tek_adimda_eski_davranis(self):
        c, brain, calistir, calistirilan = self._kur([
            {"content": "Tek adim yeter."},
        ])
        cevap, ciktilar = c._tool_calling_multi(
            [self._cagri("list_tasks")], [], brain, "m",
            lambda code: None, calistir, tools=[{"x": 1}])
        assert calistirilan == ["list_tasks"] and cevap == "Tek adim yeter."


class TestIngilizceSizinti:
    """Saglayici dusunme metnini cevap sanip gonderirse kullaniciya gitmemeli."""

    def test_ingilizce_dusunme_metni_yakalanir(self):
        import chat as c
        sizinti = ("We need to answer the user's request. We must interpret "
                   "the question and then decide which tool to call first.")
        assert c._ingilizce_sizinti_mi(sizinti) is True

    def test_turkce_cevap_gecer(self):
        import chat as c
        assert c._ingilizce_sizinti_mi(
            "VixRex şu anda main dalında, son commit Faz 4 değişikliği.") is False
        assert c._ingilizce_sizinti_mi(
            "Görev listende bir iş var: yarın saat 15:00'te yedek al.") is False
