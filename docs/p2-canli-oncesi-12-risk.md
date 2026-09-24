# P2 — Canlı Öncesi 12 Risk Denetimi

Dal: `preview/p2-arac-ara-profesyonel`

Bu belge doğrulama manifestosudur. Kodun varlığı gerçek Preview E2E kanıtı
sayılmaz. CI, provider pilotu ve gerçek Preview testi ayrı ayrı kaydedilir.

| # | Risk | P2 düzenlemesi | Canlı kabul kanıtı |
|---|---|---|---|
| 1 | Meta yetenek kapısı / gizli araç kaybı | Ana model meta araç görmez. Görünmez resolver gerçek araç adaylarını seçer; bozuk seçimde tam katalog fail-open. | Çok alanlı gerçek görev E2E |
| 2 | Araç gereken işte ezber final | Resolver `tool_required=true` derse ana çağrı `required`; toolsuz düz final kabul edilmez. | Güncel veri + proje/dosya gerçek görevleri |
| 3 | Sahte/görsel streaming | Araç sonrası final ve araçsız final `brain.cevapla_yayin` üzerinden gerçek provider parçalarını taşır; frontend animasyonu fallback. | İlk `parca` finalden önce ağda görülmeli |
| 4 | Arama sonucu kaynak sanılması | Final Kaynaklar yalnız `sayfa_oku` / `derin_oku` ile gerçekten okunan URL'lerden çıkar. | Search-only URL final kaynakta olmamalı |
| 5 | Halüsinasyonun hafızada kanıtlaşması | Hafıza kayıtları `sohbet_aracli/aracsiz` provenance taşır; prompt bunları KANIT DEĞİL diye işler; eksik/truncated final episodik hafızaya yazılmaz. | Stale hafıza + güncel araç çelişki testi |
| 6 | Preview/production hafıza farkı | Ayrı `BASAK_PREVIEW_DATABASE_URL` desteklenir; production ile aynı DB hedefi reddedilir. Yoksa `sqlite_ephemeral` açıkça raporlanır. | Ayrı staging Postgres ile E2E |
| 7 | Sınırsız model bağlamı | Tam geçmiş diskte korunur; modele giden pencere yaklaşık token bütçesine göre ölçülür, sabit N mesaj routerı yoktur; compact olayı görünür. | Uzun sohbet E2E |
| 8 | Dev tool sonucu | `sayfa_oku/derin_oku` cursor/offset ile <=50K karakterlik parçalar döndürür; toplam/erişilebilir/tavan meta bilgisi açık. | Uzun sayfa cursor testi |
| 9 | Provider mid-chain değişimi | Reasoning/tool kayıtları korunur; sağlayıcı değişimi `providerSwitch` olayıyla görünür. | Gerçek failover E2E |
| 10 | Sonsuz aynı araç döngüsü | Genel tur tavanı yok. Sadece aynı tool+args+aynı sonuç üçüncü gerçek çalıştırmada engellenir ve `loopGuard` üretilir. | Repeat-loop davranış testi |
| 11 | Yönlendir bağlam kaybı | Tamamlanan adımlar, gerçekten kullanılan kaynaklar ve kısmi cevap yeni talimata çalışma bağlamı olarak taşınır; gerçek thread-resume iddiası yok. | Redirect E2E |
| 12 | `max_tokens` sessiz kesilme | `finish_reason` taşınır; teknik final continuation denenir; tamamlanamazsa `truncated` ve açık eksik işareti, güvenilir hafızaya yazmama. | Uzun çıktı testi |

## Referans alınan resmi desenler

- OpenAI Agents SDK: deferred tool loading / tool search, tool choice ve streaming.
- Anthropic: tool search, context editing, stop reason / max_tokens işleme.
- Google Gemini: function calling modes ve compositional/sequential tool calling.
- LangGraph: interrupt/checkpoint ile gerçek resumable workflow ayrımı.

## Kabul sırası

1. Kotasız unit/regresyon CI.
2. P2 gerçek provider pilot matrisi (kota kontrollü).
3. Gerçek Vercel Preview E2E.
4. Furkan görsel/işlev testi.
5. Ancak yeni açık onaydan sonra production değerlendirmesi.

Production/main bu P2 çalışmasının hedefi değildir.
