# Başak ajan platformu: resmî kaynaklarla uyumluluk denetimi
27 Ekim 2026 · mevcut 10 aşamanın kabul kontrolü; yeni kapsam değildir.

## Kaynaklar ve doğrudan etkileri

- **Kimi Code, Agents and Sub-Agents:** https://www.kimi.com/code/docs/en/kimi-code-cli/customization/agents.html
  - Ana ajan ile alt ajanlar arasında tool allowlist ve delegasyon kontrolü ayrı yetkilerdir.
  - Başak: `allowed_tools` devralınır ve genişletilemez; yalnız ana ajan delegasyon yapar;
    kullanıcı onayı gerçek dış yazmalarda ayrıca zorunlu tutulur.
- **Qwen Code, Subagents:** https://qwenlm.github.io/qwen-code-docs/en/users/features/sub-agents/
  - Alt ajanlar bağımsız görev bağlamları ve araç erişim kuralları kullanır, görev akışı gözlenebilir.
  - Başak: bağımsız görev defteri/olay dizisi, child-progress ekranı,
    üst göreve sonuç aktarımı ve bekleme durumunu açık gösterim.
- **DeepSeek, Thinking Mode ve Tool Calls:** https://api-docs.deepseek.com/guides/thinking_mode/
  https://api-docs.deepseek.com/guides/tool_calls/
  - Tool kullanan çok adımlı thinking taleplerinde `reasoning_content` sonraki
    çağrılara tam taşınmazsa API 400 döndürebilir. Araç sonuçları gerçek tool ID
    üzerinden bağlanmalıdır.
  - Başak: mevcut model havuzuna özel adaptör eklemeden önce bu alanların
    mevcut normalizasyon ve devam kayıtlarında korunması ayrıca sınanmalı.
- **Xiaomi MiMo, API Integration ve Responses:** https://mimo.mi.com/docs/en-US/quick-start/faq/api-integration
  https://mimo.mi.com/docs/en-US/api/chat/responses
  - Çok adımlı tool+thinking akışında reasoning içeriğinin korunması önemlidir.
    Responses uyumluluğu tam değildir; örneğin `background` ve
    `previous_response_id` desteklenmez.
  - Başak: resmî API ile canlı model kabulü olmadan yalnız API benzerliğine
    dayanıp destek veya sıfır maliyet iddia edilmemeli.

## Eklenen somut korumalar
- Tek ana görev altında en çok **8 alt görev**, aynı anda en çok **3 aktif alt ajan**.
  Her iki sınır veritabanı transaction'ında doğrulanır; dördüncü iş kaybolmaz, kuyrukta kalır.
  Ayarlar RuntimeStore constructor'ında kontrol edilir; geçersiz değerler reddedilir.
- Alt ajanlar tekrar delegasyon yapamaz; ana ajan yönetir. Delegasyon aracı modelden de gizlenir.
- Görevlerin idempotency anahtarı yeniden oynatılan çağrıda önce kontrol edilir.
- UI gerçek görev kayıtlarından durum/ilerleme/kanıt gösterir; eksik kanıtı başarı göstermez.

## Canlıya çıkmadan açık kabul kapıları
1. DeepSeek/MiMo thinking araç döngüsünün **mevcut model havuzunda** reasoning_content
   ile roundtrip davranışını kotasız fixture + yetkili canlı sağlayıcı testiyle doğrulamak.
2. 3/8 paralel sınırlara PostgreSQL çok işçi yük testi uygulamak.
3. OAuth bağlantılarını ayrı test kullanıcılarıyla ve onaylı yazma senaryolarıyla doğrulamak.
4. Sürekli çalışan uzak işçi ve sandbox altyapısını gerçek ortamda kurup ölçmek.
5. Araştırma, kod/GitHub, tarayıcı/belge olmak üzere 3 uçtan uca kabulü geçirmek.

Kapsam koruması: Brain, FreeLLMAPI, mevcut sohbet davranışı ve AGENTS.md değiştirilmedi.

## 27 Ekim — thinking + onay kesintisi düzeltmesi
DeepSeek resmî belgesi, `tools` içeren sonraki isteklerde önceki
`reasoning_content` içeriğinin aktarılmasını zorunlu görüyor; eksikliği
HTTP 400 ile sonuçlanabiliyor. Xiaomi MiMo da çok-adımlı thinking/tool
akışında bu alanın korunmasını öneriyor.

Başak'ın ortak model geçmişi bunu zaten yapıyordu. Yalnız kalıcı görev
kuyruğunda, ilk modelin **henüz çalıştırılmamış** araç çağrısı onaya
takıldığında kontrol noktası yalnız çağrı kimliğini saklıyordu, assistant
`reasoning_content` ve `content` bilgileri kayboluyordu. Yeni
`pending_reply` kontrol noktası, kaldığı yerden devamda aynı yanıtı
modelin son araç çağrısıyla eşleştirerek geri verir. Simüle edilmiş gerçek
SQLite kayıtları ve iki ayrı işçiyle, DeepSeek/MiMo için ağ kullanmadan
test edilir. Resmî canlı sağlayıcı doğrulaması yine ayrı kabul koşuludur.

## P0 tarayıcı dış yazma izinleri (27 Ekim)
Önceki sürümde `bulut_tarayici` işlemlerindeki dış etki olasılığı
görev defterinde işaretleniyordu, **ancak `before_action` kullanıcı
onayını yalnız `baglanti_cagir` için istiyordu**.
Artık tarayıcıdaki `tikla`, `yaz`, `tus`, `yukle`, `indir`
ve bilinmeyen işlemler için modelin yetkisi yeterli değildir:
belirli oturum, işlem ve argüman özetine bağlı tek kullanımlık onay
gereklidir. Onay olmadan dış eylem başlamaz. Normal sayfa açma
(GET), okuma, ekran görüntüsü, DOM doğrulaması ve kaydırma onay
beklemez. Tüm dış sitelerin GET davranışını garanti etmek mümkün
olmadığı için bu istisna üretim güvenlik değerlendirmesine dahildir.
