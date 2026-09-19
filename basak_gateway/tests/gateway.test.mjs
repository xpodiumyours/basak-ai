import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const root = new URL("../", import.meta.url);
const catalog = JSON.parse(await readFile(new URL("src/tool_catalog.json", root), "utf8"));
const schemas = JSON.parse(await readFile(new URL("src/tool_schemas.json", root), "utf8"));
const providers = await readFile(new URL("src/providers.js", root), "utf8");
const appHtml = await readFile(new URL("public/app/index.html", root), "utf8");
const labHtml = await readFile(new URL("public/lab/index.html", root), "utf8");
const labJs = await readFile(new URL("public/lab.js", root), "utf8");

test("catalog and schemas are exactly 52 tools in 10 areas", () => {
  const names = Object.values(catalog.areas).flat();
  assert.equal(catalog.total, 52);
  assert.equal(names.length, 52);
  assert.equal(new Set(names).size, 52);
  assert.equal(Object.keys(catalog.areas).length, 10);
  assert.equal(schemas.total, 52);
  assert.equal(schemas.tools.length, 52);
});

test("all eight providers are represented", () => {
  for (const name of ["groq","gemini","openrouter","glm","cloudflare","cohere","kilo","nvidia"]) {
    assert.match(providers, new RegExp('"'+name+'"'));
  }
});

test("browser never asks for provider keys", () => {
  for (const html of [appHtml, labHtml]) assert.doesNotMatch(html, /API key|api_key|password/i);
});

test("chat and lab do not use localStorage", async () => {
  const appJs = await readFile(new URL("public/app.js", root), "utf8");
  assert.doesNotMatch(appJs + labJs, /localStorage/i);
});

test("acceptance UI keeps exact 8x52=416 scope", () => {
  assert.match(labJs, /416/);
  assert.match(labHtml, /416 canlı hücre/);
  assert.match(labHtml, /Aşama 4/);
  assert.match(labHtml, /Aşama 5/);
  assert.match(labHtml, /Aşama 6/);
});


test("normal /api/chat is wired to the agent loop", async () => {
  const indexJs = await readFile(new URL("src/index.js", root), "utf8");
  const agentJs = await readFile(new URL("src/agent.js", root), "utf8");
  assert.match(indexJs, /agentChat\(body\?\.messages, env\)/);
  assert.match(agentJs, /yetenek_ac/);
  assert.match(agentJs, /son_cevap/);
  assert.match(agentJs, /executeWebTool/);
});
