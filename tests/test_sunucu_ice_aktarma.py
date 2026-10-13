"""tests/test_sunucu_ice_aktarma.py — sunucu, masaüstü kütüphaneleri olmadan açılır.

2026-10-13 ÖLÇÜMÜ (kök neden): `voice/__init__.py` modül yüklenirken TTS ve
STT'yi içe aktarıyordu; `voice/tts.py` -> `sounddevice` -> PortAudio sistem
kütüphanesi. Bu kütüphaneler requirements.txt'te yalnız
`sys_platform == "win32"` için kurulur. Dolayısıyla `voice` — ve onu çeken
`basak_app` — Linux'ta hiç yüklenemiyordu:

    $ pytest tests -q
    ERROR tests/test_kapanis_db.py
    OSError: PortAudio library not found
    !!! Interrupted: 1 error during collection !!!

ÜRETİM (Vercel) LINUX'TUR. Yani test paketi, kodun çalıştığı platformda
toplanamıyordu ve bu sessizce "testler yeşil" sayılıyordu.

Neden subprocess: aynı süreçte import edilmiş modüller sys.modules'ta
kalır; engelleyici ancak temiz bir yorumlayıcıda GERÇEK koşulu taklit eder.
Neden engelleyici: CI Windows'ta koşar, orada bu kütüphaneler KURULUDUR;
kurulu olduğu için hata görünmez. Engelleyici, "bu kütüphane yok" durumunu
Windows'ta da zorlar — yani kapı, arızayı üretim platformuna gitmeden
yakalar.

Kapsam bilinçlidir: masaüstü modüllerinin (tray.py, voice/*) KENDİ içinde
modül seviyesinde bu kütüphaneleri içe aktarması doğrudur — onların işi bu.
Ölçülen kural şudur: SUNUCU GİRİŞİ (`app.py`) ve onun çektiği her şey, bu
kütüphaneler yokken de yüklenebilmelidir.
"""

import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parents[1]

# Yalnız masaüstünde kurulan üst düzey paketler (requirements.txt'te
# `sys_platform == "win32"`).
MASAUSTU_PAKETLERI = (
    "webview", "pystray", "PIL", "sounddevice", "piper",
    "faster_whisper", "pyannote", "telegram",
)

_ENGEL_KODU = '''
import sys


class _MasaustuEngeli:
    """Masaüstü paketlerini 'kurulu değil' gibi gösterir."""

    def find_spec(self, tam_ad, yol=None, hedef=None):
        kok = tam_ad.split(".")[0]
        if kok in YASAK:
            raise ModuleNotFoundError(
                "engellendi (test): %s kurulu degil gibi davraniliyor" % tam_ad)
        return None


sys.meta_path.insert(0, _MasaustuEngeli())
import app  # noqa: E402  (sunucu girisi)
print("SUNUCU_IMPORT_OK")
'''


def _kos(hedef, yasak):
    kod = "YASAK = %r\n" % (tuple(yasak),) + _ENGEL_KODU + "import %s\n" % hedef
    return subprocess.run(
        [sys.executable, "-c", kod],
        cwd=str(KOK), capture_output=True, text=True, timeout=180,
    )


class TestSunucuMasaustuKutuphanesizAcilir:
    def test_app_py_masaustu_kutuphaneleri_yokken_import_edilir(self):
        s = _kos("app", MASAUSTU_PAKETLERI)
        assert "SUNUCU_IMPORT_OK" in s.stdout, (
            "app.py, masaüstü kütüphaneleri yokken içe aktarılamıyor — "
            "üretim Linux'tur, bu sunucuyu düşürür.\nSTDOUT:\n%s\nSTDERR:\n%s"
            % (s.stdout[-2000:], s.stderr[-4000:]))

    def test_voice_bagimsiz_yuklenir(self):
        """`import voice` ses kütüphanesi istememeli (kök neden buydu)."""
        s = _kos("voice", MASAUSTU_PAKETLERI)
        assert "SUNUCU_IMPORT_OK" in s.stdout, (
            "voice paketi ses kütüphanesi yokken yüklenemiyor.\n%s"
            % s.stderr[-4000:])

    def test_engelleyici_gercekten_engelliyor(self):
        """Kapı sahte olmasın: engelleyici devredeyken paket çözülemez."""
        kod = (
            "YASAK = %r\n" % (MASAUSTU_PAKETLERI,)
            + _ENGEL_KODU.replace("import app", "")
            + "\ntry:\n    import sounddevice\nexcept ModuleNotFoundError:\n"
              "    print('ENGELLENDI')\n"
        )
        s = subprocess.run([sys.executable, "-c", kod], cwd=str(KOK),
                           capture_output=True, text=True, timeout=120)
        assert "ENGELLENDI" in s.stdout, s.stderr[-2000:]
