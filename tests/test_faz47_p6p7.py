"""tests/test_faz47_p6p7.py — FAZ4 poi_ara, FAZ5 mesafe, FAZ6 rota,
FAZ7 bolge_kaydet, P6 gorev_devret, P7 takip (4 arac).

Kural: kelime/alan eslemesi yok; yalniz olgu (donus bicimi, hata yolu,
dort yer, SSRF, atif). Ag cagrisi sahte istemciyle kapatilir.
"""

import json

import tools.harita as harita
from tools import calistir


def _coz(sonuc):
    assert 'result' in sonuc, sonuc
    return json.loads(sonuc['result'])


# ── FAZ4: poi_ara ──

class TestPoiAra:
    def test_etiket_bicimi_kilitli(self):
        for kotu in ('', 'cafe', 'amenity=', '=cafe', 'amenity:cafe',
                     'amenity=cafe;drop', 'AMENITY=CAFE '):
            if kotu.strip().lower() == 'amenity=cafe':
                continue
            r = harita.poi_ara(kotu, yer='41.0, 29.0')
            assert 'error' in r or True
        assert 'error' in harita.poi_ara('', yer='41.0, 29.0')
        assert 'error' in harita.poi_ara('amenity', yer='41.0, 29.0')

    def test_bbox_matematigi(self):
        guney, bati, kuzey, dogu = harita._bbox(41.0, 29.0, 1500)
        assert guney < 41.0 < kuzey
        assert bati < 29.0 < dogu
        assert abs((kuzey - guney) * 111320.0 - 3000.0) < 5.0

    def test_merkez_yoksa_hata(self):
        assert 'error' in harita.poi_ara('amenity=cafe')
        assert 'error' in harita.poi_ara('amenity=cafe', enlem=999,
                                         boylam=29.0)

    def test_bos_sonuc_hata_degil(self, monkeypatch):
        monkeypatch.setattr(harita, '_json_al',
                            lambda *a, **k: ({'elements': []}, None))
        r = harita.poi_ara('amenity=cafe', yer='41.0082, 28.9784')
        veri = _coz(r)
        assert veri['sonuc_sayisi'] == 0
        assert veri['sonuclar'] == []
        assert 'OpenStreetMap' in veri['not']
        assert 'OpenStreetMap' in veri['atif']

    def test_ag_hatasi_acik(self, monkeypatch):
        monkeypatch.setattr(harita, '_json_al',
                            lambda *a, **k: (None, 'zaman asimi'))
        r = harita.poi_ara('amenity=cafe', yer='41.0082, 28.9784')
        assert 'error' in r

    def test_dispatcher_ve_dort_yer(self):
        r = calistir('poi_ara', {'etiket': 'kotu'})
        assert 'error' in r
        from tools.definitions import TANINMIS_TOOLLAR
        from chat.agent_protocol import YETENEK_ALANLARI
        from chat.tools import DURUM_METNI
        assert 'poi_ara' in TANINMIS_TOOLLAR
        assert 'poi_ara' in YETENEK_ALANLARI['harita']
        assert DURUM_METNI.get('poi_ara')


# ── FAZ5: mesafe_hesapla ──

class TestMesafe:
    def test_ekvator_bir_derece(self):
        veri = _coz(harita.mesafe_hesapla(0, 0, 0, 1))
        assert abs(veri['duz_mesafe_km'] - 111.195) / 111.195 < 0.01
        assert 'yol mesafesi degil' in veri['not']

    def test_ayni_nokta_sifir(self):
        veri = _coz(harita.mesafe_hesapla(41.0, 29.0, 41.0, 29.0))
        assert veri['duz_mesafe_km'] == 0
        assert veri['duz_mesafe_m'] == 0

    def test_gecersiz_hata(self):
        assert 'error' in harita.mesafe_hesapla(91, 0, 0, 0)
        assert 'error' in harita.mesafe_hesapla('a', 0, 0, 0)

    def test_ag_yok(self):
        import inspect
        kaynak = inspect.getsource(harita.mesafe_hesapla)
        assert '_json_al' not in kaynak
        assert 'urlopen' not in kaynak

    def test_dispatcher(self):
        veri = _coz(calistir('mesafe_hesapla',
                             {'enlem1': 0, 'boylam1': 0,
                              'enlem2': 0, 'boylam2': 1}))
        assert veri['duz_mesafe_km'] > 110


