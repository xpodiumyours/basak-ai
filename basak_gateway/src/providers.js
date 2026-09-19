export const PROVIDERS = ["groq","gemini","openrouter","glm","cloudflare","cohere","kilo","nvidia"];

const PROBE_TOOL = {
  type: "function",
  function: {
    name: "protokol_probe",
    description: "Protocol acceptance probe. Call exactly once and return BASAK_PROTOCOL_OK in echo.",
    parameters: {
      type: "object",
      properties: { echo: { type: "string", description: "Exactly BASAK_PROTOCOL_OK" } },
      required: ["echo"],
      additionalProperties: false
    }
  }
};

const PROBE_PROMPT = [
  "This is a provider tool-protocol acceptance test.",
  "Call protokol_probe exactly once.",
  "Set echo to BASAK_PROTOCOL_OK.",
  "Do not answer in plain text before the tool call."
].join(" ");

const OPENROUTER_PREFERENCE = [
  "nvidia/nemotron-3-ultra-550b-a55b:free",
  "nvidia/nemotron-3-super-120b-a12b:free",
  "google/gemma-4-31b-it:free",
  "poolside/laguna-s-2.1:free",
  "poolside/laguna-xs-2.1:free",
  "cohere/north-mini-code:free",
  "thinkingmachines/inkling-small:free",
  "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
  "inclusionai/ling-3.0-flash-fin:free",
  "nex-n2.5-mini:free",
  "openrouter/free"
];

function nonEmpty(v) {
  return typeof v === "string" && v.trim().length > 0;
}

export function providerStatus(env) {
  return {
    groq: nonEmpty(env.GROQ_API_KEY),
    gemini: nonEmpty(env.GEMINI_API_KEY),
    openrouter: nonEmpty(env.OPENROUTER_API_KEY),
    glm: nonEmpty(env.ZAI_API_KEY),
    cloudflare: nonEmpty(env.CLOUDFLARE_ACCOUNT_ID) && nonEmpty(env.CLOUDFLARE_API_TOKEN),
    cohere: nonEmpty(env.COHERE_API_KEY),
    kilo: true,
    nvidia: nonEmpty(env.NVIDIA_API_KEY)
  };
}

function safeError(value, secrets = []) {
  let out = String(value || "Bilinmeyen hata");
  for (const secret of secrets.filter(Boolean)) out = out.split(secret).join("[REDACTED]");
  return out.slice(0, 900);
}

async function fetchJson(url, init, secrets = [], timeoutMs = 45000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort("timeout"), timeoutMs);
  try {
    const response = await fetch(url, { ...init, signal: controller.signal });
    const raw = await response.text();
    let data = {};
    try { data = raw ? JSON.parse(raw) : {}; }
    catch { data = { raw: raw.slice(0, 700) }; }
    if (!response.ok) {
      const detail = data?.error?.message || data?.message || data?.raw || response.statusText;
      throw new Error(response.status + ": " + safeError(detail, secrets));
    }
    return data;
  } finally {
    clearTimeout(timer);
  }
}

function openAIConfig(provider, env) {
  if (provider === "groq") return {
    url: "https://api.groq.com/openai/v1/chat/completions",
    model: "openai/gpt-oss-120b",
    mode: "required",
    headers: { Authorization: "Bearer " + (env.GROQ_API_KEY || "") },
    secrets: [env.GROQ_API_KEY]
  };
  if (provider === "gemini") return {
    url: "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    model: "gemini-3-flash-preview",
    mode: "auto",
    headers: { Authorization: "Bearer " + (env.GEMINI_API_KEY || "") },
    secrets: [env.GEMINI_API_KEY]
  };
  if (provider === "glm") return {
    url: "https://api.z.ai/api/paas/v4/chat/completions",
    model: "glm-4.7-flash",
    mode: "auto",
    headers: { Authorization: "Bearer " + (env.ZAI_API_KEY || "") },
    secrets: [env.ZAI_API_KEY],
    extra: { thinking: { type: "enabled" } }
  };
  if (provider === "cloudflare") return {
    url: "https://api.cloudflare.com/client/v4/accounts/" + encodeURIComponent(env.CLOUDFLARE_ACCOUNT_ID || "") + "/ai/v1/chat/completions",
    model: "@cf/zai-org/glm-4.7-flash",
    mode: "required",
    headers: { Authorization: "Bearer " + (env.CLOUDFLARE_API_TOKEN || "") },
    secrets: [env.CLOUDFLARE_ACCOUNT_ID, env.CLOUDFLARE_API_TOKEN]
  };
  if (provider === "kilo") return {
    url: "https://api.kilo.ai/api/gateway/chat/completions",
    model: "kilo-auto/free",
    mode: "required",
    headers: env.KILO_API_KEY ? { Authorization: "Bearer " + env.KILO_API_KEY } : {},
    secrets: [env.KILO_API_KEY]
  };
  if (provider === "nvidia") return {
    url: "https://integrate.api.nvidia.com/v1/chat/completions",
    model: "openai/gpt-oss-20b",
    mode: "auto",
    headers: { Authorization: "Bearer " + (env.NVIDIA_API_KEY || "") },
    secrets: [env.NVIDIA_API_KEY]
  };
  throw new Error("OpenAI uyumlu olmayan sağlayıcı: " + provider);
}

