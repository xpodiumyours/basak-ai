# BAŞAK | MÜHENDİSLİK MASTER PLANI

**Sürüm:** 1.0 | **Kaynak denetimi:** 2026-10-29 | **Durum:** plan ve teslim takibi başladı; üretim değişmedi.
**Yetki sınırı:** Bu belge bir üretim dağıtım onayı değildir. AGENTS.md kilitlidir; değiştirilmez.
**Kayıtlar:** [Teslim defteri](./BASAK-TESLIM-DEFTERI.md) · [Resmî kaynak sicili](./BASAK-RESMI-KAYNAK-SICILI.md).
**Önceki planlarla ilişki:** docs/MVP-PROFESYONEL-PLANI.md, docs/ORACLE-TASINMA-PLANI.md ve CANLI-KAPISI.md tarihi karar/teknik bilgi taşır. Buradaki ölçülmüş durumlar eski tahminleri geçersiz kılar. Ticari ve güvenlik kısıtları ile AGENTS.md kuralları saklıdır.

## 1. Ürün hedefi

Başak; düşük gecikmeli, modelin araç seçtiği, ücretsiz kaynakları ölçülebilir biçimde yöneten bir Türkçe yapay zekâ asistanı olacak. Kullanıcı isteği sürerken veya bağlantı koptuğunda uzun işlemler ve alt ajanlar için durum kalıcı olmalı; işlem kaybı, çift dış eylem, sahte tamamlandı iddiası olmamalı. Temel ücretsiz ürün kanıtlandıktan sonra, yetkili kullanıcı için ücretli modellerin kontrollü ve hesaplanabilir kullanımını ekleyeceğiz.

**Mimari ilkesi:** Kod veya teknoloji korunmak zorunda değildir; kullanıcı verileri, tamamlanmış eylemlerin idempotansı, güvenlik ve hizmet sürekliliği korunmak zorundadır. Daha iyi kanıtlanırsa FastAPI, PostgreSQL, worker veya ajan çekirdeği yeniden yazılabilir. Geçiş veri taşıma, karşılaştırmalı ölçüm, geri dönüş ve açık onay gerektirir. Yeni mimarinin seçimi gösterim değil kabul testleriyle yapılır.

## 2. 2026-10-29 doğrulanmış taban

| Başlık | Kanıt | Hüküm |
|---|---|---|
| Üretim sürümü | Vercel basak-vercel production SHA a167e6d47599738cac5461540294c057a863492e (main, READY) | Bugün canlı |
| Hazır sohbet düzeltmesi | fix/foreground-chat-durable-agents-20261029 SHA 3d531d50f3e25a503bf0680321c2c70ef2554435 | Preview READY; henüz production değil |
| CI | GitHub Actions kapi, agent-platform-kabul, testler: success (3d531d5) | Otomatik testler geçti, gerçek kullanıcı testi yerine geçmez |
| HTTP sohbet yolu | chat/platform_api.py üretimde ayrı worker olaylarını gözlüyor | İşçi bekleme ve kalıcı olay okuma yolu bulunuyor |
| Geliştirme yolu | Foreground chat doğrudan o run_id için Worker.tick çağırıyor | Kuyruk bekleme bağımlılığını azaltmayı hedefliyor; serverless ömrü riski ayrıca ölçülecek |
| Model katmanı | brain/brain.py + brain/registry.py + chat/flow.py | Çoklu sağlayıcı, fallback, modelin tool seçimi mevcut |
| Kalıcı görev | chat/platform_runtime.py + chat/platform_agents.py + worker/platform.py | Lease, claim, checkpoint, event ve idempotans mevcut; kesinti kabulü eksik |
| Kullanıcı deneyimi | basak-vercel.vercel.app ve yardımcı sayfalar GET ile açıldı | İstekten ilk gerçek token'a süre ölçülmedi |
| Telemetri erişimi | Vercel runtime errors/logs 403 | 35 saniyelik gecikmenin sebebi kanıtlanmış değil |
| Ticari sınır | Vercel ekip planı Hobby; yasal sayfalar TASLAK | Ticari yayın öncesi resmî şart ve hukuk kapısı gerekir |

**Doğrulama farkı:** Unit/integration PASS, gerçek hesabın canlından uçtan uca sohbet PASS anlamına gelmez. Açık veri boşluğu açık yazılacaktır.

## 3. Önce / sonra iş paketleri

