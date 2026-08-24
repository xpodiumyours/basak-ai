# Vibe coding ile Jarvis tarzı yapay zekâ asistanı geliştirme

> Tarih: 24 Ağustos 2026  
> Kapsam: Başak'ın yerel/hibrit mimarisine uygulanabilir, birincil kaynaklara dayalı kısa araştırma.

## Kısa sonuç

Vibe coding, fikri doğal dille hızla çalışan bir prototipe dönüştürmek için yararlıdır; fakat Başak gibi dosya okuyan, kalıcı hafıza tutan ve bilgisayarda eylem yapabilen bir asistanda **teslim yöntemi değil, keşif yöntemi** olmalıdır. Terimi ortaya atan Andrej Karpathy, yaklaşımı kodu ve diff'leri ayrıntılı okumadan, hata mesajlarını modele geri vererek ilerlemek şeklinde anlatmış ve bunu özellikle geçici hafta sonu projeleri bağlamında sınırlamıştır ([Karpathy'nin ilk el açıklaması](https://x.com/karpathy/status/1886192184808149383)). Başak için doğru karşılık: doğal dille hızlı keşif + küçük değişiklik + otomatik kanıt + insan onayı.

## Önerilen mimari

`mikrofon → STT → niyet/yönlendirme → hafıza/RAG → kısıtlı araç yürütücüsü → doğrulanmış cevap → TTS`

- **Yerel varsayılan, bulut kontrollü yedek:** Basit ve kişisel işler Ollama'da kalmalı; bulut yalnız ölçülmüş ihtiyaçta devreye girmeli. Yönlendirme kodla görünür olmalı, model kendi başına gizli veriyi buluta taşıyamamalıdır. Anthropic'in üretim deneyimi de önce en basit çözümün kurulmasını, karmaşıklığın yalnız gerekli olduğunda artırılmasını ve kolay işleri küçük/ucuz, zor işleri güçlü modellere yönlendirmeyi önerir ([Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)).
- **Model karar önerir, politika katmanı uygular:** Araç seçimi LLM'den gelebilir; fakat izin, yol beyaz listesi, kota, tekrar sınırı ve onay kararı deterministik kodda kalmalıdır. OWASP; en az yetkiyi, salt-okunur/yazma ayrımını, hassas eylemde açık onayı ve geri döndürülemez işlerde karar ile yürütmenin ayrılmasını önerir ([AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html), [Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/)). Başak'ın mevcut izin katmanı ve “yetki tavanı” bu yönde doğrudur.
- **Serbest metin yerine sözleşme:** Ollama, cevapları JSON Schema'ya zorlayabilir ve Pydantic ile yeniden doğrulamayı örnekler ([Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs)). Araç çağrıları da yerel API'de desteklenir ([Tool Calling](https://docs.ollama.com/capabilities/tool-calling)). Bu nedenle ANA-PLAN Faz 1'deki `{yanit, iddialar, dayanak}` sözleşmesi doğru önceliktir; şema hatasında sınırlı yeniden deneme, ardından güvenli `[B] ölçemedim` dönüşü olmalıdır.
- **Hafıza tek parça sohbet dökümü olmamalı:** Ollama embedding'leri semantik arama/RAG için üretir ve indeksleme ile sorguda aynı embedding modelinin kullanılmasını önerir ([Embeddings](https://docs.ollama.com/capabilities/embeddings)). SQLite FTS5, sözcük eşleşmesi ve BM25 sıralaması sağlar ([SQLite FTS5](https://www.sqlite.org/fts5.html)); bu yüzden Başak'taki BM25 + vektör hibriti isabetli bir temeldir. Ancak dış belge ve web içeriği talimat değil **güvenilmeyen veri** sayılmalı; belleğe yazmadan önce kaynak doğrulama, boyut/ömür sınırı ve hassas veri denetimi uygulanmalıdır ([OWASP Vector and Embedding Weaknesses](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/)).
- **Ses katmanı bağımsız ve ölçülebilir olmalı:** faster-whisper CPU'da `int8` çalışmayı ve Silero VAD ile sessizlik süzmesini doğrudan destekler ([faster-whisper](https://github.com/SYSTRAN/faster-whisper)); Piper güncel Open Home Foundation deposunda hızlı, tamamen yerel TTS olarak sürdürülür ([Piper](https://github.com/OHF-Voice/piper1-gpl)). Model boyutu, VAD eşiği ve ses hızı “hissettirerek” değil; Türkçe komut kümesinde doğruluk, ilk ses gecikmesi ve toplam tur süresiyle seçilmelidir.

## Başak için geliştirme döngüsü

1. **Tek davranışı tarif et:** Girdi, beklenen sonuç, izin sınırı ve başarısızlık davranışı yazılır.
2. **Önce kanıtı sabitle:** Gerçek hatalardan küçük bir eval bankası oluşturulur. Anthropic, başlangıç için gerçek başarısızlıklardan türetilmiş 20–50 basit görevin bile değerli olduğunu belirtiyor ([Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)).
3. **En küçük değişikliği üret:** Ajan yalnız ilgili dosyaları değiştirir; diff insan tarafından okunur. Kod ajanlarında tek dala yazma, zorunlu kontroller ve insanın birleştirmesi etkili güvenlik sınırlarıdır ([GitHub Copilot agent riskleri](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations)).
4. **Üç kapıdan geçir:** pytest/regresyon; gerçek uçtan uca ses/araç provası; kötü niyetli web-belge, yol kaçışı, sır sızıntısı ve izinsiz eylem denemesi.
5. **Ölç, karşılaştır, sonra tut:** Doğruluk, yanlış eylem, dürüst red, gecikme ve token/bulut kullanımı tabana göre kötüleşirse değişiklik geri alınır.
6. **Kanıtla kaydet:** Sonuç, ölçüm ve bilinen sınır deftere yazılır; yeni bulunan her hata eval bankasına eklenir.

## Başak için öncelik kararı

Mevcut **ANA-PLAN Faz 0 → Faz 1** sırası araştırmayla uyumludur: önce sabit eval/ölçüm, sonra yapısal cevap ve iddia→kanıt bağlantısı. Yeni bir framework, çoklu ajan veya daha büyük model eklemek şu anda ana darboğazı çözmez. En yüksek getirili kısa sıra:

1. Eval bankasını ve sayısal tabanı sabitle.
2. Yapısal çıktı + şema doğrulama + güvenli geri dönüşü tamamla.
3. Yazma/sistem/dış iletişim eylemlerine işlem-özel, süreli kullanıcı onayı ekle.
4. STT/TTS ve yerel→bulut yönlendirmesini aynı gerçek senaryo setinde gecikme/doğruluk/maliyet ile ölç.

Bu yaklaşım Başak'ı “AI kod yazdı ve çalışıyor gibi göründü” düzeyinden, her davranışı kanıtlanabilen yerel bir asistana taşır.
