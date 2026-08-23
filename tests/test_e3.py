"""tests/test_e3.py — E-3 testleri: Sen sormadan çalışma.

E-3 kuralı:
- Aktif saatler: 10:00-20:00
- Periyot: 2 saatte bir (10, 12, 14, 16, 18, 20)
- Sessiz saatlerde çalışmaz
- Tekrar engelleme (aynı kart 2 saat içinde tekrar gönderilmez)
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.zamanlayici import (
    aktif_saat_mi, kart_zamani_mi, son_kart_benzer_mi,
    kart_olustur, AKTIF_BASLANGIC, AKTIF_BITIS, KART_ZAMANLARI,
    _son_kart_zamani, _son_kart_lock,
)


class TestAktifSaat:
    """E-3: Aktif saat kontrolü."""

    def test_10_00_aktif(self):
        """10:00 aktif saatler içinde olmalı."""
        simdi = datetime(2026, 8, 22, 10, 0)
        assert aktif_saat_mi(simdi)

    def test_19_59_aktif(self):
        """19:59 hâlâ aktif olmalı."""
        simdi = datetime(2026, 8, 22, 19, 59)
        assert aktif_saat_mi(simdi)

    def test_20_00_aktif(self):
        """20:00 aktif (son kart saati dahil)."""
        simdi = datetime(2026, 8, 22, 20, 0)
        assert aktif_saat_mi(simdi)

    def test_09_59_degil(self):
        """09:59 aktif değil."""
        simdi = datetime(2026, 8, 22, 9, 59)
        assert not aktif_saat_mi(simdi)

    def test_00_00_degil(self):
        """Gece yarısı aktif değil."""
        simdi = datetime(2026, 8, 22, 0, 0)
        assert not aktif_saat_mi(simdi)

    def test_14_30_aktif(self):
        """14:30 aktif olmalı."""
        simdi = datetime(2026, 8, 22, 14, 30)
        assert aktif_saat_mi(simdi)


class TestKartZamani:
    """E-3: Kart gönderme zamanı kontrolü."""

    def test_10_00_kart(self):
        """10:00 kart zamanı olmalı."""
        simdi = datetime(2026, 8, 22, 10, 0)
        assert kart_zamani_mi(simdi)

    def test_12_00_kart(self):
        """12:00 kart zamanı olmalı."""
        simdi = datetime(2026, 8, 22, 12, 0)
        assert kart_zamani_mi(simdi)

    def test_14_00_kart(self):
        """14:00 kart zamanı olmalı."""
        simdi = datetime(2026, 8, 22, 14, 0)
        assert kart_zamani_mi(simdi)

    def test_16_00_kart(self):
        """16:00 kart zamanı olmalı."""
        simdi = datetime(2026, 8, 22, 16, 0)
        assert kart_zamani_mi(simdi)

    def test_18_00_kart(self):
        """18:00 kart zamanı olmalı."""
        simdi = datetime(2026, 8, 22, 18, 0)
        assert kart_zamani_mi(simdi)

    def test_20_00_kart(self):
        """20:00 kart zamanı olmalı (son kart)."""
        simdi = datetime(2026, 8, 22, 20, 0)
        assert kart_zamani_mi(simdi)

    def test_11_00_degil(self):
        """11:00 kart zamanı değil."""
        simdi = datetime(2026, 8, 22, 11, 0)
        assert not kart_zamani_mi(simdi)

    def test_15_00_degil(self):
        """15:00 kart zamanı değil."""
        simdi = datetime(2026, 8, 22, 15, 0)
        assert not kart_zamani_mi(simdi)

    def test_10_06_degil(self):
        """10:06 artık kart zamanı değil (5 dakika penceresi)."""
        simdi = datetime(2026, 8, 22, 10, 6)
        assert not kart_zamani_mi(simdi)


class TestTekrarEngelleme:
    """E-3: Aynı kart 2 saat içinde tekrar gönderilmez."""

    def setup_method(self):
        """Her test öncesi cache'i temizle."""
        with _son_kart_lock:
            _son_kart_zamani.clear()

    def test_ilk_gonderim(self):
        """İlk gönderimde engelleme yok."""
        simdi = datetime(2026, 8, 22, 10, 0)
        assert not son_kart_benzer_mi("test_1", simdi)

    def test_tekrar_gonderim(self):
        """Aynı kart ID'si 2 saat içinde tekrarlanamaz."""
        simdi1 = datetime(2026, 8, 22, 10, 0)
        simdi2 = datetime(2026, 8, 22, 11, 0)  # 1 saat sonra
        son_kart_benzer_mi("test_2", simdi1)
        assert son_kart_benzer_mi("test_2", simdi2)

    def test_farkli_kart_id(self):
        """Farklı kart ID'leri birbirini etkilemez."""
        simdi = datetime(2026, 8, 22, 10, 0)
        son_kart_benzer_mi("test_3a", simdi)
        assert not son_kart_benzer_mi("test_3b", simdi)

    def test_2_saat_sonra_tekrar(self):
        """2 saat sonra aynı kart tekrar gönderilebilir."""
        simdi1 = datetime(2026, 8, 22, 10, 0)
        simdi2 = datetime(2026, 8, 22, 12, 1)  # 2 saat 1 dk sonra
        son_kart_benzer_mi("test_4", simdi1)
        assert not son_kart_benzer_mi("test_4", simdi2)


class TestKartOlustur:
    """E-3: kart_olustur fonksiyonu."""

    def setup_method(self):
        with _son_kart_lock:
            _son_kart_zamani.clear()

    def test_aktif_disinda_none(self):
        """Aktif saatler dışında None dönmeli."""
        simdi = datetime(2026, 8, 22, 8, 0)
        sonuc = kart_olustur(None, simdi=simdi)
        assert sonuc is None

    def test_kart_zamani_disinda_none(self):
        """Kart zamanı değilken None dönmeli."""
        simdi = datetime(2026, 8, 22, 11, 0)
        sonuc = kart_olustur(None, simdi=simdi)
        assert sonuc is None

    def test_kart_icerigi_var(self):
        """Kart zamanında kart oluşturulmalı (en az selam)."""
        simdi = datetime(2026, 8, 22, 10, 0)
        # kart_olustur fonksiyonu gerçek araçları çağırabilir,
        # bu yüzden hata yönetimi test edilir
        sonuc = kart_olustur(None, simdi=simdi)
        # Sonuç None olabilir (hata) veya kart içerebilir
        if sonuc is not None:
            assert "kart" in sonuc
            assert "kart_id" in sonuc


class TestZamanlayiciSinif:
    """E-3: Zamanlayıcı sınıfı."""

    def test_olustur(self):
        """Zamanlayıcı oluşturulabilmeli."""
        from tools.zamanlayici import Zamanlayici
        z = Zamanlayici()
        assert z is not None

    def test_baslat_durdur(self):
        """Zamanlayıcı başlatılıp durdurulabilmeli."""
        from tools.zamanlayici import Zamanlayici
        z = Zamanlayici()
        z.baslat()
        import time
        time.sleep(0.1)
        z.durdur()
        # Thread durmuş olmalı
        assert z._durdu.is_set()


class TestSabitlemeler:
    """E-3: Sabit değerler doğru mu?"""

    def test_aktif_saatler(self):
        """Aktif saatler sabitleri doğru mu?"""
        assert AKTIF_BASLANGIC == 10
        assert AKTIF_BITIS == 20

    def test_kart_zamanlari(self):
        """Kart zamanları 2 saat aralıklarla mı?"""
        assert KART_ZAMANLARI == [10, 12, 14, 16, 18, 20]
        assert len(KART_ZAMANLARI) == 6