const KILO_TOOL_PREFERENCE = [
  "nvidia/nemotron-3-ultra-550b-a55b:free",
  "poolside/laguna-s-2.1:free",
  "nex-agi/nex-n2.5-pro:free",
  "inclusionai/ling-3.0-flash-vl:free"
];
let cachedKiloToolModel = null;

async function chooseKiloToolModel() {
  if (cachedKiloToolModel) return cachedKiloToolModel;
  const data = await fetchJson(
    "https://api.kilo.ai/api/gateway/models",
    {},
    [],
    30000
  );
  const eligible = (data?.data || []).filter((m) => {
    const p = new Set(m?.supported_parameters || []);
    return m?.isFree === true && p.has("tools") && p.has("tool_choice");
  });
  for (const id of KILO_TOOL_PREFERENCE) {
    if (eligible.some((m) => m.id === id)) {
      cachedKiloToolModel = id;
      return id;
    }
  }
  if (eligible[0]?.id) {
    cachedKiloToolModel = eligible[0].id;
    return cachedKiloToolModel;
  }
  throw new Error("Kilo: tools + tool_choice destekli ucretsiz model yok");
}

async function chooseOpenRouterModel(apiKey) {
  const data = await fetchJson(
    "https://openrouter.ai/api/v1/models",
    { headers: { Authorization: "Bearer " + apiKey } },
    [apiKey],
    30000
  );
  const models = Array.isArray(data?.data) ? data.data : [];
  const eligible = models.filter((m) => {
    const id = String(m?.id || "");
    const supported = new Set(m?.supported_parameters || []);
    return id.endsWith(":free") && supported.has("tools") && supported.has("tool_choice");
  });
  for (const wanted of OPENROUTER_PREFERENCE) {
    const hit = eligible.find((m) => m.id === wanted);
    if (hit) return hit.id;
  }
  if (eligible.length) return eligible[0].id;
  throw new Error("OpenRouter: tools + tool_choice destekli ücretsiz model bulunamadı");
}

function readToolCall(message) {
  const calls = message?.tool_calls || [];
  if (!Array.isArray(calls) || calls.length === 0) throw new Error("tool_call üretilmedi");
  const call = calls[0];
  const fn = call?.function || {};
  if (fn.name !== "protokol_probe") throw new Error("yanlış araç çağrıldı: " + (fn.name || "boş"));
  let args = fn.arguments || "{}";
  if (typeof args === "string") {
    try { args = JSON.parse(args); }
    catch { throw new Error("tool arguments geçerli JSON değil"); }
  }
  if (args?.echo !== "BASAK_PROTOCOL_OK") throw new Error("echo doğrulaması başarısız");
  return call;
}

function assistantMessage(message) {
  const out = {
    role: "assistant",
    content: message?.content ?? "",
    tool_calls: message?.tool_calls || []
  };
  for (const key of ["reasoning","reasoning_content","reasoning_details","thinking","reasoning_text","tool_plan"]) {
    if (message?.[key] !== undefined && message?.[key] !== null) out[key] = message[key];
  }
  return out;
}

