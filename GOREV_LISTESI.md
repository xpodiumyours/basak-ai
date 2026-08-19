# Başak — Görev Listesi (Sonraki Özellikler)

19 Ağustos 2026. Casper'ın onayladığı yön: 5 madde, öncelik sırası kilitli değil — hangisini isterse o açılır. Her madde kendi commit'i olacak kadar küçük parçalara bölünür (`AGENTS.md` §5/6 — kanıtsız "bitti" yok, dosyayı yeniden yazma değil düzenle).

## 1. Gerçek hafıza sistemi

**Sorun:** Şu an `knowledge/` altındaki her `.md` dosyası her sohbette ham/tam okunuyor (`_knowledge_context`, `basak_app.py`). Dosya sayısı arttıkça bağlamı tıkar, düzensizleşir.

**Hedef:** Claude Code'un kendi hafıza sistemine benzer yapı:
- Her gerçek/not **tek dosya**, kısa frontmatter (isim, konu, tarih).
- Bir **index dosyası** (`knowledge/INDEX.md`) tüm notların tek satırlık özetini tutar — Başak önce index'i okur, gerekiyorsa ilgili dosyayı açar (tüm dosyaları şişirmeden).
- Başak, konuşma sırasında öğrendiği kalıcı bir bilgiyi (örn. "Casper'ın doğum günü X") **kendisi yeni not olarak kaydedebilsin.** Bunun için Api'ye bir `not_kaydet(baslik, icerik)` fonksiyonu eklenmeli — madde 2'deki araç-çağırma altyapısını paylaşır.

## 2. Bilgisayarda iş yapma (araç kullanımı)

**Casper'ın onayladığı kapsam:** (a) belirlenmiş klasörlerde dosya okuma/yazma (`knowledge/` ve benzeri, sistemin geneli değil), (b) **izin verilen belirli uygulamaları açma** (tarayıcı, not defteri vb. — beyaz liste).

**Kesinlikle yok:** sınırsız komut çalıştırma, sistem dosyalarına erişim, onaysız silme.

**Uygulama notu:** Ollama/qwen2.5'in tool-calling (function calling) desteğini doğrula. Desteklemiyorsa basit anahtar-kelime kalıbıyla başla ("not ekle: ...", "chrome aç" gibi), ileride gerçek tool-calling'e geçilir. Her araç çağrısı loglanır (`hata.log` gibi ayrı bir `arac.log`); beyaz listeye yeni klasör/uygulama eklemek **Casper onayı gerektirir** — bkz. madde 5.

## 3. Güncel bilgi / web arama

Yerel model ve Groq'un ikisi de belli bir tarihte donmuş bilgiyle çalışıyor. `research-engine/` klasörü (ayrı git deposu, co_scientist) zaten var ama Başak'a bağlı değil — önce ne olduğu değerlendirilmeli (`research-engine/README.zh.md` var, Çince — kontrol gerek). Gerekirse daha hafif, ücretsiz bir arama entegrasyonuna gidilir. Ağır bağımlılık eklenmesin.

## 4. Basit görev/hatırlatma takibi

Başak, Casper'ın söylediği görevleri ("yarın X'i hatırlat") basit bir `gorevler.json`'da tutsun, uygun anda (açılışta veya sorulduğunda) hatırlatsın. Karmaşık takvim entegrasyonu değil, basit liste.

## 5. AGENTS.md'ye yeni güven sınırı

Madde 2 hayata geçtiğinde `AGENTS.md`'nin ilgili bölümüne eklenecek: yeni bir izinli klasör/uygulama eklemek ya da mevcut aracın kapsamını genişletmek **Casper onayı gerektirir** — ödeme/auth gibi hassas alanlarla aynı muamele.

---

**Not:** Bu liste kilitli bir plan değil, sıradaki adayların dökümü. Hangi madde açılırsa `AGENTS.md`'ye "şu an neredeyiz" olarak işlenir.