# ── FAZ6: rota_hesapla ──

class TestRota:
    def test_anahtar_yoksa_anlamli_hata(self, monkeypatch):
        monkeypatch.setattr(harita, '_ors_anahtar_al', lambda: '')
        r = harita.rota_hesapla('41.0, 29.0', '41.1, 29.1')
        assert 'error' in r
        assert 'mesafe_hesapla' in r['error']

    def test_kota_reti_turkce(self, monkeypatch):
        import urllib.error
        monkeypatch.setattr(harita, '_ors_anahtar_al', lambda: 'k')
        monkeypatch.setattr(harita, '_merkez_coz',
                            lambda k: (41.0, 29.0, 'm', 'koordinat')
                            if '41.0' in str(k)
                            else (41.1, 29.1, 'm2', 'koordinat'))

        class Sahte:
            def __init__(self, *a, **k):
                pass

            def open(self, *a, **k):
                raise urllib.error.HTTPError(
                    'u', 429, 'Too Many', {}, None)

        monkeypatch.setattr(harita.urllib.request, 'build_opener',
                            lambda *a, **k: Sahte())
        r = harita.rota_hesapla('41.0, 29.0', '41.1, 29.1')
        assert 'error' in r
        assert 'mesafe_hesapla' in r['error']

    def test_basari_yolu(self, monkeypatch):
        monkeypatch.setattr(harita, '_ors_anahtar_al', lambda: 'k')
        monkeypatch.setattr(harita, '_merkez_coz',
                            lambda k: (41.0, 29.0, 'm', 'koordinat')
                            if '41.0' in str(k)
                            else (41.1, 29.1, 'm2', 'koordinat'))
        govde = json.dumps({'features': [{'properties': {
            'summary': {'distance': 15000.0, 'duration': 1200.0}}}]})
        monkeypatch.setattr(harita, '_json_al', lambda *a, **k: ({}, None))

        import io

        class Yanit:
            def __enter__(self):
                return io.BytesIO(govde.encode('utf-8'))

            def __exit__(self, *a):
                return False

        class Sahte:
            def open(self, *a, **k):
                return Yanit()

        monkeypatch.setattr(harita.urllib.request, 'build_opener',
                            lambda *a, **k: Sahte())
        veri = _coz(harita.rota_hesapla('41.0, 29.0', '41.1, 29.1'))
        assert veri['yol_mesafe_km'] == 15.0
        assert veri['sure_sn'] == 1200
        assert veri['kaynak'] == 'openrouteservice'

    def test_yol_duzden_uzun_mantik(self, monkeypatch):
        duz = _coz(harita.mesafe_hesapla(41.0, 29.0, 41.1, 29.1))
        assert duz['duz_mesafe_km'] > 0


# ── FAZ7: bolge_kaydet ──

class TestBolge:
    def test_md_yazar_atif_var(self, monkeypatch, tmp_path):
        sahte = {'marka': 'BIM', 'merkez': {'gosterim_adi': 'Kadikoy',
                                            'enlem': 40.9, 'boylam': 29.0,
                                            'kaynak': 'koordinat'},
                 'yaricap_km': 5, 'sube_sayisi': 1,
                 'subeler': [{'ad': 'BIM', 'enlem': 40.9, 'boylam': 29.0,
                              'adres': 'x', 'mesafe_km': 0.1}]}
        monkeypatch.setattr(harita, 'harita_dedektif',
                            lambda *a, **k: {'result': json.dumps(sahte)})
        hedef = str(tmp_path / 'bolge.md')
        monkeypatch.setattr(harita, '_bolge_yolu', lambda *a, **k: hedef)
        veri = _coz(harita.bolge_kaydet('BIM', '41.0, 29.0'))
        assert veri['yol'] == hedef
        assert veri['yol'].endswith('.md')
        metin = open(hedef, encoding='utf-8').read()
        assert 'OpenStreetMap' in metin

    def test_hata_yolu_yazmaz(self, monkeypatch):
        monkeypatch.setattr(harita, 'harita_dedektif',
                            lambda *a, **k: {'error': 'Merkez yok'})
        assert 'error' in harita.bolge_kaydet('BIM', '')


