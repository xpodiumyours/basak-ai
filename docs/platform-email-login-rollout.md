# Başak — Neon e-posta girişi yayın sözleşmesi

Bu değişiklik **varsayılan kapalıdır**. GitHub CI başarılı veya Vercel READY
olması gerçek hesap girişi kabulü değildir.

## Mimari
- Neon Auth yönetilen Better Auth: parola doğrulama ve e-posta doğrulama.
- Başak: doğrulanmış Neon `user.id` değerini `basak_account` tablosunda
  `provider=neon` ile tanımlar. Mevcut imzalı, iptal edilebilir
  `basak_platform_session` HttpOnly/Secure/SameSite=Lax çerezini kullanır.
- Neon'dan gelen geçici giriş oturumu aynı sunucu isteğinde kapatılır.
  Neon oturum çerezi veya parolası Başak veritabanına/browser yanıtına yazılmaz.
- Her provider yalnız explicit HTTPS `*.neonauth.*.neon.tech/<database>/auth`
  tabanı ile çağrılır; HTTP redirect, dinamik hedef veya kullanıcı URL'si yoktur.
- E-posta **doğrulanmış değilse hesap oturumu oluşturulmaz**.
- Üretimde kullanıcı kaydı açma/şifre sıfırlama arayüzü bu sürümün
  kapsamı dışındadır. Yönetilen Neon Auth'da kayıt, doğrulama ve
  kurtarma politikaları doğrulanmadan genel kullanıcıya açılmayacak.

## İzole Preview hazırlığı
1. `preview-izole` Neon branch içinde `neon_auth` ve mevcut
   `basak_account`, `basak_account_session` tablolarını doğrula.
2. Vercel Preview web ve worker için aynı **izole** Postgres DSN hedefini
   doğrula; Production'ın Postgres endpoint'iyle aynı olamaz.
3. Preview branch kapsamlı, güçlü ve **yeni** iki ayrı gizli değer ayarla:
   `BASAK_OTURUM_ANAHTARI` (en az 32 byte),
   `BASAK_CONNECTION_KEY` (32 rastgele byte, URL-safe Base64).
   Bunları chat, GitHub veya terminal çıktısında paylaşma.
4. `BASAK_PUBLIC_URL` Preview'ın **sabit HTTPS** giriş origin'i olmalı;
   değişen deployment URL'sini kalıcı origin sanma.
5. Preview branch özelinde `BASAK_PREVIEW_NEON_AUTH_BASE_URL`:
   Neon Auth'ın **Preview** branch'ine ait /neondb/auth URL'si.
   Production Auth URL'sini kullanma.
6. Neon Auth'da e-posta doğrulamasını ve kullanıcı kaydı politikalarını
   güvenli hale getir. Varsayılan yapılandırmada doğrulama kapalıysa
   gerçek e-posta girişi kabulü yapma.
7. Son olarak yalnız Preview dalında `BASAK_NEON_EMAIL_ENABLED=true`
   ayarla ve yeniden deploy et. Production flag kapalı kalmalı.

## Kabul: gerçek kullanıcı ve gerçek yönetilen servis
- Gerçek doğrulanmış Preview hesabı ile giriş yap:
  `GET /api/hesap` -> `authenticated: true`.
- Sayfayı kapat/aç: oturum aynı kişiye ait kalmalı.
- Kullanıcı A ve kullanıcı B veri erişimi ayrılmalı.
- Yanlış parola, doğrulanmamış e-posta, 403 yabancı Origin, eksik
  anahtar, eksik/yanlış DB, Neon 500/timeout hepsinde fail-closed.
- `POST /api/hesap/cikis` sonrasında aynı çerez tekrar geçerli olmamalı.
- Anonim sohbet/FreeLLMAPI korunmalı.
- Provider tarafındaki geçici oturumun her giriş denemesinde kapandığı
  kayıtlardan doğrulanmalı.
- PostgreSQL tabloları izole Preview'da artmalı; Production'a veri
  yazılmamalı.
- Asıl kullanıcı kabulü tamamlanmadan Production'da
  `BASAK_NEON_EMAIL_ENABLED=true` yapılmamalı.

## Production
Ayrı Production Auth URL'si `BASAK_PRODUCTION_NEON_AUTH_BASE_URL`,
Production session/encryption keys, Production PostgreSQL şeması,
uygun e-posta doğrulaması ve gerçek geri alma planı doğrulanır.
Önce Preview kabul kanıtı, sonra Production için yeni kullanıcı onayı.
Bu kod/geliştirme dalı otomatik olarak production ayarlarını değiştirmez.