async function runOpenAIProtocol(provider, env) {
  const status = providerStatus(env);
  if (!status[provider]) throw new Error("sağlayıcı Cloudflare ortamında hazır değil");

  let config;
  if (provider === "openrouter") {
    const key = env.OPENROUTER_API_KEY || "";
    config = {
      url: "https://openrouter.ai/api/v1/chat/completions",
      model: await chooseOpenRouterModel(key),
      mode: "auto",
      headers: {
        Authorization: "Bearer " + key,
        "HTTP-Referer": "https://basak-gate.invalid",
        "X-Title": "Basak Gate"
      },
      secrets: [key]
    };
  } else {
    config = openAIConfig(provider, env);
    if (provider === "kilo") config.model = await chooseKiloToolModel();
  }

  const headers = { "content-type": "application/json", ...config.headers };
  const firstMessages = [{ role: "user", content: PROBE_PROMPT }];
  const first = await fetchJson(config.url, {
    method: "POST",
    headers,
    body: JSON.stringify({
      model: config.model,
      messages: firstMessages,
      tools: [PROBE_TOOL],
      tool_choice: config.mode,
      max_tokens: 4096,
      ...(config.extra || {})
    })
  }, config.secrets);

  const firstMessage = first?.choices?.[0]?.message;
  const call = readToolCall(firstMessage);

  const second = await fetchJson(config.url, {
    method: "POST",
    headers,
    body: JSON.stringify({
      model: config.model,
      messages: [
        ...firstMessages,
        assistantMessage(firstMessage),
        {
          role: "tool",
          tool_call_id: call.id || "protocol_probe",
          content: JSON.stringify({ result: "BASAK_PROTOCOL_OK" })
        }
      ],
      max_tokens: 1024,
      ...(config.extra || {})
    })
  }, config.secrets);

  const finalText = String(second?.choices?.[0]?.message?.content || "").trim();
  if (!finalText) throw new Error("tool sonucu sonrası final cevap gelmedi");

  return {
    ok: true,
    provider,
    model: config.model,
    mode: config.mode,
    toolCall: true,
    toolResultContinuation: true,
    finalPreview: finalText.slice(0, 180)
  };
}

async function runCohereProtocol(env) {
  const key = env.COHERE_API_KEY || "";
  if (!key) throw new Error("sağlayıcı Cloudflare ortamında hazır değil");
  const url = "https://api.cohere.com/v2/chat";
  const headers = { "content-type": "application/json", Authorization: "Bearer " + key };
  const tools = [{
    name: PROBE_TOOL.function.name,
    description: PROBE_TOOL.function.description,
    parameters: PROBE_TOOL.function.parameters
  }];

  const first = await fetchJson(url, {
    method: "POST",
    headers,
    body: JSON.stringify({
      model: "command-a-03-2025",
      messages: [{ role: "user", content: PROBE_PROMPT }],
      tools,
      tool_choice: "REQUIRED",
      max_tokens: 4096
    })
  }, [key]);

  const msg = first?.message;
  const calls = msg?.tool_calls || [];
  if (!Array.isArray(calls) || !calls.length) throw new Error("tool_call üretilmedi");
  const call = calls[0];
  const fn = call?.function || {};
  if (fn.name !== "protokol_probe") throw new Error("yanlış araç çağrıldı");
  let args = fn.arguments || {};
  if (typeof args === "string") {
    try { args = JSON.parse(args); }
    catch { throw new Error("tool arguments geçerli JSON değil"); }
  }
  if (args?.echo !== "BASAK_PROTOCOL_OK") throw new Error("echo doğrulaması başarısız");

  const assistant = { role: "assistant", content: msg?.content || "", tool_calls: calls };
  if (msg?.tool_plan) assistant.tool_plan = msg.tool_plan;

  const second = await fetchJson(url, {
    method: "POST",
    headers,
    body: JSON.stringify({
      model: "command-a-03-2025",
      messages: [
        { role: "user", content: PROBE_PROMPT },
        assistant,
        {
          role: "tool",
          tool_call_id: call.id || "protocol_probe",
          content: [{ type: "document", document: { data: JSON.stringify({ result: "BASAK_PROTOCOL_OK" }) } }]
        }
      ],
      max_tokens: 1024
    })
  }, [key]);

  const blocks = second?.message?.content;
  const finalText = Array.isArray(blocks)
    ? blocks.map((x) => x?.text || "").join("").trim()
    : String(blocks || "").trim();
  if (!finalText) throw new Error("tool sonucu sonrası final cevap gelmedi");

  return {
    ok: true,
    provider: "cohere",
    model: "command-a-03-2025",
    mode: "REQUIRED",
    toolCall: true,
    toolResultContinuation: true,
    finalPreview: finalText.slice(0, 180)
  };
}