| ID | Bugünkü durum (önce) | Yapılacak mühendislik işi (nasıl) | Teslim çıktısı (sonra) | Kanıt / kabul kapısı |
|---|---|---|---|---|
| P0 Ölçüm | 35 sn şikâyet var, segment bazlı canlı süre yok | Aynı run_id ile giriş, DB create, dispatch, sağlayıcı başlangıç, ilk model token, son token, araç ve tamamlanma zamanlarını ölç; kişisel mesajı loglama | P50/P95 TTFT ve toplam gecikme, hata oranı, sürüm/provider dağılımı | Gerçek kullanıcı oturumunda ölçülen ve tarihlenen rapor; karşılaştırılabilir fixture |
| P1 Sohbet | Üretim sohbeti kalıcı worker observer yoluna bağlanabiliyor; preview doğrudan başlatıyor | 3d531d5 preview için idempotans, auth, NDJSON akış, bağlantı kopması ve serverless termination prova; gerekiyorsa yürütmeyi yeniden tasarla | Hızlı görünen ilk gerçek model cevabı, doğru kalıcı sohbet | Onaylı e2e; negatif test; önce/sonra P50/P95; rollback |
| P2 Uzun görev | PostgreSQL run/lease/checkpoint var; sürekli yürütme garantisi kanıtlı değil | Ayrı ömürlü yürütücü alternatifleri: mevcut Oracle systemd worker, Vercel Daemons (beta), Python workflow (beta); maliyet, limit ve kurtarma testi | HTTP'den bağımsız, yeniden başlatmada sürdürülebilen görev | İşçi öldür, kirayı düşür, yeniden başlat, tam bir kez dış eylem ve teslim kanıtı |
| P3 Alt ajan | Parent/child, dependency ve acceptance akışları var | Model kararlı plan/devir; alt ajan çalışma alanı izolasyonu; bağımsız paralel işler; gerçek artefakt ve kabul doğrulama | Çok adımlı iş alt ajanlarca tamamlanır | En az 3 farklı senaryo: paralel, kısmi hata, onay bekleme; iz ve artefakt |
| P4 Sağlayıcı yönetimi | Ücretsiz sağlayıcı fallback + cooldown mevcut; kullanıcı deneyimi ve maliyet verisi eksik | Yeteneği resmî protokole göre test et, gerçek gecikme ve kota ile seç; provider hatalarını ölç; manuel tercih koru | Ücretsiz modda belgelenmiş ve sıfır sürpriz maliyetli havuz | Her model için tool/stream/timeout/kota/kullanım koşulu matrisi; gerçek test |
| P5 Ürün ve güven | Mobil/masaüstü arayüz, geçmiş, görev sayfası; bazı araç sayfaları yönlendirici | Durum, devam, iptal, kanıt ve hata nedenlerini anlaşılır göster; destek ve KVKK taslaklarını hukuk sürecine taşı | Kullanıcı görevlerinin görülebilir, tekrar başlatılabilir, denetlenebilir deneyimi | Mobil/masaüstü gerçek tarayıcı görevi; kullanılabilirlik ve gizlilik kabulü |
| P6 Kaynak güncelliği | Tarihi planlar kaynak ve sürüm kayması içeriyor | Resmî kaynak sicili, kontrol tarihi, yeniden kontrol tetikleyicisi, SDK sürümü ve yenileme geçmişi | Yeni mimari kararında bayat kaynak otomatik/manuel işaretlenir | Sicil kontrol raporu; bayat kaynakların kanıtsız kullanımı engellenir |
| P7 Premium | Ücretsiz ürünün e2e kalitesi ve maliyeti henüz kanıtlı değil | Ayrı ücretsiz/ücretli maliyet defteri, izinli ücretli modeller, fiyat ve ödeme/kota/onay/iptal akışları | Ekonomisi ve hukuki koşulları doğrulanmış Premium | İlk uçtan uca gerçek ödeme; negatif bakiye/çift harcama yok; açık kullanıcı onayı |

## 4. İlk parçalı sürüm sırası

**D0 / Bu oturum:** Planı, teslim defterini, kaynak sicilini ayrı geliştirme dalında yayımla. Kod ve üretime dokunma.

**D1 / Ölçüm altyapısı:** Kullanıcı isteği → ilk gerçek model token'ı → tamamlanma adımlarına anonim, korele süreler ekle; 35 saniye sorununu tahminle değil ölçümle ayır. İlk hedef: gerçek, tarihli P50/P95 tablosu. Hız sonucu henüz iddia edilmez.

