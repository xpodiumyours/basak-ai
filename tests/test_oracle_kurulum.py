"""Oracle kurulumunun sessizce bozulmasini engelleyen sozlesme testleri.

Gecmis hata: setup.sh silinmis bir feature dalini (feat/freetools-koprosu)
sabit kodluyordu; sunucu guncellemesi fetch asamasinda duruyordu. Ikinci
eksik: betik yalniz web servisini kuruyordu, kalici gorev iscisi yoktu.
"""
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
SETUP = (KOK / 'deploy' / 'oracle' / 'setup.sh').read_text(encoding='utf-8')
ISCI = (KOK / 'deploy' / 'oracle' / 'basak-isci.service').read_text(encoding='utf-8')
ENV = (KOK / 'deploy' / 'oracle' / 'basak.env.ornek').read_text(encoding='utf-8')
UZAK = (KOK / 'deploy' / 'oracle' / 'uzaktan-kur.sh').read_text(encoding='utf-8')


def test_dal_sabit_kodlanmaz_ve_varsayilan_main():
    assert 'BRANCH="${BASAK_BRANCH:-main}"' in SETUP
    assert 'feat/freetools-koprosu' not in SETUP


def test_kurulum_iki_servisi_de_kurar():
    assert 'basak.service' in SETUP
    assert 'basak-isci.service' in SETUP
    assert 'systemctl enable --now basak caddy unattended-upgrades basak-isci' in SETUP


def test_isci_webden_bagimsiz_ve_ayni_ortami_okur():
    assert 'python -m worker.platform' in ISCI
    assert 'EnvironmentFile=/etc/basak/basak.env' in ISCI
    assert 'Restart=always' in ISCI
    # Web birimi isciyi baslatmaz; isci web cokse de yasar.
    assert 'basak-isci' not in (KOK / 'deploy' / 'oracle' / 'basak.service').read_text(encoding='utf-8')


def test_iscinin_ortak_veritabani_gereksinimi_belgelenir():
    assert 'BASAK_CONNECTION_KEY=' in ENV
    assert 'DATABASE_URL=' in ENV
    assert 'platform_isciler' in SETUP
    assert 'DATABASE_URL bos' in SETUP


def test_uzaktan_kurulum_dali_ve_kurulumu_iletir():
    assert 'git reset --hard "origin/$DAL"' in UZAK
    assert 'deploy/oracle/setup.sh' in UZAK
    assert 'StrictHostKeyChecking=accept-new' in UZAK
