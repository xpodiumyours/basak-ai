# ARAŞTIRMA — İŞ DOSYASI (görev hafızası)

Tarih: 2026-09-12
Durum: KANITLANDI — KOD DENEYİNE İZİN
Risk sınıfı: Orta (yeni dosya + yeni araç + akış yüklemesi; hepsi kapılı)

## 1. Hedef

Uzun işlerde "baştan anlatma" devrini kapatmak: açık komutla açılan her işe
`data/isler/<id>.md` dosyası (HEDEF/PLAN/BULGULAR/SONRAKI/KARARLAR); aktif iş
her turda bütçeli okunur; bulgular kodla, plan modelle (denetimli) yazılır;
tur tavanı yalnız işli turda esner. Kullanıcı onayı: açık-komutla-açılış +
iş-dosyası-önce sırası (2026-09-12).

## 2. Kabul kriteri

- Komutsuz turda dosya açılmaz ve prompta iş bloğu girmez (test pinler).
- Yeni oturumda "nerede kalmıştık" SONRAKI'den devam eder (akış testi).
- İşsiz tur prompt boyu değişmez; işli turda iş bloğu ≤1500 harf.
- Atomik yazım; kilitlenme/yarım yazma yok.
- `pytest tests -q` yeşil; dışa gönderme bu pakette YOK.

## 3. Mevcut durum kanıtı

- `tools/is_kuyrugu.py`: atomik `tmp+rename` + resume + bütçe deseni mevcut
  (`_yaz:121`, `kos_bekleyenleri:188`); AMA adım kitaplığı 3 bakım işiyle
  sabit, kullanıcı ısmarlaması giremez (`is_ac:326` bilinmeyeni reddeder).
- `chat/oturum.py`: oturum dosyaları + `aktif_id` deseni mevcut; model
  bağlamına İŞ DURUMU girmez (yalnız mesajlar).
- `chat/tools.py:230-250`: `tur_siniri` parametreli, `tavan=3 if kap.kucuk`.
- `chat/flow.py:196`: geçmiş penceresi 4000 — uzun iş ortada kopar (gerekçe).
- Onay sistemi (`chat/approval.py`) dışa-dokunan araçlarda çalışır — aynen kalır.

## 4. Sorun kanıtı

İş hedefi/planı/bulgusu birinci-sınıf nesne değildir; episodik anılar
görev-sürekliliğini taşımaz (karışık, sırasız, bütçesiz). Uzun iş = tekrar
anlatma. Kullanıcı beyanı + FAZ0 bağlam-duvarı ölçümü.

## 5. Dış referans

- Kimi resmi ajan deseni: `MAX_TOOL_ROUNDS=8`, tur geçmişi eksiksiz taşınır,
  `finish_reason=length` hatadır (platform.kimi.ai ajan kılavuzu).
- OpenAI ajan kılavuzu: sorgu tamamen çözülmeden durma; TODO ile izle.
- Letta: pinned küçük blok + retrieved detay ayrımı (iş bloğu ≈ pinned özet).

## 6. Doğrulanan gerçekler

- Atomik yazım, aktif-id dosyası, tur parametresi desenleri kodda okundu.
- `is_notu` YENİ araçtır (şema: `is_id`, enum bölüm, ≤500 harf metin);
  definitions+executor+permissions üçlüsüne girer.

## 7. DOĞRULANAMADI

- Model-planı kalitesi (FAZ2 bataryası ölçecek; bozuk plan dosyaya girer
  ama kod denetimini (bölüm+uzunluk) geçer — içerik garantisi yok).

## 8. İzin verilen kapsam

- YENİ `tools/isdosya.py` (defter CRUD + bütçeli okuma + aktif takibi).
- `tools/definitions.py` + `executor.py` + `permissions.py`: `is_notu` girişi.
- `chat/flow.py`: aktif iş yükleme (bütçeli) + `uzun_is` bayrağı.
- `chat/tools.py`: `uzun_is` parametresi, tavan 8 (varsayılan yol aynı).
- `.gitignore`: `data/isler/` (kontrol edilecek).
- YENİ `tests/test_isdosya.py`.

## 9. Yasak kapsam

- `is_kuyrugu`, onay sistemi, tool şemaları (is_notu hariç), promptlar,
  KISILIK, secici, karne, streaming kararı, kişisel kapı — dokunulmaz.
- Dışa mesaj gönderme, browser, Vixrex akışı — YOK.
- Otomatik iş-sezme — YOK (yalnız açık komut).

## 10. Korunacak davranışlar

- İşsiz tur: prompt, tur tavanı, araç seti birebir aynı (test pinler).
- Kuyruk/zamanlayıcı/onay aynen çalışır.

## 11. Risk sınıfı

Orta.

## 12. Kabul sensörleri

Yeni birim+akış testleri + `pytest tests -q` + `py_compile` + canlı devam
provası (kota korumalı, 1 tur).

## 13. Geri alma koşulu

Komutsuz dosya açılırsa, işsiz tur değişirse veya test kızarırsa paket
(tek commit) geri alınır.

## 14. Sonuç (2026-09-12 uygulandı)

- YENİ `tools/isdosya.py` (defter + `tur_girisi` + `is_notu`) + `tests/test_isdosya.py`
  10/10 + `tests/test_is_giris.py` 13/13.
- Bağlantılar: definitions + executor + permissions + TANINMIS/LABEL/detay +
  EXTENDED tetikleyici; akış iki yola da (`system_prompt` eki orkestraya,
  system mesajı düz yola); `is_notu` yalnız uzun turda sette; tur tavanı
  `uzun_is` ile 8 (orkestra-deney dahil), varsayılan birebir aynı.
- Yan düzeltme: `test_tools_listesi_dogru` envanteri 21→22 (`is_notu`
  dahil; etiketsiz-araç kuralı korunur).
- Tam paket 616 geçti / 0 hata. `.gitignore`: `data/isler/`.
- KANITLANDI → paket tamamlandı (commit bekliyor).
