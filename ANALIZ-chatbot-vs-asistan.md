# Başak: Chatbot mu, Asistan mı? — Koddan Gerçek Analiz (22 Ağustos 2026)

## Tanımlar

| | Chatbot | AI Asistan |
|---|---|---|
| Etkileşim | Pasif — kullanıcı başlatır | Aktif — kendi başına hareket eder |
| Görev | Soru-cevap | Çok adımlı görevleri kendi yürütür |
| Zamanlama | Yok — sadece o an | Hatırlatır, zamanlar, otomatik başlar |
| Bağlam | Oturum içi | Oturumlar arası + proaktif |
| Öğrenme | Yok | Etkileşimlerden gelişir |

## Başak'ın Gerçek Durumu

### 1. Etkileşim Modeli → PASİF (Chatbot)
- Kullanıcı "Gönder" basar → cevap gelir
- Başak **asla kendi başına mesaj atmaz**
- Başak **asla "hey Furkan, bugün şunu yapman lazım" demez**
- Başak **asla zamanlanmamış bir görevi kendi başlatmaz**

### 2. Araç Kullanımı → VAR ama SINIRLI
- 9 araç: web_search, görevler, notlar, dosya, uygulama, hatırlatmalar
- Tümü **kullanıcı komutuyla** çalışıyor
- Kullanıcı "süt al" deyince add_task çağrılıyor
- Başak kendi başına "süt bitmiş, yenisini ekleyeyim" demiyor

### 3. Hafıza → VAR ama ETKİLEŞİMSİZ
- SQLite + vektor + BM25 ile hafıza motoru var
- Her cevap sonrası episodic hafızaya yazılıyor
- Her soru öncesi ilgili anılar bağlama ekleniyor
- Ama hafıza **sadece okunuyor/yazılıyor** — kendi başına hareket etmiyor

### 4. Çoklu Beyin → VAR ama OTOMATİK DEĞİL (sadece yanıt üretiminde)
- 9 bulut + 1 yerel = 10 sağlayıcı
- Görev türüne göre otomatik seçim
- Kota dolarsa otomatik geçiş

### 5. Arka Plan Çalışma → YOK
- Tepsi simgesi var ama sadece pencere gizleme
- Hiçbir zamanlanmış görev yok
- Hiçbir otomatik izleme yok
- Hiçbir proaktif bildirim yok

## Sonuç: Başak bir CHATBOT'tur

**Neden:**
1. Tamamen pasif — kullanıcı başlatmadıkça hiçbir şey yapmıyor
2. Tek oturumlu etkileşim — mesaj → cevap döngüsü
3. Proaktif özellik yok — zamanlama, bildirim yok
4. Kendi başına karar almıyor
5. Öğrenme döngüsü yok (P4'te planlandı)

**Chatbot'tan üstün yönleri:**
- ✅ Kalıcı hafıza
- ✅ Araç kullanımı
- ✅ Sesli etkileşim
- ✅ Kişilik/kimlik
- ✅ Çoklu beyin + otomatik geçiş

## Asistan Olmak İçin Eksikler

| Eksik | Durum | Planlanan Faz |
|---|---|---|
| Proaktif hatırlatma | ❌ | P5 zamanlayıcı |
| Otomatik görev başlatma | ❌ | P5-P6 job queue |
| Kendi başına bilgi tarama | ❌ | P4 öğrenme döngüsü |
| Uygulama durumu izleme | ❌ | P6 watchdog |
| Öğrenme + uyum | ❌ | P4 müfredat |
| Wake word + sürekli dinleme | ❌ | P7 sesli Jarvis |

**Özet:** Başak şu an **gelişmiş bir chatbot**. Asistan olmak için proaktif olması lazım.
