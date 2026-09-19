import catalog from "./tool_catalog.json" with { type: "json" };
import schemas from "./tool_schemas.json" with { type: "json" };
import { agentTurn } from "./providers.js";

const AREA_DESCRIPTIONS = {
  internet: "harici web aramasi, haber, site, sayfa, URL ve sirket bilgisi; cihaz/sistem saati veya yerel tarih icin kullanilmaz",
  dosyalar: "dosya/klasor ve proje icerigi",
  projeler: "Git, GitHub, CI, test ve proje hat sagligi",
  gorevler: "gorevler, hatirlatmalar ve sistemden gercek su anki tarih/saat bilgisi (simdi araci)",
  hafiza: "Basak hafizasinda arama",
  gorsel: "goruntu analizi veya gorsel uretimi",
  katalog: "fatura, urun karti ve Vixrex katalog/yayin paketi",
  matris: "fikir/plan agaci, satirlar ve kanitlar",
  masaustu: "masaustu uygulamasi acma",
  hesap: "guvenli matematik hesabi"
};

const AREA_TEXT = Object.entries(AREA_DESCRIPTIONS)
  .map(([k, v]) => k + "=" + v)
  .join("; ");

export const CONTROL_TOOLS = [
  {
    type: "function",
    function: {
      name: "yetenek_ac",
      description:
        "Gercek bir arac gerektiginde once ihtiyac duydugun TEK yetenek alanini acar. " +
        "Alan secimini kullanicinin amacini anlayarak sen yaparsin; kod kullanici metnini siniflandirmaz. " +
        AREA_TEXT,
      parameters: {
        type: "object",
        properties: {
          alan: { type: "string", enum: Object.keys(catalog.areas) }
        },
        required: ["alan"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "son_cevap",
      description:
        "Kullaniciya verilecek nihai cevabi teslim eder. Gercek veri veya eylem gereken istekte " +
        "gerekli gercek araclar calisip sonuclari gorulmeden kullanma. Salt sohbette dogrudan kullan.",
      parameters: {
        type: "object",
        properties: { metin: { type: "string" } },
        required: ["metin"]
      }
    }
  }
];

const CONTRACT = [
  "AJAN CALISMA SOZLESMESI:",
  "- Ilk turda gercek arac semalari yuklu degildir.",
  "- Gercek veri veya eylem gerekiyorsa yetenek_ac ile tek alan sec.",
  "- Alan acilinca yalniz o alanin gercek araclari gelir.",
  "- Uygun araci veya araclari kendin sec; kod kullanici cumlesini siniflandirmaz.",
  "- Arac basarisizsa eylemi yapilmis gibi anlatma.",
  "- Ayni basarisiz araci ayni argumanlarla tekrar tekrar cagirma; baska uygun alan/arac sec veya durumu acikla.",
  "- Is tamamlaninca son_cevap aracini cagir.",
  "- Salt sohbet/aciklama isteginde son_cevap dogrudan kullan."
].join("\n");

const IDENTITY =
  "Sen Basak'sin. Turkce ve dogal konus. Gereksiz uzun cevap verme. " +
  "Gercek veri veya eylem gerektiginde mevcut araclari kullan; uydurma sonuc verme.";

const TOOL_BY_NAME = new Map((schemas.tools || []).map((t) => [t.function.name, t]));

function areaTools(area) {
  const allowed = new Set(catalog.areas?.[area] || []);
  return (schemas.tools || [])
    .filter((t) => allowed.has(t.function.name))
    .concat(CONTROL_TOOLS);
}

function cleanHistory(messages) {
  const out = [];
  for (const m of Array.isArray(messages) ? messages.slice(-20) : []) {
    if (!m || !["user", "assistant"].includes(m.role)) continue;
    const content = String(m.content || "").trim().slice(0, 12000);
    if (content) out.push({ role: m.role, content });
  }
  return out;
}

function parseArgs(raw) {
  if (raw && typeof raw === "object") return raw;
  try {
    const value = JSON.parse(raw || "{}");
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch {
    return {};
  }
}

function assistantState(message) {
  const out = {
    role: "assistant",
    content: Array.isArray(message?.content) ? message.content : (message?.content ?? ""),
    tool_calls: message?.tool_calls || []
  };
  for (const key of ["reasoning","reasoning_content","reasoning_details","thinking","reasoning_text","tool_plan"]) {
    if (message?.[key] !== undefined && message?.[key] !== null) out[key] = message[key];
  }
  return out;
}

function toolResult(result) {
  if (!result || typeof result !== "object") return String(result ?? "");
  if (result.error) return "Hata: " + result.error;
  return JSON.stringify(result);
}

function isPrivateHost(hostname) {
  const h = String(hostname || "").toLowerCase().replace(/^\[|\]$/g, "");
  if (!h || h === "localhost" || h.endsWith(".localhost") || h.endsWith(".local")) return true;
  if (h === "::1" || h.startsWith("fc") || h.startsWith("fd") || h.startsWith("fe80:")) return true;
  const m = h.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (!m) return false;
  const [a,b,c,d] = m.slice(1).map(Number);
  if ([a,b,c,d].some((x) => x > 255)) return true;
  return a === 10 || a === 127 || a === 0 ||
    (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 168) ||
    (a === 100 && b >= 64 && b <= 127);
}

function safeUrl(raw) {
  let u;
  try { u = new URL(String(raw || "")); }
  catch { throw new Error("Gecersiz adres"); }
  if (!["http:", "https:"].includes(u.protocol)) throw new Error("Yalniz http/https adresleri acilabilir");
  if (u.username || u.password) throw new Error("Kullanici bilgili URL acilamaz");
  if (isPrivateHost(u.hostname)) throw new Error("Ic/yerel ag adresleri yasak");
  if (u.port && !["80","443"].includes(u.port)) throw new Error("Yalniz 80/443 portlari acilabilir");
  return u;
}

async function safeFetch(raw, init = {}, maxRedirects = 5) {
  let u = safeUrl(raw);
  for (let i = 0; i <= maxRedirects; i++) {
    const r = await fetch(u.toString(), { ...init, redirect: "manual" });
    if (![301,302,303,307,308].includes(r.status)) return { response: r, url: u.toString() };
    const location = r.headers.get("location");
    if (!location) return { response: r, url: u.toString() };
    u = safeUrl(new URL(location, u).toString());
  }
  throw new Error("Cok fazla yonlendirme");
}

function stripHtml(html) {
  return String(html || "")
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/\s+/g, " ")
    .trim();
}

function tokenizeExpression(expr) {
  const s = String(expr || "");
  const tokens = [];
  let i = 0;
  while (i < s.length) {
    if (/\s/.test(s[i])) { i++; continue; }
    if (/\d|\./.test(s[i])) {
      let j = i + 1;
      while (j < s.length && /[\d.]/.test(s[j])) j++;
      const n = Number(s.slice(i, j));
      if (!Number.isFinite(n)) throw new Error("Gecersiz sayi");
      tokens.push({ type: "n", value: n });
      i = j;
      continue;
    }
    if (s.slice(i, i + 2) === "**") { tokens.push({ type: "op", value: "**" }); i += 2; continue; }
    if ("+-*/%()".includes(s[i])) { tokens.push({ type: "op", value: s[i] }); i++; continue; }
    throw new Error("Yalniz + - * / % ** ve parantez kullanilabilir");
  }
  return tokens;
}

function calculate(expr) {
  const t = tokenizeExpression(expr);
  let p = 0;
  const peek = () => t[p]?.value;
  const take = (v) => {
    if (v !== undefined && peek() !== v) throw new Error("Ifade hatasi");
    return t[p++];
  };
  function primary() {
    if (peek() === "+") { take("+"); return primary(); }
    if (peek() === "-") { take("-"); return -primary(); }
    if (peek() === "(") {
      take("("); const v = add(); take(")"); return v;
    }
    const x = take();
    if (!x || x.type !== "n") throw new Error("Ifade hatasi");
    return x.value;
  }
  function power() {
    let left = primary();
    if (peek() === "**") { take("**"); left = left ** power(); }
    return left;
  }
  function mult() {
    let left = power();
    while (["*","/","%"].includes(peek())) {
      const op = take().value, right = power();
      if ((op === "/" || op === "%") && right === 0) throw new Error("Sifira bolme");
      left = op === "*" ? left * right : op === "/" ? left / right : left % right;
    }
    return left;
  }
  function add() {
    let left = mult();
    while (["+","-"].includes(peek())) {
      const op = take().value, right = mult();
      left = op === "+" ? left + right : left - right;
    }
    return left;
  }
  const result = add();
  if (p !== t.length || !Number.isFinite(result)) throw new Error("Ifade hesaplanamadi");
  return result;
}

const REPOS = {
  basak: "xpodiumyours/basak-ai",
  vixrex: "xpodiumyours/vixrex",
  numeramatch: "xpodiumyours/NumeraMatch",
  xses: "xpodiumyours/xses"
};

async function githubJson(path) {
  const r = await fetch("https://api.github.com" + path, {
    headers: { accept: "application/vnd.github+json", "user-agent": "Basak-Gate" }
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error("GitHub " + r.status + ": " + (data?.message || "istek basarisiz"));
  return data;
}

async function githubStatus(args) {
  const repo = REPOS[String(args.proje || "").toLowerCase()];
  if (!repo) return { error: "Bilinmeyen proje" };
  const op = String(args.islem || "");

  if (["calisma_liste","run_list","kosular"].includes(op)) {
    const d = await githubJson("/repos/" + repo + "/actions/runs?per_page=5");
    return { result: (d.workflow_runs || []).slice(0, 5).map((r) => ({
      name: r.name, status: r.status, conclusion: r.conclusion, headBranch: r.head_branch
    })) };
  }

  if (["pr_liste","pr_list"].includes(op)) {
    let state = String(args.durum || "open").toLowerCase();
    const mergedOnly = state === "merged";
    if (mergedOnly) state = "closed";
    if (!["open","closed","all"].includes(state)) return { error: "Gecersiz durum" };
    const d = await githubJson("/repos/" + repo + "/pulls?state=" + state + "&per_page=30");
    const list = (Array.isArray(d) ? d : [])
      .filter((x) => !mergedOnly || Boolean(x.merged_at))
      .map((x) => ({
        number: x.number, title: x.title,
        state: x.merged_at ? "MERGED" : x.state,
        headRefName: x.head?.ref
      }));
    return { result: list };
  }

  if (["pr_goruntule","pr_gor","pr_view"].includes(op)) {
    const no = Number(args.no);
    if (!Number.isInteger(no) || no < 1) return { error: "PR numarasi sayi olmali" };
    const p = await githubJson("/repos/" + repo + "/pulls/" + no);
    return { result: {
      number: p.number, title: p.title,
      state: p.merged_at ? "MERGED" : p.state,
      mergedAt: p.merged_at, headRefName: p.head?.ref
    }};
  }

  return { error: "Gecerli islem: pr_liste, pr_goruntule, calisma_liste" };
}

export async function executeWebTool(name, args) {
  try {
    if (name === "simdi") {
      const text = new Intl.DateTimeFormat("tr-TR", {
        timeZone: "Europe/Istanbul",
        weekday: "long", year: "numeric", month: "long", day: "numeric",
        hour: "2-digit", minute: "2-digit", second: "2-digit"
      }).format(new Date());
      return { result: text, timezone: "Europe/Istanbul" };
    }

    if (name === "hesapla") return { result: calculate(args?.ifade) };

    if (name === "adres_kontrol") {
      const started = Date.now();
      let out = await safeFetch(args?.url, { method: "HEAD" });
      if (out.response.status === 405) {
        out = await safeFetch(args?.url, { method: "GET", headers: { range: "bytes=0-0" } });
      }
      return { result: { durum: out.response.status, sure_ms: Date.now() - started, son_adres: out.url } };
    }

    if (name === "sayfa_oku" || name === "derin_oku") {
      const out = await safeFetch(args?.url, {
        method: "GET",
        headers: {
          "user-agent": "Basak-Gate/1.0",
          accept: "text/html,text/plain,application/json;q=0.8,*/*;q=0.2"
        }
      });
      const type = out.response.headers.get("content-type") || "";
      const raw = await out.response.text();
      const text = type.includes("html") ? stripHtml(raw) : raw.trim();
      const limit = name === "derin_oku" ? 250000 : 120000;
      return { result: text.slice(0, limit), son_adres: out.url, truncated: text.length > limit };
    }

    if (name === "github_durum") return await githubStatus(args || {});

    return {
      error:
        "Bu arac web kapisinda henuz gercek calistiriciya bagli degil. " +
        "Arac calistirilmadi; yapilmis gibi davranma.",
      bridge_required: true
    };
  } catch (error) {
    return { error: String(error?.message || error).slice(0, 900) };
  }
}

export async function agentChat(messages, env, turnFn = agentTurn) {
  const history = cleanHistory(messages);
  if (!history.length || history.at(-1).role !== "user") {
    throw new Error("Gecerli kullanici mesaji yok");
  }

  let expanded = [
    { role: "system", content: IDENTITY },
    { role: "system", content: CONTRACT },
    ...history
  ];
  let tools = CONTROL_TOOLS;
  let openedArea = null;
  const trace = [];
  const failedCalls = new Set();
  let lastProvider = "";
  let lastModel = "";

  for (let step = 0; step < 20; step++) {
    const turn = await turnFn(expanded, tools, env);
    lastProvider = turn.provider;
    lastModel = turn.model;
    const message = turn.message || {};
    const calls = Array.isArray(message.tool_calls) ? message.tool_calls : [];
    if (!calls.length) throw new Error("Ajan protokolu bozuldu: tool_call yok");

    const names = calls.map((c) => c?.function?.name || "");
    if (names.length && names.every((n) => n === "son_cevap")) {
      const args = parseArgs(calls[0]?.function?.arguments);
      const text = String(args.metin || "").trim();
      if (!text) throw new Error("son_cevap metni bos");
      return {
        text,
        provider: lastProvider,
        model: lastModel,
        agent: true,
        trace,
        toolsUsed: trace.filter((x) => x.kind === "tool" && x.ok).map((x) => x.name)
      };
    }

    expanded.push(assistantState(message));
    const offered = new Set(tools.map((t) => t?.function?.name).filter(Boolean));

    for (const call of calls) {
      const name = call?.function?.name || "";
      const args = parseArgs(call?.function?.arguments);
      const callId = call?.id || ("call_" + step + "_" + trace.length);
      let result;

      if (name === "yetenek_ac") {
        const area = String(args.alan || "");
        if (!offered.has("yetenek_ac")) result = { error: "yetenek_ac bu turda acik degil" };
        else if (!catalog.areas?.[area]) result = { error: "bilinmeyen yetenek alani" };
        else {
          openedArea = area;
          tools = areaTools(area);
          result = { acilan_alan: area, kullanilabilir_araclar: catalog.areas[area] };
          trace.push({ kind: "area", name: area, ok: true });
        }
      } else if (name === "son_cevap") {
        result = { error: "son_cevap gercek araclarla ayni turda kullanilamaz" };
      } else if (!TOOL_BY_NAME.has(name)) {
        result = { error: "bilinmeyen arac" };
      } else if (!offered.has(name)) {
        result = { error: "bu arac su an acik degil; once yetenek_ac kullan" };
      } else {
        const signature = name + ":" + JSON.stringify(args || {});
        if (failedCalls.has(signature)) {
          result = {
            error: "Ayni basarisiz arac ve argumanlar tekrar denenmedi; baska uygun yol sec."
          };
        } else {
          result = await executeWebTool(name, args);
          if (result.error) failedCalls.add(signature);
        }
        trace.push({
          kind: "tool",
          name,
          area: openedArea,
          ok: !result.error,
          bridgeRequired: Boolean(result.bridge_required)
        });
      }

      expanded.push({
        role: "tool",
        tool_call_id: callId,
        name,
        content: toolResult(result)
      });
    }
  }

  throw new Error("Ajan dongusu 20 turda final cevaba ulasamadi");
}
