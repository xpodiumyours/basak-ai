"""tests/test_olcu1.py — Ö-1 testleri: ölçüm araçları her zaman sunulur.

Ö-1 kuralı: measurement tools (git_durum, belge_ara, dosya_bilgi) keyword
eşleşmesi beklenmeksizin her zaman modele sunulur. Diğer tool'lar keyword
eşleşmesiyle eklenir.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.definitions import TOOLS


class TestOlcumToolHerZamanMevcut:
    """Ö-1: Measurement araçları TOOLS listesinde ve her zaman erişilebilir."""

    def test_olcum_toollari_tanimli(self):
        """git_durum, belge_ara, dosya_bilgi TOOLS listesinde var mı?"""
        isimler = {t["function"]["name"] for t in TOOLS}
        assert "git_durum" in isimler, "git_durum TOOLS listesinde yok"
        assert "belge_ara" in isimler, "belge_ara TOOLS listesinde yok"
        assert "dosya_bilgi" in isimler, "dosya_bilgi TOOLS listesinde yok"

    def test_olcum_toollari_sadece_okunur(self):
        """Measurement araçları salt-okunur olmalı (yazma/komut yok)."""
        import re
        for tool in TOOLS:
            ad = tool["function"]["name"]
            if ad not in ("git_durum", "belge_ara", "dosya_bilgi"):
                continue
            desc = tool["function"]["description"].lower()
            # Salt okunur araçlarda yazma/komut kelimeleri olmamalı
            # İngilizce git komut adları en güvenilir gösterge
            yasakli_kelimeler = [
                r"\bpush\b", r"\bpull\b", r"\bfetch\b",
                r"\bcheckout\b", r"\breset\b", r"\bmerge\b",
            ]
            for y in yasakli_kelimeler:
                eslesme = re.search(y, desc)
                assert not eslesme, (
                    "%s açıklamasında '%s' kelimesi var — salt okunur olmalı"
                    % (ad, y)
                )

    def test_olcum_toollari_beyaz_listeli_proje_ister(self):
        """Measurement araçlarının parametrelerinde proje zorunlu alan olmalı."""
        for tool in TOOLS:
            ad = tool["function"]["name"]
            if ad not in ("git_durum", "belge_ara", "dosya_bilgi"):
                continue
            params = tool["function"]["parameters"]
            assert "proje" in params.get("properties", {}), (
                "%s aracında proje parametresi yok" % ad
            )
            assert "proje" in params.get("required", []), (
                "%s aracında proje zorunlu alan değil" % ad
            )

    def test_olcum_toollari_diger_toollardan_ayri_isimlere_sahip(self):
        """Measurement tool isimleri diger tool'larla cakismamali."""
        olcum_adi = {"git_durum", "belge_ara", "dosya_bilgi"}
        diger_adi = {t["function"]["name"] for t in TOOLS} - olcum_adi
        assert len(olcum_adi & diger_adi) == 0, (
            "Measurement tool isimleri diger tool'larla cakisiyor"
        )


class TestOlcumPromptKuvvetli:
    """Ö-1: OLCU_YONLENDIRME promptu yeterince guclu mu?"""

    def test_olcu_yonlendirmesi_chat_pyde_var(self):
        """OLCU_YONLENDIRME sabiti chat.py'de tanimli olmali."""
        chat_yolu = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "chat.py",
        )
        with open(chat_yolu, "r", encoding="utf-8") as f:
            icerik = f.read()
        assert "ÖLÇÜM ÖNCE GELİR" in icerik, (
            "chat.py'de ÖLÇÜM ÖNCE GELİR promptu yok"
        )
        # Measurement tools her zaman sunulmali
        assert "_OLCUM_TOOLLARI" in icerik, (
            "chat.py'de _OLCUM_TOOLLARI sabiti yok — measurement araçları "
            "keyword'e bagli kaliyor"
        )
        # Prompt measurement tool adlarini icerir
        for tool_ad in ("git_durum", "belge_ara", "dosya_bilgi"):
            assert tool_ad in icerik, (
                "OLCU_YONLENDIRME'de '%s' aracina referans yok" % tool_ad
            )
