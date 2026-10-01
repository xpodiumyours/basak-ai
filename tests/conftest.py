"""tests/conftest.py — test kosusu teshis dosyasina (hata.log) yazmaz.

Denetim bulgusu (2026-10-01): hata.log 36.016 satira cikmisti ve agirligi
TEST gurultusuydu — sayim: ~15.500 satir "Optional ajan stream acilamadi:
testte stream yok" + ~13.500 satir httpx2 "HTTP Request" kaydi.

Kaynak: test dosyalarindan biri basak_app'i import ettiginde (toplama
asamasinda bile) basak_app.py'deki basicConfig(force=True)
RotatingFileHandler'i KURUYOR; sonrasi tum test kayitlari teshis
dosyasina dusuyordu ve gercek kok sebep gomuluyordu.

Cozum: conftest toplanmadan once yuklenir; buradaki bayrak basak_app'e
test ortaminda oldugunu soyler, basak_app dosya handler'i kurmaz.
Konsol kaydi aynen kalir, uretimde (python basak_app.py) bayrak yoktur.
"""

import os

os.environ["BASAK_TEST_KOSUSU"] = "1"
