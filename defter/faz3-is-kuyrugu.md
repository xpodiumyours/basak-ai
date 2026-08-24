---
kim:    opencode
tarih:  2026-08-24
konu:   Faz 3 — kalıcı iş kuyruğu (görev kaybı=0 altyapısı)
tip:    karar
omur:   sonsuz
kaynak: tools/is_kuyrugu.py + tests/test_is_kuyrugu.py + CANLI-KAPISI.md
---

Uzun görevlerin çökmeden hayatta kalması için kalıcı kuyruk kuruldu.

TASARIM SAPMASI (bilinçli): plan taslağındaki pending/running/completed/
failed DOSYALARI yerine TEK data/jobs/kuyruk.json + atomik tmp+rename.
Gerekçe: çökme iki dosya arasında yakalanırsa görev ikiye bölünür/kaybolur;
tek dosyada durum daima tutarlı. Planın `durum` alanı job içinde aynen.

SÖZLEŞME: adımlar isimdir (kalıcılık), fonksiyon koşucuya verilir.
Her adım ÖNCE calisiyor+calisan_adim, SONRA mevcut_adim+1 yazılır →
onaylanmış adım asla tekrar koşmaz; yarım adım maksimum_deneme'ye kadar
denenir; bütçe (maksimum_gorev_suresi / sure_butcesi) dolunca BEKLIYOR'a
dönüp sonraki çağrıda kaldığı yerden sürer. onay_gerekli işler
onayla(id)'ye dek atlanır.

BULGU-DÜZELTME: ilk testte deneme sayacı iş-genesine kaçmıştı (ilk
adımın denemesi ikinci adımı limit'e yaklaştırıyordu) — sayaç adım
ilerleyişinde sıfırlanacak şekilde düzeltildi; regresyon testi var.

KANIT: 12 yeni sözleşme testi (mutlu yol, retry, kalıcı hata, YENİDEN
DOĞUM ile a-asla-tekrar, yarım-adım resume, bütçe bekletme, onay kapısı,
eksik fonksiyon, JSON geçerliliği, .tmp artığı yok, 80 paralel eklemede
id benzersizliği). 528/528 yesil.

ENTEGRASYON: zamanlayıcı/sunum bağlantısı ayrı dilim (Faz 3b); OS-level
restart provası sonda fazında (Faz 4).
