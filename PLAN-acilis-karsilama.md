# PLAN — Karşılama Mesajı Yeniden Düzenleme

Tarih: 2026-08-25
İsteyen: Casper — "böyle karşılamasın beni"

## Sorun

Uygulama açıldığında **iki ayrı mesaj** basılıyor:
1. Eski `zamanlayici.py` kartı: ham veri yığını (hatırlatmalar, görevler, hava, projeler)
2. Yeni `karsila_metni_olustur`: temiz karşılama

Kullanıcı bunların **ikisini de** istemiyor — ya da en azından bu biçimde istemiyor.

## Kaynak Haritası

| Kaynak | Ne basıyor | Tetik |
|--------|-----------|-------|
| `basak_app.py:174` → `karsila_metni_olustur()` | "Merhaba Casper. Bugün..." | boot() her açılışta |
| `tools/zamanlayici.py:113-175` → `ozet_karti_olustur()` | "İyi günler — Salı..." + ham hatırlatma/görev/hava/proje | Arka plan zamanlayıcısı (10:00-20:00) |
| `tools/executor.py:135` → `get_reminders` tool'u | `bugunku_hatirlatmalar` ham çıktısı | Model tool çağrısında |

## Düzenleme Planı

### ADIM 1 — Tek karşılama fonksiyonu (tools/reminders.py)

Mevcut iki fonksiyon (`bugunku_hatirlatmalar` + `karsila_metni_olustur`) **birleştirilecek**.

Yeni fonksiyon: `acilis_karsilama(knowledge_dir, gorevler_file)`

Çıkısı tek, temiz bir karşılama metni olacak. İçeriği:
- Saate göre selam (Günaydın/Merhaba/İyi akşamlar/İyi geceler)
- Bugünün tarihi ve gün adı
- Hatırlatmalar (varsa cümle形式ında, ham satır değil)
- Bekleyen görevler (varsa)
- Kapanış: ne yapabileceği

**Hava durumu ve proje durumu KARŞILAMAYA GİRMEYECEK** — bunlar ayrı tool çıktıları, karşılama ağır kalır.

### ADIM 2 — zamanlayici.py'yi güncelle

`ozet_karti_olustur()` artık kendi selamını/hatırlatmasını/görevini/hava/projesini tek tek yazmak yerine:
- `acilis_karsilama()` çağrılacak
- Hava ve proje durumu **ayrı mesaj** olarak (isteğe bağlı)

### ADIM 3 — boot() güncellemesi

`basak_app.py:boot()` → `acilis_karsilama()` çağıracak. Tek mesaj dönecek.

### ADIM 4 — `bugunku_hatirlatmalar` eski fonksiyonu

- `bugunku_hatirlatmalar()` **silinmeyecek** (geriye uyumluluk için korunur)
- Ama karşılama için **kullanılmayacak** — sadece `get_reminders` tool'u çağırırsa kullanılacak

### ADIM 5 — Test ve doğrulama

Uygulama açılacak, **tek mesaj** görülecek:
- Selam + tarih var mı?
- Hatırlatma cümle formatında mı (ham satır değil)?
- Görev sayısı söyleniyor mu?
- Kapanış cümlesi var mı?
- **İkinci mesaj** (ham veri) çıkıyor mu? → çıkmamalı

## Sınırlar

- `brain/` altına dokunulmayacak
- Mevcut `bugunku_hatirlatmalar` silinmeyecek (geriye uyumluluk)
- Tool sayısı 18'de kalacak
- Hava/proje karşılama dışına çıkacak (ayrı mesaj)