**D2 / Chat stabilizasyonu:** Daha önce üretilmiş 3d531d5 düzeltmesinin gerçek hesap oturumu, iptal/yeniden bağlanma ve sunucu kesilmesi kabulünü yap. P0 ölçümlerini karşılaştır. Ana dala merge ve production için ayrı açık onay al.

**D3 / Kesintiden kurtulan tek uzun görev:** Mevcut run store üzerinde 1 uzun işin en az bir alt araç çağrısı sırasında worker öldürme + geri kazanım senaryosu. Aynı harici eylem iki kere yapılmaz. Kapanma/yeniden açılma kaydı üretilir.

**D4 / Alt ajan pilotu:** 1 yönetici + 2 bağımsız alt ajan; 2 ayrı işi paralel yürütüp artefakt ve kullanıcı kabul durumunu tek sonuçta birleştir. Kullanıcı metniyle sabit tool veya model rotası kurulmaz.

**D5 / Ücretsiz sağlayıcı kalite kapısı:** Gerçek sağlayıcı akışları, tool-calling, süre, 429 ve kullanım izni belgelendirilir; ücretsiz çalıştığı kanıtlanmayan sağlayıcı için ödeme taahhüdü yaratılmaz.

**D6 / Ürün, güven, gelir:** Kayıtsız/hesaplı kullanım deneyimi, onaylı yasal metinler, ticari host koşulları; ücretsiz ürün kabulünden sonra Premium pilotu.

## 5. Net ölçüm ve kabul ilkeleri

- TTFT = kullanıcı isteğinin sunucuya ulaşması ile **ilk gerçek model içeriğinin** istemciye gönderilmesi. 'Görev başladı' bildirimi TTFT sayılmaz.
- Sohbet hedefi (ölçümden sonra gözden geçirilecek ürün eşiği): kısa, araçsız istek için ilk model içeriği P95 < 8 sn; toplam yanıt P95 < 15 sn. Bunlar gerçek veri değil **hedef**. Sağlayıcı/kota/hata ayrı segmentlerde raporlanır.
- Yüksek hacimli testler ücretsiz sağlayıcı kotasını bitirecek şekilde körlemesine çalıştırılmaz; gerçek ağ/sır içeren testler mevcut CANLI-KAPISI.md yöntemiyle açık tetiklenir.
- Uzun görev: bağlantı kopması, worker ölümü, süreç restart, yarışan worker, lease kaybı, yarım harici yazma ve insan onayı durumları test edilir.
- Model yetkisi: araç ve yetenek seçimini model yapar; keyword yönlendirme, keyfi tavan, cevabı değiştiren filtre eklenmez (AGENTS.md §0). Güvenlikte kullanıcı izolasyonu, sır koruması ve eylem onayı korunur.
- Yeni mimari adayında sadece işlevi değil; gecikme, toplam kaynak tüketimi, destek koşulu, bakımı, migrate/rollback süreci ve bağımlılık olgunluğu karşılaştırılır. Beta otomatik tercih edilmez, otomatik elenmez.
- Her teslimde önce/sonra, etkilenen dosyalar, Git SHA, test komutları ve gerçek çıktısı, preview adresi, canlı onay ve rollback yöntemi bulunur. Verisi yoksa 'ölçülmedi' yazılır.

## 6. Ücretsiz yürütmenin dürüst altyapı sınırı

- OpenAI Background mode, tek bir model yanıtını asenkron yürütür; Başak'ın günlerce süren çok adımlı ve çok sağlayıcılı görev motorunun yerine otomatik geçmez.
- Vercel Hobby Fluid Compute HTTP fonksiyonu için belgelenmiş üst sınır 300 saniyedir. Hobby Cron en sık günde bir ve zamanlaması yaklaşık bir saat esnek olduğundan, düşük gecikmeli işçi uyandırma için tek başına çözüm değildir.
- Vercel 2026-10-15 itibarıyla Python GA; Workflow Python ve Daemons yeni/beta seçeneklerdir. Resmî fiyat/plan/erişim koşulları doğrulanmadan ücretsiz sürekli çalışma varsayılmaz.
- Depodaki docs/ORACLE-TASINMA-PLANI.md mevcut bir aday ve kurulum planıdır, çalışır üretim worker'ının kanıtı değildir. Sağlayıcı hesabı, compute, kalıcılık, elektrik/limit, tenant izolasyonu ve maliyet gerçek testte değerlendirilir.

## 7. Bulut envanteri: Oracle + Render + Vercel

