"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const root = path.join(__dirname, "..");
const privateScript = fs.readFileSync(path.join(root, "web/private-access.js"), "utf8");
const commonScript = fs.readFileSync(path.join(root, "web/common.js"), "utf8");
const css = fs.readFileSync(path.join(root, "web/chat.css"), "utf8");

async function openPage({ enabled = true, authenticated = false, hash = "", redeem = true,
                           cookieSaved = true, statusFails = false } = {}) {
  const requests = [], dialogs = [], timerCallbacks = [], eventHandlers = {};
  let currentSession = authenticated;
  const location = {
    hash, pathname: "/", search: "", origin: "https://basak-vercel.vercel.app",
    replace(url) { this.replacedWith = url; },
  };
  const history = { replaceState() { location.hash = ""; } };
  const document = {
    documentElement: { dataset: {} },
    body: { append(node) { dialogs.push(node); } },
    querySelectorAll() { return dialogs.filter(node => !node.removed); },
    getElementById() { return null; },
    createElement(tag) {
      return {
        tag, children: [], textContent: "",
        append(...nodes) { this.children.push(...nodes); },
        replaceChildren(...nodes) { this.children = nodes; },
        setAttribute() {}, showModal() { this.open = true; },
        close() { this.open = false; }, remove() { this.removed = true; },
        addEventListener(event, handler) { this["on" + event] = handler; },
      };
    },
  };
  async function fetch(url) {
    requests.push(url);
    if (url === "/api/ozel-erisim/ac") {
      if (redeem && cookieSaved) currentSession = true;
      return {
        ok: redeem,
        json: async () => redeem ? { ok: true } : { error: "Geçersiz bağlantı" },
      };
    }
    if (url === "/api/ozel-erisim") {
      if (statusFails) throw Error("Ağ hatası");
      return { ok: true, json: async () => ({ enabled, authenticated: currentSession, owner: false }) };
    }
    if (url === "/api/kimlik") {
      return {
        ok: true, status: 200,
        json: async () => ({ ok: true, kullanici: "test", basak_id: "test" }),
      };
    }
    return { ok: true, json: async () => ({ ok: true }) };
  }
  const window = {
    addEventListener(event, handler) { eventHandlers[event] = handler; },
    dispatchEvent() {},
  };
  const localStorage = { getItem() { return null; }, setItem() {} };
  class MockAbortController {
    constructor() { this.signal = {}; }
    abort() { this.signal.aborted = true; }
  }
  const context = vm.createContext({
    window, document, fetch, location, history, URLSearchParams, URL, localStorage,
    AbortController: MockAbortController,
    Event: class {}, CustomEvent: class {},
    setTimeout(callback) { timerCallbacks.push(callback); return timerCallbacks.length; },
    clearTimeout() {}, setInterval() {},
  });
  vm.runInContext(privateScript, context);
  vm.runInContext(commonScript, context);
  await window.BasakPrivateAccess.ready;
  await new Promise(resolve => setImmediate(resolve));
  return { requests, dialogs, location, window };
}

test("locked access shows invite instructions without a failed identity request", async () => {
  const page = await openPage();
  assert.ok(page.dialogs.some(node => node.children.some(child => child.textContent === "Başak sana özel")));
  assert.ok(!page.requests.includes("/api/kimlik"));
});

test("an authenticated private session initializes identity", async () => {
  const page = await openPage({ authenticated: true });
  assert.ok(page.requests.includes("/api/kimlik"));
});

test("public mode remains available without a private invitation", async () => {
  const page = await openPage({ enabled: false });
  assert.ok(page.requests.includes("/api/kimlik"));
});

test("a valid invitation checks the mobile session before reloading", async () => {
  const page = await openPage({ hash: "#davet=" + "x".repeat(43) });
  assert.equal(page.location.replacedWith, "/");
  assert.equal(page.requests.filter(p => p === "/api/ozel-erisim").length, 1);
  assert.ok(!page.requests.includes("/api/kimlik"));
});

test("invalid invitations cannot start a guest identity", async () => {
  const page = await openPage({ hash: "#davet=" + "x".repeat(43), redeem: false });
  assert.equal(page.location.replacedWith, undefined);
  assert.ok(!page.requests.includes("/api/kimlik"));
});

test("blocked cookies stop redirect loops on mobile browsers", async () => {
  const page = await openPage({ hash: "#davet=" + "x".repeat(43), cookieSaved: false });
  assert.equal(page.location.replacedWith, undefined);
  assert.ok(page.dialogs.some(node => node.children.some(child =>
    String(child.textContent).includes("Oturum doğrulanamadı"))));
});

test("private access API errors fail closed and show a retry instruction", async () => {
  const page = await openPage({ statusFails: true });
  assert.ok(!page.requests.includes("/api/kimlik"));
  assert.ok(page.dialogs.some(node => node.children.some(child =>
    String(child.textContent).includes("Bağlantını kontrol"))));
});

test("private dialog has narrow mobile width and non-zooming text inputs", () => {
  assert.match(css, /\.private-dialog\{width:calc\(100vw - 24px\)/);
  assert.match(css, /\.private-dialog input\{font-size:16px/);
});
