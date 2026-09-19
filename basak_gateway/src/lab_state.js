import { DurableObject } from "cloudflare:workers";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }
  });
}

export class LabState extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.ctx = ctx;
  }

  async fetch(request) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/put") {
      const body = await request.json();
      if (!body?.key) return json({ error: "key gerekli" }, 400);
      await this.ctx.storage.put(String(body.key), body.value);
      await this.ctx.storage.setAlarm(Date.now() + 24 * 60 * 60 * 1000);
      return json({ ok: true });
    }
    if (request.method === "GET" && url.pathname === "/get") {
      const key = url.searchParams.get("key");
      if (!key) return json({ error: "key gerekli" }, 400);
      const value = await this.ctx.storage.get(key);
      return json({ found: value !== undefined, value: value ?? null });
    }
    if (request.method === "GET" && url.pathname === "/status") {
      const [r1, r3, r4, phase2] = await Promise.all([
        this.ctx.storage.list({ prefix: "r1:" }),
        this.ctx.storage.list({ prefix: "r3:" }),
        this.ctx.storage.list({ prefix: "r4:" }),
        this.ctx.storage.get("phase2")
      ]);
      const okKeys = (map) => [...map.entries()].filter(([,v]) => v?.ok).map(([k]) => k);
      return json({
        phase1Passed: okKeys(r1).length,
        phase1PassedKeys: okKeys(r1),
        phase2Accepted: Boolean(phase2?.accepted),
        phase3Passed: okKeys(r3).length,
        phase3PassedKeys: okKeys(r3),
        phase4Passed: okKeys(r4).length,
        phase4PassedKeys: okKeys(r4)
      });
    }
    if (request.method === "POST" && url.pathname === "/clear") {
      await this.ctx.storage.deleteAll();
      return json({ ok: true });
    }
    return json({ error: "state endpoint yok" }, 404);
  }

  async alarm() {
    await this.ctx.storage.deleteAll();
  }
}
