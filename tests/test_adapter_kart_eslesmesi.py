"""tests/test_adapter_kart_eslesmesi.py — kesfedilen her adaptörün karti var.

Denetim bulgusu (2026-10-01): "ovh/sambanova adaptörleri kesfedilir ama
registry karti yok". Kok neden: keşif (brain.adapters.registry.
discover_all) ile kart tablosu (brain.registry.SAGLAYICILAR) arasindaki
baglanti HIC denetlenmiyordu — kartsiz saglayici sessizce disda
kaliyordu, kimse farketmiyordu.

Not: ovh/sambanova dosyalari bu DEPODA HIC YOK (git gecmisinde de yok);
Casper'in yerel Windows makinesinde bulunan commit edilmemis dosyalar.
Yani hata tekrarlanabilir: adaptör dosyasi eklenir, kart unutulur.

Bu test baglantiyi IKI YONLU kilitler:
1. kesfedilen -> kart VAR: kartsiz adaptör eklenirse test KIRMIZI olur,
2. kart -> adaptör VAR: olu kart, calismayan/var olmayan saglayici
   icin sahte varlik birakmaz.

Hata mesaji ne yapilacagini soyler (AGENTS.md: "iddia yok, resmi belge
var" — kartin veri_saklama iddiasi resmî belgesiz YAZILMAZ).
"""

import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))


def _durum():
    from brain import registry
    from brain.adapters.registry import discover_all
    return set(discover_all()), set(registry.SAGLAYICILAR)


def test_kesfedilen_her_saglayicinin_karti_var():
    kesfedilen, kartli = _durum()
    kartsiz = sorted(kesfedilen - kartli)
    assert not kartsiz, (
        "Kartsiz saglayici: %s — adaptör keşfediliyor ama registry "
        "kartı yok; zincirin dışında kalıyor ve kimse fark etmiyor. "
        "Ya brain/registry.py'ye resmî belgeyle kart ekle (veri_saklama "
        "+ kaynak zorunlu) ya da adaptör dosyasını kaldır. "
        "(AGENTS.md: iddia yok, resmî belge var)"
        % ", ".join(kartsiz)
    )


def test_her_kartin_adaptoru_var():
    kesfedilen, kartli = _durum()
    adaptorsuz = sorted(kartli - kesfedilen)
    assert not adaptorsuz, (
        "Adaptörü olmayan kart: %s — kart var ama adaptör "
        "keşfedilemiyor (dosya silindi mi, import mu patlıyor?). "
        "Kart, çalışmayan sağlayıcı için sahte varlık bırakmaz; "
        "ya adaptörü geri getir ya da kartı kaldır."
        % ", ".join(adaptorsuz)
    )