export async function runProtocol(provider, env) {
  const started = Date.now();
  try {
    const result = provider === "cohere"
      ? await runCohereProtocol(env)
      : await runOpenAIProtocol(provider, env);
    return { ...result, durationMs: Date.now() - started };
  } catch (error) {
    const secrets = [
      env.GROQ_API_KEY, env.GEMINI_API_KEY, env.OPENROUTER_API_KEY, env.ZAI_API_KEY,
      env.CLOUDFLARE_ACCOUNT_ID, env.CLOUDFLARE_API_TOKEN, env.COHERE_API_KEY,
      env.KILO_API_KEY, env.NVIDIA_API_KEY
    ];
    return {
      ok: false,
      provider,
      model: "-",
      mode: provider === "cohere" ? "REQUIRED" : (["groq","cloudflare","kilo"].includes(provider) ? "required" : "auto"),
      toolCall: false,
      toolResultContinuation: false,
      durationMs: Date.now() - started,
      error: safeError(error?.message || error, secrets)
    };
  }
}

function normalizeMessages(messages) {
  const clean = [];
  for (const m of Array.isArray(messages) ? messages.slice(-20) : []) {
    if (!m || !["user","assistant"].includes(m.role)) continue;
    const content = String(m.content || "").slice(0, 12000).trim();
    if (!content) continue;
    clean.push({ role: m.role, content });
  }
  return clean;
}

async function openAIChat(provider, env, messages) {
  let config;
  if (provider === "openrouter") {
    const key = env.OPENROUTER_API_KEY || "";
    config = {
      url: "https://openrouter.ai/api/v1/chat/completions",
      model: await chooseOpenRouterModel(key),
      headers: {
        Authorization: "Bearer " + key,
        "HTTP-Referer": "https://basak-gate.invalid",
        "X-Title": "Basak Gate"
      },
      secrets: [key]
    };
  } else {
    config = openAIConfig(provider, env);
  }
  const data = await fetchJson(config.url, {
    method: "POST",
    headers: { "content-type": "application/json", ...config.headers },
    body: JSON.stringify({
      model: config.model,
      messages,
      max_tokens: 1536,
      ...(config.extra || {})
    })
  }, config.secrets);
  const text = String(data?.choices?.[0]?.message?.content || "").trim();
  if (!text) throw new Error("boş cevap");
  return { text, provider, model: config.model };
}

async function cohereChat(env, messages) {
  const key = env.COHERE_API_KEY || "";
  const data = await fetchJson("https://api.cohere.com/v2/chat", {
    method: "POST",
    headers: { "content-type": "application/json", Authorization: "Bearer " + key },
    body: JSON.stringify({ model: "command-a-03-2025", messages, max_tokens: 1536 })
  }, [key]);
  const blocks = data?.message?.content;
  const text = Array.isArray(blocks)
    ? blocks.map((x) => x?.text || "").join("").trim()
    : String(blocks || "").trim();
  if (!text) throw new Error("boş cevap");
  return { text, provider: "cohere", model: "command-a-03-2025" };
}

async function workersAIFallback(env, messages) {
  if (!env.AI || typeof env.AI.run !== "function") throw new Error("Workers AI binding yok");
  const response = await env.AI.run("@cf/google/gemma-4-26b-a4b-it", {
    messages,
    max_tokens: 1536,
    chat_template_kwargs: { enable_thinking: false }
  });
  const text = String(response?.response || response?.result?.response || response?.text || "").trim();
  if (!text) throw new Error("Workers AI boş cevap");
  return { text, provider: "cloudflare-binding-fallback", model: "@cf/google/gemma-4-26b-a4b-it" };
}

