import catalog from "./tool_catalog.json" with { type: "json" };
import schemas from "./tool_schemas.json" with { type: "json" };
import { LabState } from "./lab_state.js";
import { PROVIDERS, providerStatus, runProtocol, runToolFirst, runToolSecond } from "./providers.js";
import { agentChat } from "./agent.js";

export { LabState };

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
    areaCount10: Object.keys(areas).length === 10,
    schemas52: schemas?.total === 52 && Array.isArray(schemas?.tools) && schemas.tools.length === 52
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

function validSession(value) {
  return typeof value === "string" && /^[A-Za-z0-9_-]{8,80}$/.test(value);
}

function sessionFrom(url, body = null) {
  return url.searchParams.get("session") || body?.session || "";
}

function labStub(env, session) {
  if (!validSession(session)) throw new Error("gecerli lab session gerekli");
  return env.LAB_STATE.get(env.LAB_STATE.idFromName(session));
}

async function statePut(env, session, key, value) {
  const stub = labStub(env, session);
  const r = await stub.fetch("https://lab/put", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ key, value })
  });
  if (!r.ok) throw new Error("lab state yazilamadi");
}

async function stateGet(env, session, key) {
  const stub = labStub(env, session);
  const r = await stub.fetch("https://lab/get?key=" + encodeURIComponent(key));
  const d = await r.json();
  return d.found ? d.value : null;
}

async function stateStatus(env, session) {
  const r = await labStub(env, session).fetch("https://lab/status");
  if (!r.ok) throw new Error("lab status okunamadi");
  return r.json();
}

function toolByName(name) {
  return (schemas?.tools || []).find((t) => t?.function?.name === name) || null;
}

function publicReport(status) {
  const accepted = status.phase1Passed === 8
    && status.phase2Accepted
    && status.phase3Passed === 416
    && status.phase4Passed === 416
    && status.phase5Accepted;
  return {
    accepted,
    phase1: { passed: status.phase1Passed, total: 8 },
    phase2: { accepted: status.phase2Accepted, totalTools: 52 },
    phase3: { passed: status.phase3Passed, total: 416 },
    phase4: { passed: status.phase4Passed, total: 416 },
    phase5: { accepted: status.phase5Accepted, chatTurns: status.chatTurns },
    phase6: { reportReady: accepted }
  };
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
        stages: ["8 protokol","52 arac yapisi","416 canli hucre","ikinci tur","gercek sohbet","tek kabul raporu"]
      });
    }

    if (request.method === "GET" && url.pathname === "/api/lab/catalog") {
      return json({ total: catalog.total, areas: catalog.areas });
    }

    if (request.method === "GET" && url.pathname === "/api/lab/status") {
      try {
        const session = sessionFrom(url);
        const status = await stateStatus(env, session);
        return json({ ...status, report: publicReport(status) });
      } catch (error) {
        return json({ error: String(error?.message || error) }, 400);
      }
    }

    if (request.method === "POST" && url.pathname.startsWith("/api/lab/phase1/")) {
      const provider = url.pathname.split("/").pop();
      if (!PROVIDERS.includes(provider)) return json({ error: "bilinmeyen provider" }, 404);
      const session = sessionFrom(url);
      const result = await runProtocol(provider, env);
      if (validSession(session)) await statePut(env, session, "r1:" + provider, result);
      return json(result);
    }

    if (request.method === "POST" && url.pathname === "/api/lab/phase2") {
      const body = await request.json().catch(() => ({}));
      const session = sessionFrom(url, body);
      const report = phase2Report();
      if (validSession(session)) await statePut(env, session, "phase2", report);
      return json(report);
    }

    if (request.method === "POST" && url.pathname.startsWith("/api/lab/phase3/")) {
      const parts = url.pathname.split("/").filter(Boolean);
      const provider = parts[3];
      const toolName = parts[4];
      const session = sessionFrom(url);
      if (!PROVIDERS.includes(provider)) return json({ error: "bilinmeyen provider" }, 404);
      const tool = toolByName(toolName);
      if (!tool) return json({ error: "bilinmeyen tool" }, 404);
      try {
        const out = await runToolFirst(provider, tool, env);
        if (validSession(session)) {
          await statePut(env, session, "r3:" + provider + ":" + toolName, out.public);
          if (out.public.ok && out.state) await statePut(env, session, "s3:" + provider + ":" + toolName, out.state);
        }
        return json(out.public);
      } catch (error) {
        return json({ ok: false, provider, tool: toolName, error: String(error?.message || error) }, 500);
      }
    }

    if (request.method === "POST" && url.pathname.startsWith("/api/lab/phase4/")) {
      const parts = url.pathname.split("/").filter(Boolean);
      const provider = parts[3];
      const toolName = parts[4];
      const session = sessionFrom(url);
      if (!PROVIDERS.includes(provider)) return json({ error: "bilinmeyen provider" }, 404);
      const tool = toolByName(toolName);
      if (!tool) return json({ error: "bilinmeyen tool" }, 404);
      try {
        const state = await stateGet(env, session, "s3:" + provider + ":" + toolName);
        const result = await runToolSecond(provider, tool, state, env);
        if (validSession(session)) await statePut(env, session, "r4:" + provider + ":" + toolName, result);
        return json(result);
      } catch (error) {
        return json({ ok: false, provider, tool: toolName, error: String(error?.message || error) }, 500);
      }
    }

    if (request.method === "POST" && url.pathname === "/api/lab/phase5") {
      const body = await request.json().catch(() => ({}));
      const session = sessionFrom(url, body);
      try {
        const status = await stateStatus(env, session);
        if (status.phase4Passed !== 416 || status.chatTurns < 2) {
          return json({ ok: false, error: "Faz 4 tam degil veya en az 2 basarili sohbet turu yok" }, 409);
        }
        const value = { accepted: true, acceptedAt: new Date().toISOString() };
        await statePut(env, session, "phase5", value);
        return json({ ok: true, ...value });
      } catch (error) {
        return json({ ok: false, error: String(error?.message || error) }, 400);
      }
    }

    if (request.method === "GET" && url.pathname === "/api/lab/report") {
      try {
        const status = await stateStatus(env, sessionFrom(url));
        return json({ product: "Basak Gate", generatedAt: new Date().toISOString(), ...publicReport(status) });
      } catch (error) {
        return json({ error: String(error?.message || error) }, 400);
      }
    }

    if (request.method === "POST" && url.pathname === "/api/chat") {
      try {
        const body = await request.json();
        const result = await agentChat(body?.messages, env);
        if (validSession(body?.acceptanceSession)) {
          const current = Number(await stateGet(env, body.acceptanceSession, "chat_turns") || 0);
          await statePut(env, body.acceptanceSession, "chat_turns", current + 1);
        }
        return json({
          ok: true,
          ...result,
          acceptance: false,
          note: "Normal web sohbeti gercek ajan dongusunu kullanir; Faz 5 resmi kabulu laboratuvar oturumunda ayrica verilir."
        });
      } catch (error) {
        return json({ ok: false, error: String(error?.message || error).slice(0, 1400) }, 503);
      }
    }

    if (url.pathname.startsWith("/api/")) return json({ error: "endpoint yok" }, 404);
    return securityHeaders(await env.ASSETS.fetch(request));
  }
};
