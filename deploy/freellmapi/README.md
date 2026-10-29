# Basak — tek FreeLLMAPI baglantisi

## Teslimin durumu

Bu dizin kurulum icindir; canli kurulumun yapildigi anlamina gelmez.
Vercel ortam degiskenlerine yetkili erisim ve kalici diskin oldugu bir
FreeLLMAPI sunucusu olmadan anahtar aktarimi ve canli kabul tamamlanamaz.
Kullanicinin bilgisayarina kurulum gerekmez. Bulut sunucusu mevcut
Vercel Functions ortamina eklenmis veya baska bir hesapta acilmis degildir.

## 1. Mevcut anahtarlari tek seferde toplama

Yetkili sunucu is ortami mevcut saglayici ortam degiskenlerini tasimalidir.
Alternatif olarak mevcut `ayarlar.json` dosyasi `--ayarlar` ile verilir.
`--kontrol` anahtar yazmaz veya ag istegi gondermez:

```bash
python -m scripts.freellmapi_kurulum --kontrol
```

Panel icin `FREELLMAPI_ADMIN_EMAIL` ve `FREELLMAPI_ADMIN_PASSWORD`
guvenli sunucu ortamindan saglandiktan sonra:

```bash
python -m scripts.freellmapi_kurulum
```

Bu, `.env.freellmapi-config.json` dosyasini yalniz sahibine okuma/yazma
izniyle olusturur; var olan dosyayi ezmez. Groq, Google, Zhipu, Cohere,
NVIDIA, Kilo, OpenRouter, Mistral ve Cloudflare biletleri tek yapilandirmaya
aktarilir. Bos biletler atlanir; yeni saglayici hesabi veya kota uretilmez.
Cloudflare icin `account_id:token` resmi FreeLLMAPI bicimi kullanilir.
Dosya ve ciktilar tarayiciya, kaynak koduna veya Git'e eklenmez.
Vercel'in geri okunamayan Secret degerlerini `env pull` ile elde etmek
mumkun degildir; bu adim icin yetkili kaynak ortam gerekir.

## 2. Gateway'i kalici bulut sunucusunda baslatma

`BASAK_FREELLMAPI_CONFIG` toplu JSON dosyasinin mutlak yolu;
`ENCRYPTION_KEY` 32 rastgele baytin 64 haneli hex karsiligidir.
Sunucunun gizli degisken yonetiminde saklanir ve yeniden baslatmalarda
korunur. Bu degiskenler ayarlandiktan sonra bulut sunucusunda:

```bash
docker compose -f deploy/freellmapi/compose.yaml up -d
```

Compose kalici SQLite volume'u olusturur; gateway yalniz loopback'e
acilir. Vercel'den erisim icin guvenilen HTTPS erisim katmani gereklidir.
FreeLLMAPI kaynak projesi kendi proxy'sini halka acik, cok kullanicili
bir servis olarak yayinlamayi onermiyor; panel ve proxy ozel tutulmalidir.
`latest` upstream'in resmi imajidir; kontrollu yayin icin test edilen
imaj digest'i bulut operatoru tarafindan sabitlenmelidir.

Resmi belgeler:
- https://github.com/tashfeenahmed/freellmapi/blob/main/docs/en/install/01-install.md
- https://vercel.com/kb/guide/is-sqlite-supported-in-vercel

## 3. Basak'i tek baglantiya gecirme

Kendi gateway panelinin Keys bolumunden olusan ortak anahtar alinir.
Ilk olarak gelistirme dalina ozel Vercel Preview ortaminda uc degisken
tanimlanir:

| Degisken | Deger |
|---|---|
| `FREELLMAPI_URL` | Kendi gateway'inin guvenilen HTTPS adresi |
| `FREELLMAPI_API_KEY` | Kendi panelinden uretilen ortak anahtar (Secret) |
| `FREELLMAPI_MODEL` | `auto` veya gateway'de dogrulanan ucretsiz zincir/model |

Adres ve anahtar verildiginde Basak'in sohbet zinciri yalniz FreeLLMAPI
uzerinden calisir. Normal yanit, native arac cagrisi ve final metin akisi
ayni baglantiyi kullanir. Model secimi ve saglayici yedeklemesi gateway'de
yapilir. Ayar var ama baglanti kurulamamissa Basak saglayicilara sessizce
dogrudan cikmaz; hata verir. Ayarlar hic yoksa eski kurulum devam eder.
Goruntu okuma gibi ayri ozelliklerin dogrudan entegrasyonlari bu sohbet
degisikligiyle tasinmaz; onlarin anahtarlarini kaldirmayin.

## 4. Canli kabul

Panelde mevcut biletlerin saglik sonucunu, ucretsiz model listesini ve
istenen model kimliklerinin gercekten bu hesaplarda kullanilabildigini
kontrol edin. `auto` veya ozel profile ucretli custom modeller eklemeyin.
Videodaki isimlerin aynisini yazmak, o varyantin halen ucretsiz ve erisilebilir
oldugunu kanitlamaz. Ucretli modelle sessiz ikame yapilmaz.

Preview'da gercek sohbet, native arac cagrisi -> arac sonucu -> final
yanit ve streaming olculmeden production'a gecilmez. Bu kabul bu
calisma ortaminda henuz yapilamadi. Ana dal merge/yayin onayi ayridir.

Geri alma: yeni deployment'ta uc `FREELLMAPI_*` ayarini kaldirip onceki
dogrudan baglantilari kullanin; veritabani volume'unu ve sifreleme
anahtarini silmeyin. Onayli onceki Vercel deployment'ina donus de mumkundur.