export async function chat(messages, env) {
  const clean = normalizeMessages(messages);
  if (!clean.length || clean[clean.length - 1].role !== "user") throw new Error("geçerli kullanıcı mesajı yok");

  const status = providerStatus(env);
  const errors = [];
  for (const provider of PROVIDERS) {
    if (!status[provider]) continue;
    try {
      if (provider === "cohere") return await cohereChat(env, clean);
      return await openAIChat(provider, env, clean);
    } catch (error) {
      errors.push(provider + ": " + safeError(error?.message || error));
    }
  }
  try {
    return await workersAIFallback(env, clean);
  } catch (error) {
    errors.push("cloudflare-binding-fallback: " + safeError(error?.message || error));
  }
  throw new Error("Hiçbir ücretsiz sohbet hattı cevap vermedi. " + errors.join(" | ").slice(0, 1200));
}


function sampleValue(schema, name = "value") {
  if (!schema || typeof schema !== "object") return "test";
  if (Array.isArray(schema.enum) && schema.enum.length) return schema.enum[0];
  const type = schema.type;
  if (type === "integer" || type === "number") return 1;
  if (type === "boolean") return true;
  if (type === "array") return [];
  if (type === "object") {
    const out = {};
    const props = schema.properties || {};
    for (const req of schema.required || []) out[req] = sampleValue(props[req] || {}, req);
    return out;
  }
  const n = String(name || "").toLowerCase();
  if (n.includes("url")) return "https://example.com";
  if (n === "site") return "example.com";
  if (n === "proje") return "basak";
  if (n === "aralik") return "gun";
  if (n === "platform") return "vixrex";
  if (n.includes("path")) return "knowledge/test.txt";
  if (n.includes("folder")) return ".";
  if (n === "b64") return "dGVzdA==";
  if (n.includes("dosya")) return "test.json";
  if (n.includes("query") || n.includes("sorgu")) return "Basak protocol test";
  return "test";
}

function sampleArgs(tool) {
  const params = tool?.function?.parameters || { type: "object", properties: {}, required: [] };
  return sampleValue(params, "root");
}

function validateValue(value, schema, path = "args") {
  if (!schema || typeof schema !== "object") return [];
  const errors = [];
  if (Array.isArray(schema.enum) && !schema.enum.includes(value)) errors.push(path + ": enum disi");
  const type = schema.type;
  if (type === "string" && typeof value !== "string") errors.push(path + ": string degil");
  if (type === "integer" && !Number.isInteger(value)) errors.push(path + ": integer degil");
  if (type === "number" && (typeof value !== "number" || !Number.isFinite(value))) errors.push(path + ": number degil");
  if (type === "boolean" && typeof value !== "boolean") errors.push(path + ": boolean degil");
  if (type === "array" && !Array.isArray(value)) errors.push(path + ": array degil");
  if (type === "object") {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      errors.push(path + ": object degil");
    } else {
      for (const req of schema.required || []) {
        if (!(req in value)) errors.push(path + "." + req + ": zorunlu alan yok");
      }
      for (const [key, child] of Object.entries(schema.properties || {})) {
        if (key in value) errors.push(...validateValue(value[key], child, path + "." + key));
      }
    }
  }
  return errors;
}

function genericToolCall(message, tool) {
  const expected = tool?.function?.name;
  const calls = message?.tool_calls || [];
  if (!Array.isArray(calls) || calls.length !== 1) throw new Error("tam bir tool_call bekleniyordu");
  const call = calls[0];
  const fn = call?.function || {};
  if (fn.name !== expected) throw new Error("beklenen arac " + expected + ", gelen " + (fn.name || "bos"));
  let args = fn.arguments || "{}";
  if (typeof args === "string") {
    try { args = JSON.parse(args); }
    catch { throw new Error("tool arguments JSON degil"); }
  }
  const errors = validateValue(args, tool?.function?.parameters || {});
  if (errors.length) throw new Error("schema dogrulamasi: " + errors.slice(0, 5).join("; "));
  return { call, args };
}

function matrixPrompt(tool, target) {
  const name = tool?.function?.name || "tool";
  return [
    "This is a Basak provider-tool matrix acceptance cell.",
    "Call the only available function " + name + " exactly once.",
    "Use harmless synthetic arguments matching its JSON schema.",
    "Target example arguments: " + JSON.stringify(target) + ".",
    "Do not execute a real-world action and do not answer in plain text before the tool call."
  ].join(" ");
}

