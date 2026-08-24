"""tests/test_sozlesme_kapisi.py — FAZ 1.2 cevap sözleşmesi kapısı.

Model tek JSON sözleşme üretir: {"yanit", "iddialar"}. Kapı;
- beyan edilen "olcum" iddiasını bu turda koşan araca karşı denetler,
- beyan edilmemiş eylem/ölçüm cümlesini eler,
- düz sohbete dokunmaz.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from olcu import (SOZLESME_PROMPTU, YEDEK_CUMLE, sozlesme_coz,
                  sozlesme_gecerli_mi, sozlesme_kapisi)


class TestSozlesmeCoz:
    def test_duz_json(self):
        ham = '{"yanit": "Merhaba dunya", "iddialar": []}'
        soz = sozlesme_coz(ham)
        assert soz == {"yanit": "Merhaba dunya", "iddialar": []}

    def test_citili_json_ve_cevre_prosi(self):
        ham = ('Tabii, bakalim!\n```json\n'
               '{"yanit": "Selam, nasilsin?", "iddialar": []}\n'
               '```\nIyi gunler dilerim.')
        soz = sozlesme_coz(ham)
        assert soz is not None and soz["yanit"] == "Selam, nasilsin?"

    def test_string_icinde_suslu_parantez(self):
        ham = ('{"yanit": "Dedim ki: \\"obje {icice}\\" tamamdir", '
               '"iddialar": []}')
        soz = sozlesme_coz(ham)
        assert soz is not None
        assert soz["yanit"] == 'Dedim ki: "obje {icice}" tamamdir'

    def test_kaconus_json_none(self):
        assert sozlesme_coz('{"yanit": ') is None
        assert sozlesme_coz("kesinlikle json degil") is None
        assert sozlesme_coz("") is None

    def test_json_dizisi_none(self):
        assert sozlesme_coz("[1, 2, 3]") is None

    def test_sema_disi_yanit_bos_none(self):
        assert sozlesme_coz('{"yanit": "", "iddialar": []}') is None


class TestSozlesmeGecerliMi:
    def test_minimal_gecerli(self):
        s = {"yanit": "Tamamdir.", "iddialar": []}
        assert sozlesme_gecerli_mi(s) is True

    def test_ekstra_anahtarlar_umursanmaz(self):
        s = {"yanit": "Tamamdir.", "iddialar": [
            {"metin": "Tamamdir", "tur": "yok", "fazlalik": 1}], "x": 2}
        assert sozlesme_gecerli_mi(s) is True

    def test_yanit_yok_false(self):
        assert sozlesme_gecerli_mi({"iddialar": []}) is False
        assert sozlesme_gecerli_mi({"yanit": "", "iddialar": []}) is False

    def test_olcum_dayanaksiz_false(self):
        s = {"yanit": "X kaydedildi.", "iddialar": [
            {"metin": "X kaydedildi", "tur": "olcum"}]}
        assert sozlesme_gecerli_mi(s) is False

    def test_tur_gecersiz_false(self):
        s = {"yanit": "Bir sey.", "iddialar": [
            {"metin": "Bir sey", "tur": "dedikodu",
             "dayanak": {"arac": "git_durum"}}]}
        assert sozlesme_gecerli_mi(s) is False

    def test_iddialar_liste_degil_false(self):
        assert sozlesme_gecerli_mi(
            {"yanit": "Sohbet.", "iddialar": "bos"}) is False


class TestSozlesmeKapisi:
    def test_t1_tuzagi_beyansiz_eylem(self):
        """T1 tuzağı: eylem iddiası var, iddia listesi boş → cümle düşer."""
        soz = {"yanit": "Evet, görev kaydedildi.", "iddialar": []}
        temiz, rapor = sozlesme_kapisi(soz)
        assert temiz == YEDEK_CUMLE
        assert rapor["gecerli"] is True and rapor["kullanan_yapi"] is True
        assert rapor["elnen_sayisi"] == 1
        assert rapor["elennen"][0]["neden"] == "beyan_edilmemis_eylem"

    def test_durust_beyan_tamami_yasar(self):
        """Aynı cümle beyanlı + kanıt aracı koştu → hiçbir şey elenmez."""
        soz = {
            "yanit": "Evet, görev kaydedildi.",
            "iddialar": [{"metin": "görev kaydedildi", "tur": "olcum",
                          "dayanak": {"arac": "list_tasks"}}],
        }
        temiz, rapor = sozlesme_kapisi(
            soz, olcumler=[("list_tasks", '{"gorevler": ["alisveris"]}')])
        assert temiz == "Evet, görev kaydedildi."
        assert rapor["elnen_sayisi"] == 0
        assert rapor["kosan_araclar"] == ["listtasks"]

    def test_kanit_yok_arac_uyusmazligi(self):
        soz = {
            "yanit": "Gorev listesi su an bos.",
            "iddialar": [{"metin": "Gorev listesi su an bos",
                          "tur": "olcum",
                          "dayanak": {"arac": "git_durum"}}],
        }
        temiz, rapor = sozlesme_kapisi(
            soz, olcumler=[("web_search", "hava durumu istanbul")])
        assert "bos" not in temiz and "web_search" in temiz
        assert rapor["elennen"][0]["neden"] == "kanit_yok"

    def test_kismi_elik_sadece_szintiriyon_duser(self):
        soz = {
            "yanit": ("Listede iki acik gorev var.\n"
                      "Bu arada yeni bir not deftere kaydedildi."),
            "iddialar": [{"metin": "iki acik gorev var", "tur": "olcum",
                          "dayanak": {"arac": "list_tasks"}}],
        }
        temiz, rapor = sozlesme_kapisi(
            soz, olcumler=[("list_tasks", "{}")])
        assert "iki acik gorev var" in temiz
        assert "kaydedildi" not in temiz
        assert rapor["elnen_sayisi"] == len(rapor["elennen"]) == 1
        assert rapor["elennen"][0]["neden"] == "beyan_edilmemis_eylem"

    def test_hepsi_elendi_aracli_ham_satirlar_doner(self):
        soz = {"yanit": "Gorev kaydedildi.", "iddialar": []}
        temiz, rapor = sozlesme_kapisi(
            soz, olcumler=[("list_tasks", '{"gorevler": []}')])
        assert "list_tasks" in temiz and "kaydedildi" not in temiz
        assert rapor["kosan_araclar"] == ["listtasks"]

    def test_sohbet_degismez_sifir_elik(self):
        metin = "Selam, nasilsin, bugun ne yaptin?"
        temiz, rapor = sozlesme_kapisi({"yanit": metin, "iddialar": []})
        assert temiz == metin
        assert rapor["elnen_sayisi"] == 0 and rapor["elennen"] == []

    def test_olcum_alani_beyansiz_aracli_turn(self):
        """Araç turu: beyansız commit-hash cümlesi düşer, nötr sohbet yaşar."""
        soz = {
            "yanit": ("Son degisiklik 3ce42e3 ile geldi.\n"
                      "Bu arada hava bugun cok guzeldi."),
            "iddialar": [],
        }
        temiz, rapor = sozlesme_kapisi(
            soz, olcumler=[("git_log", "commit 3ce42e3 feat(vitrin)")])
        assert "3ce42e3" not in temiz and "degisiklik" not in temiz
        assert "hava bugun cok guzeldi" in temiz
        assert [e["neden"] for e in rapor["elennen"]] == \
            ["olcum_alani_beyansiz"]

    def test_negasyon_iddia_degildir_yasar(self):
        soz = {"yanit": "Gorev eklenmedi, uzgunum.", "iddialar": []}
        temiz, rapor = sozlesme_kapisi(soz)
        assert temiz == "Gorev eklenmedi, uzgunum."
        assert rapor["elnen_sayisi"] == 0

    def test_tur_yok_gorusu_dayanaksiz_yasar(self):
        soz = {
            "yanit": "Bence proje harika gidiyor.",
            "iddialar": [{"metin": "Bence proje harika gidiyor",
                          "tur": "yok"}],
        }
        temiz, rapor = sozlesme_kapisi(soz)
        assert temiz == "Bence proje harika gidiyor."
        assert rapor["elnen_sayisi"] == 0


def test_prompt_kisa_ve_sema_ornekli():
    assert isinstance(SOZLESME_PROMPTU, str)
    assert len(SOZLESME_PROMPTU) < 900
    for parca in ('"yanit"', '"iddialar"', '"tur"', '"dayanak"'):
        assert parca in SOZLESME_PROMPTU
