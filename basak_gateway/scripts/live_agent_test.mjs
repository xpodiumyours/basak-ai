import { agentChat } from "../src/agent.js";

const env = {};
const cases = [
  {
    name: "salt sohbet",
    prompt: "Merhaba Başak. Nasılsın? Kısa cevap ver.",
    check: (r) => (r.toolsUsed || []).length === 0
  },
  {
    name: "saat araci",
    prompt: "Şu an İstanbul'da saat kaç? Tahmin etme, gerekli aracı kullan.",
    check: (r) => (r.toolsUsed || []).includes("simdi")
  },
  {
    name: "hesap araci",
    prompt: "137.42 ile 18.7'yi çarp, 927.31 ekle ve sonucu 3.14'e böl. Kesin sonucu ver.",
    check: (r) => (r.toolsUsed || []).includes("hesapla")
  },
  {
    name: "github araci",
    prompt: "Başak projesinin GitHub'daki son 5 Actions çalışmasının durumunu kontrol et ve kısaca söyle.",
    check: (r) => (r.toolsUsed || []).includes("github_durum")
  }
];

for (const c of cases) {
  let lastError = null;

  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const result = await agentChat(
        [{ role: "user", content: c.prompt }],
        env
      );

      if (!c.check(result)) {
        throw new Error(
          "beklenen arac davranisi yok: " + JSON.stringify(result.trace || [])
        );
      }

      console.log(JSON.stringify({
        case: c.name,
        ok: true,
        provider: result.provider,
        model: result.model,
        toolsUsed: result.toolsUsed,
        text: result.text.slice(0, 180)
      }, null, 0));

      lastError = null;
      break;
    } catch (error) {
      lastError = error;
      const message = String(error?.message || error);
      console.log(JSON.stringify({
        case: c.name,
        attempt,
        ok: false,
        error: message.slice(0, 500)
      }));

      if (!/429|rate|limit|quota/i.test(message) || attempt === 3) break;
      await new Promise((resolve) => setTimeout(resolve, 22000));
    }
  }

  if (lastError) throw lastError;
}
