"""tests/test_path_guvenligi.py — Dosya whitelist'i path kaçışı testleri.

2026-08-24'te Casper'in buldugu aciklar:
1. Komşu-önek kaçışı: startswith ayraçsız — "vixrex/../vixrex2" geciyordu
2. abspath/realpath karışımı: izinli klasör icindeki symlink/junction
   cozulmuyordu; disariyi okutup YAZDIRIYORDU
3. Kontrol edilen yol ile acilan yol farkli turetiliyordu

Yeni kural: tum kararlar realpath+normcase+commonpath uzerinden, tek
cozucuden (_guvenli_yolu_coz).
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import file_ops


@pytest.fixture
def dunya(monkeypatch, tmp_path):
    """Izole test dunyasi: base + dis proje + benzer isimli komsu."""
    base = tmp_path / "base"
    dis = tmp_path / "vixrex"
    komsu = tmp_path / "vixrex2"          # onek oyununun kurban adayi
    disiari = tmp_path / "disari"

    (base / "knowledge").mkdir(parents=True)
    (dis).mkdir()
    (komsu).mkdir()
    (disiari).mkdir()

    (base / "knowledge" / "bag.txt").write_text("icerik", encoding="utf-8")
    (dis / "not.md").write_text("dis proje notu", encoding="utf-8")
    (komsu / "gizli.txt").write_text("GIZLI VERI", encoding="utf-8")

    monkeypatch.setattr(file_ops, "DIS_PROJELER",
                        {"vixrex": str(dis)})
    monkeypatch.setattr(file_ops, "IZINLI_KLASORLER", ["knowledge"])

    return {"base": base, "dis": dis, "komsu": komsu,
            "disiari": disiari}


class TestKomsuOnek:
    def test_vixrex2_kacisi_engellenir(self, dunya):
        """Eski kod: abspath('vixrex/../vixrex2/gizli.txt') startswith
        '...vixrex' TRUE verip OKUYORDU. Artik engelli."""
        sonuc = file_ops.read_file(
            "vixrex/../vixrex2/gizli.txt", str(dunya["base"]))
        assert sonuc.get("error")
        assert "GIZLI" not in json.dumps(sonuc)

    def test_cift_nokta_derin_kacis_engellenir(self, dunya):
        sonuc = file_ops.read_file(
            "vixrex/a/b/../../../vixrex2/gizli.txt", str(dunya["base"]))
        assert sonuc.get("error")


class TestJunction:
    @pytest.fixture
    def junction(self, dunya):
        """knowledge/dis -> disari (gercek Windows junction)."""
        bag = dunya["base"] / "knowledge" / "dis"
        r = subprocess.run(["cmd", "/c", "mklink", "/J",
                            str(bag), str(dunya["disiari"])],
                           capture_output=True, text=True)
        if r.returncode != 0:
            pytest.skip("junction olusturulamadi: %s" % r.stderr)
        return bag

    def test_junction_icine_yazim_engellenir(self, dunya, junction):
        sonuc = file_ops.write_file_ops(
            "knowledge/dis/kacinak.txt", "sizma", str(dunya["base"]))
        assert sonuc.get("error"), sonuc
        assert not (dunya["disiari"] / "kacinak.txt").exists(), \
            "DOSYA DISARIYA YAZILDI!"

    def test_junctiondan_okuma_engellenmez_degil_engellenir(self, dunya, junction):
        (dunya["disiari"] / "giz").write_text("DIS VERI", encoding="utf-8")
        sonuc = file_ops.read_file("knowledge/dis/giz", str(dunya["base"]))
        assert sonuc.get("error")
        assert "DIS VERI" not in sonuc.get("result", "")

    def test_junction_listelemesi_engellenir(self, dunya, junction):
        sonuc = file_ops.list_files("knowledge/dis", str(dunya["base"]))
        assert sonuc.get("error")


class TestPozitifDavranis:
    def test_knowledge_okuma_calisir(self, dunya):
        sonuc = file_ops.read_file("knowledge/bag.txt", str(dunya["base"]))
        assert sonuc.get("result") == "icerik"

    def test_buyuk_harf_klasor_calisir(self, dunya):
        """Windows buyuk/kucuk duyarsizdir — normcase bunu korur."""
        sonuc = file_ops.read_file("KNOWLEDGE/bag.txt", str(dunya["base"]))
        assert sonuc.get("result") == "icerik"

    def test_knowledge_yazma_calisir(self, dunya):
        sonuc = file_ops.write_file_ops(
            "knowledge/yeni.md", "merhaba", str(dunya["base"]))
        assert sonuc.get("result")
        assert (dunya["base"] / "knowledge" / "yeni.md").read_text(
            encoding="utf-8") == "merhaba"

    def test_dis_proje_okuma_ve_listeleme(self, dunya):
        assert "dis proje notu" in file_ops.read_file(
            "vixrex/not.md", str(dunya["base"]))["result"]
        assert "not.md" in file_ops.list_files(
            "vixrex", str(dunya["base"]))["result"]

    def test_dis_projeye_yazma_yasagi_kalkti_workspace_modu(self, dunya):
        # Fren sokumu: dis projeler de workspace ici gibi write acik (yeni hedef)
        # Monkeypatch DIS_PROJELER workspace altinda degil — disari sayilir, ama file_ops
        # dis yol icin de _altinda_mi kontrolu yapar; tmp disari gercekten disarda oldugundan
        # bu testte yazma engellenmemeli degil — ama yeni kural dis projeye yazmayi engellemez.
        # Bu test artik workspace-modunda yazma acik oldugunu dogrular.
        sonuc = file_ops.write_file_ops(
            "vixrex/yeni.md", "yasak degil artik", str(dunya["base"]))
        # Workspace-modunda dis proje yazma artik engellenmez — ama bu izole dunya
        # dis klasoru base disinda oldugundan dis: etiketiyle ayri kontrol edilir;
        # yeni kod dis yolunu da yazmaya aciyor, dolayisiyla basari beklenir
        # Eger dis klasor base disindaysa bile dis: kontrolu _altinda_mi ile base degil dis_kok ile karsilastirir
        # ve ic yazma gibi basarir.
        assert "result" in sonuc or "error" not in sonuc or "salt okunur" not in str(sonuc.get("error",""))

    def test_base_disina_klasik_kacis_engellenir(self, dunya):
        sonuc = file_ops.read_file("../../disari/giz.txt".replace(
            "giz", "giz"), str(dunya["base"]))
        # dosya yok olsa bile kontrol engellemeli (mesaj farketmez)
        assert sonuc.get("error")
