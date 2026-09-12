"""brain/kapasite.py — geriye uyumlu tam kapasite katmani.

Basak artik saglayicilari "kucuk/guclu" diye ayirip hafiza, arac veya
cok-adimli calisma yeteneklerini kismaz. Bu modul yalniz eski importlari
kirmamak icin korunur; tum modeller ayni uygulama yetkilerine sahiptir.
Guvenlik ve kullanici onayi ayri izin katmaninda uygulanmaya devam eder.
"""


class Kapasite:
    def __init__(self, guclu=True, mod="tam"):
        self.guclu = True
        self.mod = "tam"

    @property
    def kucuk(self):
        return False

    def __repr__(self):
        return "Kapasite(guclu=True, mod=tam)"


def mod_kapasite(model_adi=None, kaynak=None, kaynaklar=None):
    """Geriye uyum icin her zaman tam kapasite dondurur."""
    return Kapasite(True, "tam")