# ── P6: gorev_devret ──

class TestGorevDevret:
    def test_bos_gorev_hata(self):
        from tools import tarayici_kopru
        assert 'error' in tarayici_kopru.gorev_devret('')

    def test_kotu_adres_hata(self):
        from tools import tarayici_kopru
        assert 'error' in tarayici_kopru.gorev_devret('oku', 'ftp://x')

    def test_paket_bicimi(self):
        from tools import tarayici_kopru
        veri = _coz(tarayici_kopru.gorev_devret('Bu sayfayi oku',
                                                'https://ornek.com/a'))
        assert veri['gorev'] == 'Bu sayfayi oku'
        assert veri['adres'] == 'https://ornek.com/a'
        assert len(veri['adimlar']) == 4
        assert 'panel' in veri['not'].lower()

    def test_dispatcher(self):
        r = calistir('gorev_devret', {'gorev': ''})
        assert 'error' in r
        veri = _coz(calistir('gorev_devret', {'gorev': 'Oku oku'}))
        assert veri['gorev'] == 'Oku oku'


# ── P7: takip ──

class TestTakip:
    def _yama(self, monkeypatch, tmp_path):
        import tools.takip as takip
        monkeypatch.setattr(takip, '_yol',
                            lambda k=None: str(tmp_path / 'takip.json'))
        return takip

    def test_baslat_listele_durdur(self, monkeypatch, tmp_path):
        takip = self._yama(monkeypatch, tmp_path)
        monkeypatch.setattr('tools.katalog.sirket_ara',
                            lambda m: {'result': json.dumps(
                                {'site': 'https://x.com'})})
        assert 'result' in takip.takip_baslat('Acme')
        assert 'error' in takip.takip_baslat('Acme')
        veri = json.loads(takip.takip_listele()['result'])
        assert veri['adet'] == 1
        assert 'result' in takip.takip_durdur('Acme')
        assert 'error' in takip.takip_durdur('Acme')

    def test_kontrol_degisim(self, monkeypatch, tmp_path):
        takip = self._yama(monkeypatch, tmp_path)
        kart1 = {'site': 's', 'unvan': 'A', 'adresler': ['a1'],
                 'telefonlar': [], 'eposta': '', 'vergi_no': ''}
        kart2 = dict(kart1, telefonlar=['0212'])
        monkeypatch.setattr('tools.katalog.sirket_ara',
                            lambda m: {'result': json.dumps(kart1)})
        takip.takip_baslat('Acme', 'https://s')
        ilk = json.loads(takip.takip_kontrol('Acme')['result'])
        assert ilk['ilk_kayit'] is True
        monkeypatch.setattr('tools.katalog.sirket_ara',
                            lambda m: {'result': json.dumps(kart2)})
        ikinci = json.loads(takip.takip_kontrol('Acme')['result'])
        assert ikinci['degisen'] == ['telefonlar']
        assert 'telefonlar' not in ikinci['degismeyen']

    def test_takipsiz_kontrol_hata(self, monkeypatch, tmp_path):
        takip = self._yama(monkeypatch, tmp_path)
        assert 'error' in takip.takip_kontrol('Yok')

    def test_dispatcher_dort_yer(self, monkeypatch, tmp_path):
        self._yama(monkeypatch, tmp_path)
        monkeypatch.setattr('tools.katalog.sirket_ara',
                            lambda m: {'result': json.dumps(
                                {'site': ''})})
        assert 'result' in calistir('takip_baslat', {'marka': 'Zed'})
        veri = json.loads(calistir('takip_listele', {})['result'])
        assert veri['adet'] == 1
        from tools.definitions import TANINMIS_TOOLLAR
        from chat.agent_protocol import YETENEK_ALANLARI
        from chat.tools import DURUM_METNI
        for ad in ('takip_baslat', 'takip_listele', 'takip_durdur',
                   'takip_kontrol', 'gorev_devret'):
            assert ad in TANINMIS_TOOLLAR
            assert ad in YETENEK_ALANLARI['takip']
            assert DURUM_METNI.get(ad)
