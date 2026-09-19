import catalog from "./tool_catalog.json" with { type: "json" };
import { PROVIDERS, providerStatus, runProtocol, chat } from "./providers.js";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff",
      "referrer-policy": "no-referrer"
    }
  });
}

function phase2Report() {
  const areas = catalog?.areas || {};
  const names = Object.values(areas).flat();
  const unique = new Set(names);
  const checks = {
    declaredTotal52: catalog?.total === 52,
    actualTotal52: names.length === 52,
    unique52: unique.size === 52,
    areaCount10: Object.keys(areas).length === 10
  };
  return {
    phase: 2,
    accepted: Object.values(checks).every(Boolean),
    checks,
    total: names.length,
    unique: unique.size,
    areas: Object.fromEntries(Object.entries(areas).map(([k, v]) => [k, v.length]))
  };
}

function securityHeaders(response) {
  const out = new Response(response.body, response);
  out.headers.set("x-content-type-options", "nosniff");
  out.headers.set("referrer-policy", "no-referrer");
  out.headers.set("permissions-policy", "camera=(), microphone=(), geolocation=()");
  if ((out.headers.get("content-type") || "").includes("text/html")) {
    out.headers.set(
      "content-security-policy",
      "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    );
  }
  return out;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/api/health") {
      return json({
        ok: true,
        product: "Basak Gate",
        mode: "free-only",
        providerReady: providerStatus(env),
        providers: PROVIDERS,
        workersAiBinding: Boolean(env.AI),
        stages: [
          "8 protokol",
          "52 arac yapisi",
          "416 canli hucre",
          "ikinci tur",
          "gercek sohbet",
          "tek kabul raporu"
        ]
      });
    }

    if (request.method === "POST" && url.pathname.startsWith("/api/lab/phase1/")) {
      const provider = url.pathname.split("/").pop();
      if (!PROVIDERS.includes(provider)) return json({ error: "bilinmeyen provider" }, 404);
      return json(await runProtocol(provider, env));
    }

    if (request.method === "POST" && url.pathname === "/api/lab/phase2") {
      return json(phase2Report());
    }

    if (request.method === "POST" && url.pathname === "/api/chat") {
      try {
        const body = await request.json();
        const result = await chat(body?.messages, env);
        return json({
          ok: true,
          ...result,
          acceptance: false,
          note: "Bu ekran keşif sohbetidir; Faz 5 kabul kaniti sayilmaz."
        });
      } catch (error) {
        return json({ ok: false, error: String(error?.message || error).slice(0, 1400) }, 503);
      }
    }

    if (url.pathname.startsWith("/api/")) {
      return json({ error: "endpoint yok" }, 404);
    }

    const assetResponse = await env.ASSETS.fetch(request);
    return securityHeaders(assetResponse);
  }
};