function matrixConfig(provider, env, model = null) {
  if (provider === "openrouter") {
    const key = env.OPENROUTER_API_KEY || "";
    return {
      url: "https://openrouter.ai/api/v1/chat/completions",
      model: model || "",
      mode: "auto",
      headers: {
        Authorization: "Bearer " + key,
        "HTTP-Referer": "https://basak-gate.invalid",
        "X-Title": "Basak Gate"
      },
      secrets: [key]
    };
  }
  const config = openAIConfig(provider, env);
  if (model) config.model = model;
  return config;
}

async function firstOpenAICell(provider, tool, env) {
  const status = providerStatus(env);
  if (!status[provider]) throw new Error("saglayici Cloudflare ortaminda hazir degil");
  let config;
  if (provider === "openrouter") {
    const key = env.OPENROUTER_API_KEY || "";
    config = matrixConfig(provider, env, await chooseOpenRouterModel(key));
  } else {
    config = matrixConfig(provider, env);
    if (provider === "kilo") config.model = await chooseKiloToolModel();
  }
  const target = sampleArgs(tool);
  const messages = [{ role: "user", content: matrixPrompt(tool, target) }];
  const headers = { "content-type": "application/json", ...config.headers };
  const first = await fetchJson(config.url, {
    method: "POST",
    headers,
    body: JSON.stringify({
      model: config.model,
      messages,
      tools: [tool],
      tool_choice: config.mode,
      max_tokens: 2048,
      ...(config.extra || {})
    })
  }, config.secrets);
  const message = first?.choices?.[0]?.message;
  const parsed = genericToolCall(message, tool);
  return {
    public: {
      ok: true,
      provider,
      tool: tool.function.name,
      model: config.model,
      mode: config.mode,
      argsValid: true
    },
    state: {
      v: 1,
      kind: "openai",
      provider,
      tool: tool.function.name,
      model: config.model,
      messages,
      assistant: assistantMessage(message),
      call: parsed.call
    }
  };
}

async function firstCohereCell(tool, env) {
  const key = env.COHERE_API_KEY || "";
  if (!key) throw new Error("saglayici Cloudflare ortaminda hazir degil");
  const target = sampleArgs(tool);
  const prompt = matrixPrompt(tool, target);
  const ctool = {
    name: tool.function.name,
    description: tool.function.description || "",
    parameters: tool.function.parameters || {}
  };
  const data = await fetchJson("https://api.cohere.com/v2/chat", {
    method: "POST",
    headers: { "content-type": "application/json", Authorization: "Bearer " + key },
    body: JSON.stringify({
      model: "command-a-03-2025",
      messages: [{ role: "user", content: prompt }],
      tools: [ctool],
      tool_choice: "REQUIRED",
      max_tokens: 2048
    })
  }, [key]);
  const msg = data?.message || {};
  const calls = msg.tool_calls || [];
  if (!Array.isArray(calls) || calls.length !== 1) throw new Error("tam bir tool_call bekleniyordu");
  const call = calls[0];
  let args = call?.function?.arguments || {};
  if (typeof args === "string") {
    try { args = JSON.parse(args); }
    catch { throw new Error("tool arguments JSON degil"); }
  }
  if (call?.function?.name !== tool.function.name) throw new Error("yanlis arac cagrildi");
  const errors = validateValue(args, tool.function.parameters || {});
  if (errors.length) throw new Error("schema dogrulamasi: " + errors.slice(0, 5).join("; "));
  const assistant = { role: "assistant", content: msg.content || "", tool_calls: calls };
  if (msg.tool_plan) assistant.tool_plan = msg.tool_plan;
  return {
    public: {
      ok: true,
      provider: "cohere",
      tool: tool.function.name,
      model: "command-a-03-2025",
      mode: "REQUIRED",
      argsValid: true
    },
    state: {
      v: 1,
      kind: "cohere",
      provider: "cohere",
      tool: tool.function.name,
      model: "command-a-03-2025",
      messages: [{ role: "user", content: prompt }],
      assistant,
      call
    }
  };
}

function matrixFailure(provider, tool, error, env, started) {
  const secrets = [
    env.GROQ_API_KEY, env.GEMINI_API_KEY, env.OPENROUTER_API_KEY, env.ZAI_API_KEY,
    env.CLOUDFLARE_ACCOUNT_ID, env.CLOUDFLARE_API_TOKEN, env.COHERE_API_KEY,
    env.KILO_API_KEY, env.NVIDIA_API_KEY
  ];
  const msg = safeError(error?.message || error, secrets);
  return {
    ok: false,
    provider,
    tool: tool?.function?.name || "-",
    blocked: /429|rate|quota|too many/i.test(msg),
    error: msg,
    durationMs: Date.now() - started
  };
}

