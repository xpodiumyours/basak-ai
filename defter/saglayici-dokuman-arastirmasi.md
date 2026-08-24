# Saglayici dokuman arastirmasi - sozlesme modu icin resmi kanitlar

- **kim:** opencode (mimar)
- **tarih:** 2026-08-24
- **konu:** OpenAI/Anthropic/Kimi/DeepSeek resmi dokumanlari dogrulandi; FAZ 1 ve
  FAZ 4 icin somut kararlar
- **tip:** arastirma
- **omur:** 30g (saglayici dokumanlari degisir; URL+tarih kayitli)
- **kaynak:** anthropic.com/engineering/building-effective-agents,
  developers.openai.com/api/docs/guides/agent-builder-safety,
  api-docs.deepseek.com/guides/json_mode + /guides/anthropic_api,
  platform.kimi.ai/docs/guide/response_format (erisim: 2026-08-24)

## Dogrulanan resmi kaynaklar (Resmidokumanuyum.md atiflari saglam)

1. **Anthropic Building Effective Agents:** basit birlesebilir oruntuler >
   karmaşik framework; arac arayuzune (ACI) prompt kadar emek; olc ve iterasyon
   yap. Raporun "basit mimari" olcutu dogru dayanakta.
2. **OpenAI agent-builder-safety:** guvenilmeyen veri developer mesajina
   giremez; yapisal cikti veri akisini sinirlar AMA riski kaldirmez; arac
   onaylari acik kalmali; trace grader/eval onerisi. (Not: Agent Builder
   urunu 30 Kasim 2026'da kapaniyor; guvenlik rehberi gecerli.)
3. **DeepSeek JSON Output (resmi):** response_format json_object destekli;
   prompt'ta "json" kelimesi VE ornek sart; max_tokens dusukse JSON kirilir;
   **bilinen hata: bos content donebiliyor**.
4. **Kimi/Moonshot (resmi):** json_object + json_schema(strict) destekli;
   zayif modellerde (kimi-k2.6 benzetmesi: bizim qwen2.5:3b) karmasik sema
   bozuluyor -> **sema basit tutulmali + is katmaninda ikinci dogrulama**
   (bizim sozlesme_gecerli_mi tam bu); finish_reason=length kirilma kontrolu
   oneriliyor; response_format prefix-cache'i bozmuyor.

## Plan kararlarina dogrudan etki eden bulgular

| Bulgu | Plan karari |
|---|---|
| DeepSeek bos-content hatasi + Kimi length-truncation uyarisi | Kapı v2'ye DURUM MAKINESI eklenecek: ok/refusal/incomplete/invalid + tek kontrollu duzeltme (Resmidokumanuyum P1 maddesinin resmi gerekcesi) |
| Kimi: zayif modelde karmaşik sema kirilir | Bizim {yanit, iddialar} semasi zaten minimal - oldugu gibi kalacak; daha karmasiklasmayacak |
| Her iki saglayici max_tokens disiplini istiyor | Sozlesme modunda max_tokens artirilacak + finish_reason denetlenecek |
| DeepSeek'in Anthropic-uyumlu ucu (api.deepseek.com/anthropic), tool_choice:none TAM DESTEKLI | Olmus kod durumdaki deepseek.py canlandirilabilir; groq'un "tool choice is none" hatasini yasamayan saglayici havuza girecek |
| Kimi api.moonshot.ai/v1 OpenAI-uyumlu | Yeni adaptor adayi; ama veri karti olmadan acilmayacak |

## Veri karti uyarisini guclendiren gercek

Hem DeepSeek hem Moonshot Cin merkezli; Resmidokumanuyum.md P0'daki
"saglayici veri karti olmadan hassas veri gitmez" kurali bu saglayicilar icin
kritik. Kart dolana kadar ikisi de zincire ALINMAYACAK.

## Onerilen siralama degisikligi YOK

Groq tool_choice duzeltmesi + temiz A/B ilk sirada kaliyor; bu arastirma o
duzeltmenin tasarimini netlestirdi: son turda tool_call gelirse (a) ciktiyi
tool-callsuz tekrar iste (tek kontrollu retry) veya (b) DeepSeek gibi
tool_choice:none'i dogru uygulayan saglayiciya gec - zincir bunu zaten yapiyor,
sadece groq ayagi patlıyor.