**Kritik ayrım:** Kullanıcı Oracle ve Render bağlantılarının kurulduğunu belirtti. Bağlantı bilgisi operasyonel sağlık testi değildir. Bu oturumdaki erişilebilir araçlar yalnız Vercel deployment durumunu doğruladı; Oracle ve Render hesaplarındaki çalışan servis/işçi listesine doğrudan erişilemedi. GitHub'da Oracle kurulum betikleri var; Render için çalışır servis veya deployment yapılandırması bu taramada bulunmadı. Bu nedenle Oracle/Render **bağlantı beyanı mevcut**, **canlı çalışma kanıtı bekleniyor** durumundadır.

| Platform | Bugün kanıtlanan | Resmî ücretsiz sınır | Hedef rol / test |
|---|---|---|---|
| Vercel | Production a167e6d READY, geliştirme Preview READY, Hobby planı | Fluid Compute Hobby HTTP üst süresi 300 sn. Sürekli background worker kabulü değildir. | Web/API ve kısa sohbet, gerçek TTFT; ticari plan şartları ayrıca kontrol |
| Oracle Cloud | docs/ORACLE-TASINMA-PLANI.md ve deploy/oracle/{setup.sh,setup-ol9.sh,*.service} var; gerçek VM/servis durumu bu oturumda okunamadı | OCI Always Free A1 için 1.500 OCPU-saat ve 9.000 GB-saat/ay; kapasite, hesap ve kota şartlarına tabi | Bağımsız uzun görev işçisi adayı; VM heartbeat, restart ve dış eylem idempotansı test edilmeden 'çalışıyor' denmez |
| Render | Kullanıcı bağlantıyı bildirdi; bu oturumda Render API/servis kimliği bulunamadı | Free web servisleri 15 dk isteksizlikte uyur; tekrar açılması yaklaşık 1 dk; yerel dosya geçicidir. Sürekli Background Worker ücretsiz değildir | Önizleme, demo, ölçümlü failover adayı; sürekli ücretsiz işçi olarak varsayılmaz |

**Kontrol kanıtları:** 
- Vercel: Vercel deployment API, production SHA ve preview hazır durumu 2026-10-29.
- Oracle resmi: https://docs.oracle.com/iaas/Content/FreeTier/freetier.htm ve https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- Render resmi: https://render.com/docs/free ve https://render.com/docs/your-first-deploy ve https://render.com/docs/background-workers
- Vercel resmi: https://vercel.com/docs/functions/limitations

**Gerçek bağlantı kabul listesi (hiçbiri henüz Oracle/Render için bu oturumda tamamlanmadı):**
1. Sağlayıcı kontrol panelinden servis kimliği, tipi, planı, bölgesi ve canlı deployment SHA kanıtı.
2. Servis health, işçi heartbeat, veri tabanı bağlantısı, isteğin doğru kullanıcıya ait olması.
3. 5 dakikalık/1 saatlik görev + web bağlantısı koparma, sunucu/işçi yeniden başlatma, ikinci işçi yarışı.
4. Kaldığı yerden tamamlama, çift dış eylem sıfır, kullanıcıya olay akışı ve teslim edilebilir artefakt.
5. Toplam maliyetin ve kullanım izinlerinin resmî plandan doğrulanması; ücretli yol kullanıcı onayı olmadan etkinleşmez.

**Karar yasağı:** Render bağlı diye sürekli ücretsiz işlem gücü varsayılmaz; Oracle betiği var diye VM çalışıyor denmez; Vercel READY diye gerçek sohbet gecikmesi kanıtlanmış sayılmaz.

## 8. Karar kaydı, canlı kapısı ve geri alma

Her karar: problem → mevcut kanıt → en az iki teknik seçenek → performans/maliyet/güvenlik farkı → seçilen yöntem → ölçüm sonucunu barındırır. İlk karar: P0'ı ölçmeden normal sohbet için yeni orkestrasyon eklenmez; P2'de ise yürütme motoru yeniden yazımına tamamen açıktır.

**Release gate:** geliştirme dalı → CI → preview → gerçek kullanıcı/gerçek hesap kabulü → açık production onayı → dağıtım → aynı metriklerle post-deploy ölçüm → rollback. Merge'in production deploy tetikleyebileceği unutulmaz. Öncesi/sonrası eşik sağlanmazsa iş 'teslim edildi' değil 'geri alındı/açık' yazılır.

**Kaynak güncelliği:** docs/BASAK-RESMI-KAYNAK-SICILI.md. Haftalık ve her mimari/ödeme kararından önce yeniden doğrulama yapılır; bağlantının varlığı içerik/sürümün değişmediğini kanıtlamaz.
