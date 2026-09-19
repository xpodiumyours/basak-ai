import test from "node:test";
import assert from "node:assert/strict";
import { agentChat, executeWebTool } from "../src/agent.js";

function call(name, args, id = "c1") {
  return {
    id,
    type: "function",
    function: { name, arguments: JSON.stringify(args || {}) }
  };
}

test("salt sohbet gercek arac kosmadan son_cevap ile biter", async () => {
  const fake = async () => ({
    provider: "fake",
    model: "fake",
    message: {
      role: "assistant",
      content: "",
      tool_calls: [call("son_cevap", { metin: "Merhaba." })]
    }
  });

  const r = await agentChat([{ role: "user", content: "Merhaba" }], {}, fake);
  assert.equal(r.text, "Merhaba.");
  assert.deepEqual(r.toolsUsed, []);
});

test("normal sohbet yetenek_ac -> simdi -> son_cevap zincirini gercek calistirir", async () => {
  let step = 0;
  const fake = async (messages, tools) => {
    step++;
    const names = tools.map((t) => t.function.name);

    if (step === 1) {
      assert.deepEqual(names, ["yetenek_ac", "son_cevap"]);
      return {
        provider: "fake",
        model: "fake",
        message: {
          role: "assistant",
          content: "",
          tool_calls: [call("yetenek_ac", { alan: "gorevler" }, "a1")]
        }
      };
    }

    if (step === 2) {
      assert.ok(names.includes("simdi"));
      return {
        provider: "fake",
        model: "fake",
        message: {
          role: "assistant",
          content: "",
          tool_calls: [call("simdi", {}, "a2")]
        }
      };
    }

    const toolResult = messages.filter((m) => m.role === "tool").at(-1)?.content || "";
    assert.match(toolResult, /Europe\/Istanbul/);

    return {
      provider: "fake",
      model: "fake",
      message: {
        role: "assistant",
        content: "",
        tool_calls: [call("son_cevap", { metin: "Saat aracla okundu." }, "a3")]
      }
    };
  };

  const r = await agentChat(
    [{ role: "user", content: "İstanbul'da saat kaç?" }],
    {},
    fake
  );

  assert.equal(r.text, "Saat aracla okundu.");
  assert.deepEqual(r.toolsUsed, ["simdi"]);
});

test("hesapla web aracinin sonucu gercek hesaplanir", async () => {
  const r = await executeWebTool("hesapla", { ifade: "(120*18)/100" });
  assert.equal(r.result, 21.6);
});

test("masaustu/dosya araci bagli degilse yapilmis gibi sayilmaz", async () => {
  const r = await executeWebTool("read_file", { path: "x.txt" });
  assert.ok(r.error);
  assert.equal(r.bridge_required, true);
});