export async function runToolFirst(provider, tool, env) {
  const started = Date.now();
  try {
    const out = provider === "cohere"
      ? await firstCohereCell(tool, env)
      : await firstOpenAICell(provider, tool, env);
    out.public.durationMs = Date.now() - started;
    return out;
  } catch (error) {
    return { public: matrixFailure(provider, tool, error, env, started), state: null };
  }
}

async function secondOpenAICell(tool, state, env) {
  const config = matrixConfig(state.provider, env, state.model);
  const headers = { "content-type": "application/json", ...config.headers };
  const data = await fetchJson(config.url, {
    method: "POST",
    headers,
    body: JSON.stringify({
      model: state.model,
      messages: [
        ...state.messages,
        state.assistant,
        {
          role: "tool",
          tool_call_id: state.call?.id || "basak_cell",
          content: JSON.stringify({ ok: true, tool: tool.function.name, result: "BASAK_CELL_OK" })
        }
      ],
      max_tokens: 1024,
      ...(config.extra || {})
    })
  }, config.secrets);
  const text = String(data?.choices?.[0]?.message?.content || "").trim();
  if (!text) throw new Error("tool sonucu sonrasi final cevap yok");
  return {
    ok: true,
    provider: state.provider,
    tool: tool.function.name,
    model: state.model,
    continuation: true,
    finalPreview: text.slice(0, 180)
  };
}

async function secondCohereCell(tool, state, env) {
  const key = env.COHERE_API_KEY || "";
  if (!key) throw new Error("saglayici Cloudflare ortaminda hazir degil");
  const data = await fetchJson("https://api.cohere.com/v2/chat", {
    method: "POST",
    headers: { "content-type": "application/json", Authorization: "Bearer " + key },
    body: JSON.stringify({
      model: state.model,
      messages: [
        ...state.messages,
        state.assistant,
        {
          role: "tool",
          tool_call_id: state.call?.id || "basak_cell",
          content: [{
            type: "document",
            document: { data: JSON.stringify({ ok: true, tool: tool.function.name, result: "BASAK_CELL_OK" }) }
          }]
        }
      ],
      max_tokens: 1024
    })
  }, [key]);
  const blocks = data?.message?.content;
  const text = Array.isArray(blocks)
    ? blocks.map((x) => x?.text || "").join("").trim()
    : String(blocks || "").trim();
  if (!text) throw new Error("tool sonucu sonrasi final cevap yok");
  return {
    ok: true,
    provider: "cohere",
    tool: tool.function.name,
    model: state.model,
    continuation: true,
    finalPreview: text.slice(0, 180)
  };
}

export async function runToolSecond(provider, tool, state, env) {
  const started = Date.now();
  try {
    if (!state || state.provider !== provider || state.tool !== tool.function.name) throw new Error("Faz 3 devam durumu bulunamadi");
    const result = provider === "cohere"
      ? await secondCohereCell(tool, state, env)
      : await secondOpenAICell(tool, state, env);
    return { ...result, durationMs: Date.now() - started };
  } catch (error) {
    return matrixFailure(provider, tool, error, env, started);
  }
}


function agentToolChoice(provider) {
  if (provider === "cohere") return "REQUIRED";
  return ["groq","cloudflare","kilo"].includes(provider) ? "required" : "auto";
}

function openAICompatibleMessages(messages) {
  return (messages || []).map((m) => {
    if (!m || typeof m !== "object") return m;
    const out = { ...m };
    if (Array.isArray(out.content)) {
      out.content = out.content.map((x) => x?.text || x?.content || "").join("");
    }
    delete out.tool_plan;
    return out;
  });
}

