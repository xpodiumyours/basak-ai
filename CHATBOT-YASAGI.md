# CHATBOT YASAĞI — Kalıcı Söz

**Casper'in kararı (2026-09-13):** Başak'ı chatbot'a çevirecek veya
benzetecek HER kural, HER katman, bundan sonraki BÜTÜN çalışmalarda
yasaktır. Bu yasak "iyi niyetli" gerekçelerle de delinemez:
güvenlik, kota, hız, "küçük model şaşırmasın" — hiçbiri geçerli değildir.

## Neden var?

Eskiden "model seçsin" deniyor ama arkada kod onun seçimini bozuyordu.
En kötüsü: araç sunulan her çağrı, adı bile konmamış bir tablo yüzünden
daha seçicide patlıyordu (`NameError`). Model alet kullanamayınca geriye
boş konuşan bir chatbot kalıyordu. On günün özeti bu.

## Yasak olan (sade dille)

1. **Kelimeye bakıp karar veren kod:** "şu kelime geçerse şunu aç" türü
   her şey. Model ne kullanacağını şemaya bakıp kendisi seçer.
2. **Cevaba dokunan kod:** cevabı kısaltma, ek satır yapıştırma,
   düşünceyi/ifadeyi silme, toparlama dayatma.
3. **Tavanlar:** tur sınırı, son turda alet kapatma, sonucu kırpma,
   geçmişi budama, modeli boğan küçük limitler, düşünmeyi kapatma.
4. **Seçimi ele geçiren katmanlar:** onay kuyruğu, izin tablosu, yetki
   tavanı, karne/shuffle ile sıralama oyunu, orkestra/jüri/gölge,
   elle kapatma bayrakları, sahte yönlendirme mesajları.
5. **Küçük/büyük model ayrımı:** modele adına bakıp farklı davranmak.
6. **Sormadan konuşma:** kullanıcı sormadan mesaj yok — açılışta da
   kapanışta da durduk yere konuşulmaz. Başak çağrılınca gelir.

## Serbest olan (dokunulmaz)

Yol kara listesi (şifre/sistem dosyaları), internet saldırısı savunması
(SSRF), beyaz liste dışı aletin çalışmaması, sabit komut tabloları.
Bunlar modeli daraltmaz, bilgisayarı korur.

## Denetim

Bekçi: `tests/test_chatbot_yasagi.py`. Her kod değişikliğinde
`python -m pytest tests -q` koşar; yasak geri gelirse paket kırmızı olur.
Bekçi hem davranışı ölçer hem yasaklı isimleri tarar; eski yasaklı kodla
yakaladığı ispatlıdır.

## Değişiklik kuralı

Bu dosya ve bekçi testi, Casper açıkça "değiştir" demeden
değiştirilemez, gevşetilemez, taşınamaz. Gevşetme teklifi bile bu
dosyaya gerekçesiyle yazılır, sessizce yapılmaz.
