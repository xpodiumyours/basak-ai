"""tools/takip.py - Firma takibi (P7): eklenti + zamanlayici, yeni servis yok."""

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

_KILIT = threading.Lock()
_ALANLAR = ('unvan', 'adresler', 'telefonlar', 'eposta', 'vergi_no')


def _kok():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _kisi():
    try:
        from chat.kimlik import aktif_kullanici
        return str(aktif_kullanici() or 'casper').strip() or 'casper'
    except Exception:
        return 'casper'


def _yol(kisi=None):
    kisi = str(kisi or _kisi()).strip() or 'casper'
    guvenli = ''.join(c if (c.isalnum() or c in '-_') else '_' for c in kisi)
    guvenli = (guvenli[:40] or 'casper')
    return os.path.join(_kok(), 'data', guvenli, 'takip.json')


def _oku():
    yol = _yol()
    try:
        with open(yol, 'r', encoding='utf-8') as f:
            veri = json.load(f)
        return veri if isinstance(veri, dict) else {}
    except (OSError, ValueError):
        return {}


def _yaz(veri):
    yol = _yol()
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    tmp = yol + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(veri, f, ensure_ascii=False)
    os.replace(tmp, yol)


def _j(veri):
    return json.dumps(veri, ensure_ascii=False)


def takip_baslat(marka, adres=''):
    temiz = ' '.join(str(marka or '').split())
    if not temiz:
        return {'error': 'Marka bos olamaz.'}
    anahtar = temiz.lower()
    with _KILIT:
        veri = _oku()
        if anahtar in veri:
            return {'error': 'Zaten takipte: ' + temiz}
        site = str(adres or '').strip()
        if not site:
            try:
                from tools import katalog
                kart = katalog.sirket_ara(temiz)
                if 'result' in kart:
                    site = str(json.loads(kart['result']).get('site') or '')
            except Exception:
                site = ''
        veri[anahtar] = {'marka': temiz, 'site': site}
        _yaz(veri)
    return {'result': _j({'marka': temiz, 'site': site, 'durum': 'takipte'})}


def takip_listele():
    with _KILIT:
        veri = _oku()
    liste = [{'marka': v.get('marka', ''), 'site': v.get('site', '')}
             for v in veri.values()]
    return {'result': _j({'adet': len(liste), 'takipler': liste})}


def takip_durdur(marka):
    temiz = ' '.join(str(marka or '').split())
    if not temiz:
        return {'error': 'Marka bos olamaz.'}
    with _KILIT:
        veri = _oku()
        if temiz.lower() not in veri:
            return {'error': 'Takipte degil: ' + temiz}
        del veri[temiz.lower()]
        _yaz(veri)
    return {'result': _j({'marka': temiz, 'durum': 'durduruldu'})}


def _kart_alanlar(kart_veri):
    cikti = {}
    for alan in _ALANLAR:
        deger = kart_veri.get(alan, '')
        if isinstance(deger, list):
            cikti[alan] = sorted(str(x) for x in deger)
        else:
            cikti[alan] = str(deger or '')
    return cikti


def takip_kontrol(marka):
    temiz = ' '.join(str(marka or '').split())
    if not temiz:
        return {'error': 'Marka bos olamaz.'}
    with _KILIT:
        veri = _oku()
        kayit = veri.get(temiz.lower())
    if not kayit:
        return {'error': 'Takipte degil: ' + temiz}
    try:
        from tools import katalog
        kart = katalog.sirket_ara(temiz)
    except Exception as e:
        return {'error': 'Kart uretilemedi: ' + str(e)[:120]}
    if 'error' in kart:
        return {'error': kart['error']}
    try:
        yeni = json.loads(kart['result'])
    except (TypeError, ValueError):
        return {'error': 'Kart anlasilmadi.'}
    eski = kayit.get('son_kart') or {}
    yeni_alan = _kart_alanlar(yeni)
    if eski:
        degisen = sorted(k for k in _ALANLAR if eski.get(k) != yeni_alan.get(k))
        degismeyen = sorted(k for k in _ALANLAR if k not in degisen)
        ilk = False
    else:
        degisen = []
        degismeyen = []
        ilk = True
    with _KILIT:
        veri = _oku()
        if temiz.lower() in veri:
            veri[temiz.lower()]['son_kart'] = yeni_alan
            veri[temiz.lower()]['site'] = str(
                yeni.get('site') or kayit.get('site') or '')
            _yaz(veri)
    return {'result': _j({
        'marka': temiz,
        'degisen': degisen,
        'degismeyen': degismeyen,
        'ilk_kayit': ilk,
        'kart': yeni,
    })}