async function openAIAgentTurn(provider, messages, tools, env) {
  let config;
  if (provider === "openrouter") {
    const key = env.OPENROUTER_API_KEY || "";
    config = {
      url: "https://openrouter.ai/api/v1/chat/completions",
      model: await chooseOpenRouterModel(key),
      headers: {
        Authorization: "Bearer " + key,
        "HTTP-Referer": "https://basak-gate.invalid",
        "X-Title": "Basak Gate"
      },
      secrets: [key],
      extra: {}
    };
  } else {
    config = openAIConfig(provider, env);
    if (provider === "kilo") config.model = await chooseKiloToolModel();
  }

  const mode = agentToolChoice(provider);
  const data = await fetchJson(config.url, {
    method: "POST",
    headers: { "content-type": "application/json", ...config.headers },
    body: JSON.stringify({
      model: config.model,
      messages: openAICompatibleMessages(messages),
      tools,
      tool_choice: mode,
      max_tokens: 2048,
      ...(config.extra || {})
    })
  }, config.secrets);

  const message = data?.choices?.[0]?.message;
  if (!message || !Array.isArray(message.tool_calls) || !message.tool_calls.length) {
    throw new Error("ajan turunda tool_call gelmedi");
  }
  return { message: assistantMessage(message), provider, model: config.model, mode };
}

function cohereMessages(messages) {
  return (messages || []).map((m) => {
    if (!m || typeof m !== "object") return m;
    if (m.role === "tool") {
      const content = Array.isArray(m.content)
        ? m.content
        : [{ type: "document", document: { data: String(m.content || "") } }];
      return { role: "tool", tool_call_id: m.tool_call_id, content };
    }
    const out = { ...m };
    if (Array.isArray(out.content)) {
      out.content = out.content.map((x) => x?.text || "").join("");
    }
    return out;
  });
}

async function cohereAgentTurn(messages, tools, env) {
  const key = env.COHERE_API_KEY || "";
  if (!key) throw new Error("Cohere hazir degil");
  const nativeTools = tools.map((t) => ({
    name: t.function.name,
    description: t.function.description || "",
    parameters: t.function.parameters || {}
  }));
  const data = await fetchJson("https://api.cohere.com/v2/chat", {
    method: "POST",
    headers: { "content-type": "application/json", Authorization: "Bearer " + key },
    body: JSON.stringify({
      model: "command-a-03-2025",
      messages: cohereMessages(messages),
      tools: nativeTools,
      tool_choice: "REQUIRED",
      max_tokens: 2048
    })
  }, [key]);

  const msg = data?.message || {};
  if (!Array.isArray(msg.tool_calls) || !msg.tool_calls.length) {
    throw new Error("ajan turunda tool_call gelmedi");
  }
  const message = { role: "assistant", content: msg.content || "", tool_calls: msg.tool_calls };
  if (msg.tool_plan) message.tool_plan = msg.tool_plan;
  return { message, provider: "cohere", model: "command-a-03-2025", mode: "REQUIRED" };
}

async function workersAIAgentTurn(messages, tools, env) {
  if (!env.AI || typeof env.AI.run !== "function") throw new Error("Workers AI binding yok");
  const data = await env.AI.run("@cf/zai-org/glm-4.7-flash", {
    messages: openAICompatibleMessages(messages),
    tools,
    tool_choice: "required",
    max_tokens: 2048
  });
  const message =
    data?.choices?.[0]?.message ||
    data?.result?.choices?.[0]?.message ||
    data?.message ||
    (Array.isArray(data?.tool_calls)
      ? { role: "assistant", content: data?.response || "", tool_calls: data.tool_calls }
      : null);
  if (!message || !Array.isArray(message.tool_calls) || !message.tool_calls.length) {
    throw new Error("Workers AI ajan turunda tool_call gelmedi");
  }
  return {
    message: assistantMessage(message),
    provider: "cloudflare-binding",
    model: "@cf/zai-org/glm-4.7-flash",
    mode: "required"
  };
}

export async function agentTurn(messages, tools, env) {
  const status = providerStatus(env);
  const errors = [];

  for (const provider of PROVIDERS) {
    if (!status[provider]) continue;
    try {
      if (provider === "cohere") return await cohereAgentTurn(messages, tools, env);
      return await openAIAgentTurn(provider, messages, tools, env);
    } catch (error) {
      errors.push(provider + ": " + safeError(error?.message || error));
    }
  }

  try {
    return await workersAIAgentTurn(messages, tools, env);
  } catch (error) {
    errors.push("cloudflare-binding: " + safeError(error?.message || error));
  }

  throw new Error("Ajan turu icin calisan ucretsiz saglayici yok. " + errors.join(" | ").slice(0, 1500));
}
