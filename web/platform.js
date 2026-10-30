// Başak çalışma alanı. Yalnız kalıcı sunucu durumunu gösterir; ajan çalıştırmaz.
// Reference: https://www.kimi.com/code/docs/en/kimi-code-desktop/task-execution-and-review.html
(function (scope) {
  "use strict";
  const STATUS = Object.freeze({
    queued: "Sırada", running: "Çalışıyor", waiting_children: "Alt ajanlar bekleniyor",
    awaiting_approval: "Onay bekliyor",
    awaiting_connection: "Bağlantı bekliyor", paused: "Duraklatıldı",
    verifying: "Doğrulanıyor", completed: "Tamamlandı", partial: "Kısmi",
    blocked: "Engellendi", failed: "Başarısız", cancelled: "İptal edildi",
    uncertain: "Sonuç belirsiz",
  });
  const TERMINAL = new Set(["completed", "partial", "blocked", "failed", "cancelled", "uncertain"]);
  const ACTIONS = new Set(["iptal", "devam", "yon", "onay", "kabul", "uzlastir"]);

  function workArtifact(artifact) { return artifact.id !== "answer" && artifact.kind !== "answer"; }

  // Protocol bookkeeping is retained on the server, but is not user work.
  function activityEvent(event) {
    const p = event.payload || {};
    const tool = p.tool || p.arac || p.ad;
    if (["yetenek_ac", "son_cevap"].includes(tool)) return false;
    if (event.type === "chat") return ["toolStart", "toolDone", "arac"].includes(p.tur);
    if (event.type === "artifact") return workArtifact(p.artifact || p);
    if (event.type === "check") return (p.check || p).id !== "response_recorded";
    return ["tool_started", "tool_done", "approval", "steering"].includes(event.type);
  }

  function hasWork(run) {
    if (!run) return false;
    return !!(run.has_work || (run.kind && run.kind !== "chat") ||
      run.children?.length || run.artifacts?.some(workArtifact) ||
      run.approvals?.some(a => a.status === "pending") ||
      ["awaiting_approval", "awaiting_connection", "uncertain"].includes(run.durum));
  }

  function eventTime(value) {
    if (value == null || value === "") return "";
    const numeric = Number(value);
    const date = new Date(Number.isFinite(numeric) ?
      (Math.abs(numeric) < 1e12 ? numeric * 1000 : numeric) : value);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleTimeString("tr-TR");
  }

  async function observeRun(id, read, signal, wait) {
    const terminal = new Set([...TERMINAL, "verifying", "awaiting_approval", "awaiting_connection", "paused"]);
    const delay = wait || (() => new Promise(resolve => setTimeout(resolve, 1000)));
    while (true) {
      if (signal?.aborted) throw new DOMException("İzleme durduruldu", "AbortError");
      const data = await read("/api/kosu/" + encodeURIComponent(id) + "/agac", signal);
      if (signal?.aborted) throw new DOMException("İzleme durduruldu", "AbortError");
      const run = data.kosu;
      if (!run || run.id !== id) throw new Error("Kayıtlı çalışma okunamadı.");
      if (terminal.has(run.durum)) {
        if (run.answer) return {istek: id, tur: "bitir", cevap: run.answer, kaynak: run.provider || ""};
        if (TERMINAL.has(run.durum)) return {istek: id, tur: "error", metin: run.hata || statusText(run.durum)};
        return {istek: id, tur: "checkpoint", kosu_id: id};
      }
      await delay();
    }
  }

  function createState(principal) {
    return { principal: String(principal || ""), user: null, runs: {}, selectedId: null,
      cursor: 0, log: [], connections: [], providers: [] };
  }

  function identity(state, user) {
    const principal = String(user && user.id || "");
    const next = principal === state.principal ? { ...state } : createState(principal);
    next.user = user || null;
    return next;
  }

  function snapshot(state, root) {
    if (!root || !(root.id || root.kosu_id)) return state;
    const id = String(root.id || root.kosu_id);
    const next = { ...state, runs: { ...state.runs } };
    function walk(run) {
      const key = String(run.id || run.kosu_id || "");
      if (!key) return;
      next.runs[key] = { ...run, id: key, children: run.children || [],
        artifacts: run.artifacts || [], checks: run.checks || [], approvals: run.approvals || [] };
      for (const child of run.children || []) walk(child);
    }
    walk(root);
    if (state.selectedId !== id) {
      next.selectedId = id;
      next.cursor = 0;
      next.log = [];
    }
    return next;
  }

  function events(state, incoming) {
    const next = { ...state, runs: { ...state.runs }, log: state.log.slice() };
    for (const event of (incoming || []).slice().sort((a, b) => Number(a.seq) - Number(b.seq))) {
      const seq = Number(event.seq);
      if (!Number.isSafeInteger(seq) || seq <= next.cursor) continue;
      const payload = event.payload && typeof event.payload === "object" ? event.payload : {};
      const id = String(payload.origin_run_id || event.run_id || next.selectedId || "");
      const previous = next.runs[id] || { id, children: [], artifacts: [], checks: [], approvals: [] };
      const run = { ...previous };
      if (event.type === "status") run.durum = payload.durum || payload.status || run.durum;
      if (event.type === "model" || event.type === "provider") {
        run.model_ref = payload.model_ref || payload.model || run.model_ref;
        run.provider = payload.provider || payload.saglayici || run.provider;
      }
      if (event.type === "artifact" || event.type === "check" || event.type === "approval") {
        const field = { artifact: "artifacts", check: "checks", approval: "approvals" }[event.type];
        const item = payload[event.type] || payload;
        const list = (run[field] || []).slice();
        const index = list.findIndex((old) => old.id && old.id === item.id);
        if (index < 0) list.push(item); else list[index] = { ...list[index], ...item };
        run[field] = list;
      }
      next.runs[id] = run;
      next.log.push(event);
      next.cursor = seq;
    }
    return next;
  }

  function statusText(value) { return STATUS[value] || "Durum alınamadı"; }

  function mergeMessages(saved, local) {
    saved = Array.isArray(saved) ? saved : [];
    local = Array.isArray(local) ? local : [];
    let shared = 0;
    while (shared < saved.length && shared < local.length &&
        saved[shared].role === local[shared].role && saved[shared].content === local[shared].content) shared++;
    // Legacy turns written while the worker was offline are still local.
    // A server refresh must not erase them or duplicate a newer durable answer.
    if (shared === saved.length) return local.slice();
    if (shared === local.length) return saved.slice();
    const remaining = local.slice(shared);
    if (remaining[0]?.role === 'assistant' && saved[shared]?.role === 'assistant') remaining.shift();
    return saved.concat(remaining);
  }

  // Derived exclusively from persisted task snapshots; never invent progress.
  function childProgress(run) {
    const children = (run && run.children) || [];
    const counts = { total: children.length, completed: 0, running: 0, failed: 0, pending: 0 };
    for (const child of children) {
      if (child.durum === "completed") counts.completed++;
      else if (child.durum === "running") counts.running++;
      else if (TERMINAL.has(child.durum)) counts.failed++;
      else counts.pending++;
    }
    return counts;
  }

  function workerStatusText(health) {
    if (!health || !health.online) return "Ajan işçisi çevrimdışı · görevler sırada bekler";
    const n = Number(health.live_workers) || 0;
    return "Ajan işçisi çevrimiçi · " + n + " çalışan";
  }

  function approvalDetails(approval) {
    const preview = approval && approval.preview || {};
    const titles = { repository: "Depo", branch: "Dal", path: "Dosya",
      workflow: "İş akışı", ref: "Referans", document_id: "Belge",
      spreadsheet_id: "Tablo", page_id: "Sayfa", block_id: "Blok",
      file_id: "Dosya kimliği", range: "Hücre aralığı", session_id: "Tarayıcı oturumu",
      data_source_id: "Veri kaynağı" };
    const targets = preview.target || {};
    const fields = Object.keys(titles).filter(k => typeof targets[k] === "string")
      .map(k => titles[k] + ": " + targets[k]);
    if (typeof preview.operation === "string" && preview.operation) fields.unshift("İşlem: " + preview.operation);
    return fields.join(" · ") || "İşlem ayrıntısı kayıtlı değil; onay öncesi hedefi doğrula";
  }

  function evidenceText(check) {
    const data = check && check.evidence;
    if (!data || typeof data !== "object" || Array.isArray(data)) return String(check.id || "Kabul kontrolü");
    const detail = [];
    if (data.verified === true) detail.push("Tarayıcı doğrulandı");
    if (typeof data.exit_code === "number") detail.push("Çıkış kodu " + data.exit_code);
    if (typeof data.sha256 === "string") detail.push("SHA-256 " + data.sha256.slice(0, 12));
    if (data.missing === true) detail.push("Kanıt bulunamadı");
    if (data.unsupported_validator) detail.push("Bilinmeyen doğrulama türü");
    return String(check.id || "Kabul kontrolü") + (detail.length ? " · " + detail.join(" · ") : "");
  }

  function safeHref(value, origin) {
    if (!value) return null;
    try {
      const url = new URL(String(value), origin);
      if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) return null;
      for (const key of url.searchParams.keys()) {
        if (/token|secret|password|api[-_]?key|authorization/i.test(key)) return null;
      }
      return url.href;
    } catch { return null; }
  }

  function previewHref(value, origin) {
    const href = safeHref(value, origin);
    if (!href) return null;
    const url = new URL(href);
    return url.origin === origin && url.pathname.startsWith("/api/kosu/") ? href : null;
  }

  function createClient(fetcher) {
    async function request(path, options) {
      const response = await fetcher(path, { credentials: "same-origin", cache: "no-store", ...options });
      const data = response.status === 204 ? {} : await response.json().catch(() => ({}));
      if (!response.ok) {
        const error = new Error(data.error || data.detail || "İstek tamamlanamadı (" + response.status + ").");
        error.status = response.status;
        throw error;
      }
      return data;
    }
    return {
      read: (path) => request(path),
      write: (path, data, method, requestKey) => request(path, { method: method || "POST",
        headers: { "Content-Type": "application/json", ...(requestKey ? {'Idempotency-Key': requestKey} : {}) }, body: JSON.stringify(data || {}) }),
      action(id, action, data) {
        if (!ACTIONS.has(action)) return Promise.reject(new Error("Geçersiz görev işlemi."));
        return request("/api/kosu/" + encodeURIComponent(id) + "/" + action, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data || {}),
        });
      },
    };
  }

  const exported = { createState, identity, snapshot, events, statusText, mergeMessages,
    childProgress, evidenceText, approvalDetails, workerStatusText, hasWork, activityEvent, eventTime, observeRun,
    safeHref, previewHref, createClient };
  if (typeof module !== "undefined" && module.exports) module.exports = exported;
  if (!scope.document) return;
  scope.BasakWorkspace = exported;

  const document = scope.document;
  const byId = (id) => document.getElementById(id);
  if (!byId("platformRunTree")) return;
  const client = createClient(scope.fetch.bind(scope));
  let state = createState("");
  let revision = 0;
  let polling = false;
  let selectionVersion = 0;
  let previewKind = "outputs";
  let selectedArtifact = null;
  let busy = false;
  let pendingChatSubmission = null;
  const expandedEvents = new Set();
  const originalFetch = scope.basakFetch;
  if (typeof originalFetch === 'function') {
    scope.basakFetch = async function (path, options = {}) {
      if (path !== '/api/sohbet') return originalFetch(path, options);
      if (scope.basakKimlikHazir) await scope.basakKimlikHazir;
      const userId=state.user?.id || scope.basakKimlik?.kullanici;
      if (!userId || scope.basakLegacyBridge) return originalFetch(path, options);
      const signature = userId + ':' + String(options.body || '');
      const previous = pendingChatSubmission && state.runs[pendingChatSubmission.run];
      if (!pendingChatSubmission || pendingChatSubmission.signature !== signature ||
          (previous && TERMINAL.has(previous.durum))) {
        pendingChatSubmission = {signature, key: scope.crypto.randomUUID(), run: null};
      }
      const headers = new Headers(options.headers || {});
      headers.set('Idempotency-Key', pendingChatSubmission.key);
      const response = await originalFetch(path, {...options, headers});
      const run = response.headers.get('X-Basak-Run-ID');
      if (run) pendingChatSubmission.run = run;
      return response;
    };
  }
  const durableChats = new Set();
  let selectedConversation = null;
  scope.addEventListener('basak:conversation', ({detail}) => {
    selectedConversation = detail;
    const id = detail?.runs?.at(-1)?.id;
    if (id && state.user && state.selectedId !== id) selectRun(id, false).catch(handleError);
    else if (!id) {
      selectionVersion += 1; state.selectedId = null; state.log = []; state.cursor = 0;
      renderRunTree(); renderEvents(); renderPreview();
    }
  });
  scope.addEventListener('basak:durable-run', ({detail: event}) => {
    durableChats.add(event.istek);
    if (state.selectedId !== event.kosu_id) selectRun(event.kosu_id, false).catch(handleError);
  });
  scope.addEventListener('basak:open-task', ({detail}) => {
    selectRun(detail.id).then(() => switchView('tasks')).catch(handleError);
  });
    document.addEventListener('click', (event) => {
      const action = event.target.closest('.work-stop,.work-redirect,.work-continue,.work-answer');
      const row = action && action.closest('[data-durable-run]');
      if (!row) return;
      event.preventDefault(); event.stopImmediatePropagation();
      const id = row.dataset.durableRun;
      if (action.classList.contains('work-stop')) perform(id, 'iptal', {});
      else selectRun(id).then(() => switchView('tasks')).catch(handleError);
    }, true);

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = String(text);
    return element;
  }

  function message(text, error) {
    const element = byId("platformMessage");
    element.textContent = text || "";
    element.classList.toggle("is-error", !!error);
    const notice = byId("workspaceNotice");
    notice.textContent = text || "";
    notice.classList.toggle("is-error", !!error);
  }

  function switchView() {
    byId("platformTaskView").hidden = !hasWork(currentRun());
    const chat = document.querySelector(".chat-main");
    if (chat) chat.hidden = false;
  }

  function showPreview(open) {
    const compact = scope.matchMedia("(max-width: 1100px)").matches;
    byId("workspacePreview").hidden = !open;
    byId("workspaceToggle").setAttribute("aria-expanded", String(open));
    document.querySelector(".app-shell").classList.toggle("workspace-open", open);
    byId("workspaceBackdrop").hidden = !open || !compact;
    document.querySelector(".main-panel").inert = open && compact;
    byId("sidebar").inert = open && compact;
    if (open && compact) {
      byId("workspacePreview").setAttribute("role", "dialog");
      byId("workspacePreview").setAttribute("aria-modal", "true");
    } else {
      byId("workspacePreview").removeAttribute("role");
      byId("workspacePreview").removeAttribute("aria-modal");
    }
    if (open) byId("workspaceClose").focus();
    else {
      const toggle = byId("workspaceToggle");
      (toggle.getBoundingClientRect().right > 0 ? toggle : byId("sidebarToggle")).focus();
    }
  }

  function accountRequired() {
    if (state.user) return false;
    message("Bulut görevleri ve bağlantılar için sana verilen özel bağlantıyı aç.", false);
    previewKind = "connections";
    renderPreview();
    showPreview(true);
    return true;
  }

  function handleError(error) {
    if (error.status === 401) {
      state = identity(state, null);
      revision += 1;
      render();
    }
    message(error.message, true);
  }

  function currentRun() { return state.runs[state.selectedId] || null; }

  function renderAccount() {
    const container = byId("platformAccount");
    container.replaceChildren();
    if (state.user) {
      container.append(node("strong", "workspace-account-name", state.user.name || "Hesabım"));
      const logout = node("button", "workspace-text-button", "Çıkış yap");
      logout.type = "button";
      logout.addEventListener("click", async () => {
        logout.disabled = true;
        try {
          await client.write("/api/hesap/cikis", {});
          state = identity(state, null);
          revision += 1;
          selectedArtifact = null;
          durableChats.clear(); pendingChatSubmission = null;
          render();
          scope.dispatchEvent(new CustomEvent("basak:platform-account", { detail: null }));
          scope.location.reload(); // Reload chat/history under the new anonymous identity.
        } catch (error) { handleError(error); }
        finally { logout.disabled = false; }
      });
      container.append(logout);
    } else {
      container.append(node("span", "workspace-muted", "Kişisel çalışma alanı"));
      const button = node("button", "workspace-text-button", "Özel bağlantınla aç");
      button.type = "button";
      button.addEventListener("click", () => {
        if (scope.BasakPrivateAccess) scope.BasakPrivateAccess.openHelp();
        else { previewKind = "connections"; renderPreview(); showPreview(true); }
      });
      container.append(button);
    }
    if (scope.BasakPrivateAccess) scope.BasakPrivateAccess.decorate(container);
  }
  scope.addEventListener("basak:private-ready", renderAccount);

  function renderTaskList() {
    const list = byId("platformTaskList");
    list.replaceChildren();
    const roots = Object.values(state.runs).filter((run) => !run.parent_id && run.kind !== "chat");
    list.closest(".workspace-task-sidebar").hidden = !roots.length;
    byId("platformTaskEmpty").hidden = roots.length > 0;
    byId("platformTaskEmpty").textContent = state.user ? "Henüz bulut görevi yok." : "Görevlerini görmek için özel bağlantını aç.";
    for (const run of roots) {
      const button = node("button", "workspace-task-link");
      button.type = "button";
      button.setAttribute("aria-current", String(state.selectedId === run.id));
      button.append(node("span", "workspace-task-title", run.istek || "Çalışma"));
      button.append(node("small", "workspace-task-status", statusText(run.durum)));
      button.addEventListener("click", () => selectRun(run.id));
      list.append(button);
    }
  }

  function renderRunTree() {
    const root = currentRun();
    switchView();
    const container = byId("platformRunTree");
    container.replaceChildren();
    byId("platformRunHeader").hidden = !root;
    byId("platformSteerForm").hidden = !root || TERMINAL.has(root.durum);
    if (!root) return;
    byId("platformRunTitle").textContent = root.istek || "Görev";
    const status = byId("platformRunStatus");
    status.textContent = statusText(root.durum);
    status.dataset.status = root.durum || "unknown";
    byId("platformCancel").disabled = busy || TERMINAL.has(root.durum);
    byId("platformCancel").hidden = TERMINAL.has(root.durum);
    byId("platformResume").hidden = !["paused", "blocked", "awaiting_connection", "partial", "failed", "verifying"].includes(root.durum);
    byId("platformResume").disabled = busy;
    const progress = childProgress(root);
    if (progress.total) {
      container.append(node("p", "workspace-muted",
        "Alt ajanlar · " + progress.completed + "/" + progress.total + " tamamlandı · " +
        progress.running + " çalışıyor · " + progress.pending + " bekliyor · " +
        progress.failed + " başarısız/kısmi"));
    }
    const visited = new Set();
    function draw(run, depth) {
      if (!run || visited.has(run.id)) return;
      visited.add(run.id);
      const row = node("article", "workspace-run-row" + (depth ? " is-child" : ""));
      row.style.setProperty("--depth", String(depth));
      row.append(node("strong", "", depth ? run.istek || "Alt görev" : "Başak · ana görev"));
      const badge = node("span", "workspace-status", statusText(run.durum));
      badge.dataset.status = run.durum || "unknown";
      row.append(badge);
      const model = [run.model_ref, run.provider].filter(Boolean).join(" · ");
      if (model) row.append(node("small", "workspace-muted", model));
      if (run.hata || run.reason || run.blocked_reason) row.append(node("p", "workspace-run-reason", run.hata || run.reason || run.blocked_reason));
      for (const check of run.checks || []) {
        if (check.id === "response_recorded") continue;
        row.append(node("p", "workspace-check", (check.ok === true ? "Geçti: " : "Geçmedi: ") + evidenceText(check)));
      }
      if (depth && run.answer) row.append(node('pre', 'workspace-code', run.answer));
      const activity = state.log.filter(event =>
        (event.payload?.origin_run_id || event.run_id) === run.id &&
        ['tool_started', 'tool_done', 'chat'].includes(event.type));
      const tools = activity.filter(event => activityEvent(event) && (event.type !== 'chat' ||
        ['toolStart', 'toolDone', 'arac'].includes(event.payload?.tur)));
      if (tools.length) {
        const detail = node('details', 'workspace-agent-tools');
        detail.append(node('summary', '', 'Araç işlemleri · ' + tools.length));
        for (const event of tools) {
          detail.append(node('p', 'workspace-run-reason', eventLabel(event)));
        }
        row.append(detail);
      }
      for (const artifact of run.artifacts || []) {
        if (!workArtifact(artifact)) continue;
        const button = node('button', 'workspace-button workspace-file', artifact.title || 'Dosya');
        button.type = 'button';
        button.addEventListener('click', () => {
          selectedArtifact = artifact.id; previewKind = 'outputs'; renderPreview(); showPreview(true);
        });
        row.append(button);
      }
      if (run.durum === 'uncertain') {
        const button = node('button', 'workspace-button', 'İşlemi kanıtla uzlaştır');
        button.type = 'button';
        button.addEventListener('click', () => reconcileRun(run.id, row));
        row.append(button);
      }
      for (const approval of run.approvals || []) {
        if (approval.status !== "pending") continue;
        const box = node("div", "workspace-approval");
        box.append(node("p", "", "Onay: " + (approval.action || "İşlem") + " · " + (approval.resource || "")));
        box.append(node("p", "workspace-muted", approvalDetails(approval)));
        box.append(node("small", "workspace-muted", "İşlem özeti: " + String(approval.arguments_digest || "").slice(0, 16)));
        for (const approved of [true, false]) {
          const button = node("button", "workspace-button", approved ? "Bu işlemi onayla" : "Reddet");
          button.type = "button";
          button.disabled = busy;
          button.addEventListener("click", () => perform(run.id, "onay", { approval_id: approval.id, approved }));
          box.append(button);
        }
        row.append(box);
      }
      if (["verifying", "partial"].includes(run.durum)) {
        for (const condition of run.acceptance || []) {
          if ((condition.kind || "human") !== "human") continue;
          const box = node("div", "workspace-approval");
          box.append(node("p", "", "Sonucu değerlendir: " + (condition.description || condition.id || "Görev sonucu")));
          for (const accepted of [true, false]) {
            const button = node("button", "workspace-button", accepted ? "Bu sonucu kabul et" : "Düzeltme gerekli");
            button.type = "button"; button.disabled = busy;
            button.addEventListener("click", () => perform(run.id, "kabul", { check_id: condition.id, accepted }));
            box.append(button);
          }
          row.append(box);
        }
      }
      container.append(row);
      for (const child of run.children || []) draw(state.runs[child.id || child.kosu_id] || child, depth + 1);
    }
    draw(root, 0);
  }

  async function reconcileRun(id, row) {
    try {
      const data = await client.read('/api/kosu/' + encodeURIComponent(id) + '/islemler');
      for (const action of (data.actions || []).filter((item) => item.status === 'uncertain')) {
        const box = node('div', 'workspace-reconcile');
        box.append(node('p', '', action.tool + ' · ' + action.call_id));
        box.append(node('p', '', 'İşlemin hedefi bağlı sağlayıcıdan yeniden okunur. Sonuç doğrulanamazsa görev belirsiz kalır.'));
        const button = node('button', 'workspace-button', 'Sağlayıcıdan doğrula');
        button.type = 'button';
        button.addEventListener('click', () => perform(id, 'uzlastir', {call_id: action.call_id}));
        box.append(button); row.append(box);
      }
    } catch (error) { handleError(error); }
  }

  function eventLabel(event) {
    const payload = event.payload || {};
    const labels = { steering: "Yeni yön alındı", approval: "Onay durumu", artifact: "Çıktı kaydedildi",
      check: "Kabul kontrolü", tool_started: "Araç çalışıyor", tool_done: "Araç sonucu",
      model: "Model", provider: "Sağlayıcı", status: "Durum", chat: "Araç işlemi" };
    return (labels[event.type] || event.type || "Olay") + " · " + (
      payload.durum ? statusText(payload.durum) : payload.tool || payload.arac || payload.ad || payload.title || payload.model_ref || payload.provider || "");
  }

  function renderEvents() {
    const container = byId("platformEvents");
    const wasBottom = container.scrollHeight - container.clientHeight - container.scrollTop < 40;
    container.replaceChildren();
    if (!state.log.length) {
      container.append(node("p", "workspace-muted", currentRun() ? "Görev olayları bekleniyor." : "Bir görev seçtiğinde çalışma adımları burada görünür."));
      return;
    }
    for (const event of state.log.filter(activityEvent)) {
      const entry = node("details", "workspace-event");
      entry.open = expandedEvents.has(event.seq);
      entry.addEventListener("toggle", () => {
        if (entry.open) expandedEvents.add(event.seq); else expandedEvents.delete(event.seq);
      });
      const summary = node("summary", "", eventLabel(event));
      const stamp = eventTime(event.created_at);
      summary.append(node("small", "workspace-event-time", stamp));
      entry.append(summary, node("pre", "workspace-code", JSON.stringify(event.payload || {}, null, 2)));
      container.append(entry);
    }
    if (wasBottom) container.scrollTop = container.scrollHeight;
  }

  function renderConnections(container) {
    container.append(node("h2", "workspace-panel-title", "Bağlantılar"));
    if (!state.user) container.append(node("p", "workspace-muted", "Başak’ı sana verilen özel bağlantıyla açabilirsin; hesap oluşturman gerekmiyor."));
    for (const provider of state.providers) {
      const card = node("section", "workspace-connection");
      card.append(node("strong", "", provider.label || provider.id));
      const connected = state.connections.filter((connection) => {
        if (connection.status === "revoked") return false;
        if (provider.id === "composio") return connection.provider === "mcp" && Boolean(connection.metadata?.composio_toolkit);
        if (provider.id === "mcp") return connection.provider === "mcp" && !connection.metadata?.composio_toolkit;
        return connection.provider === provider.id;
      });
      if (!provider.configured) {
        card.append(node("p", "workspace-muted", "Sunucu bağlantısı yapılandırılmadı."));
      } else if (!state.user && provider.login) {
        const link = node("a", "workspace-button", (provider.label || provider.id) + " ile giriş yap");
        link.href = "/api/baglantilar/oauth/" + encodeURIComponent(provider.id) + "/baslat?purpose=login";
        card.append(link);
      } else if (state.user && provider.id === "composio") {
        for (const toolkit of provider.toolkits || []) {
          if (connected.some((connection) => connection.metadata?.composio_toolkit === toolkit.id)) continue;
          const link = node("a", "workspace-button", toolkit.label + " bağla");
          link.href = "/api/baglantilar/composio/baslat?toolkit=" + encodeURIComponent(toolkit.id);
          card.append(link);
        }
      } else if (state.user && provider.id !== "mcp") {
        if (provider.id === "github" && provider.installation_url) {
          const selection = node("a", "workspace-button", "Depo erişimini seç");
          selection.href = provider.installation_url;
          selection.target = "_blank";
          selection.rel = "noopener noreferrer";
          card.append(selection, node("p", "workspace-muted", "GitHub’da erişilecek depoları seç, sonra hesabını bağla."));
        }
        const link = node("a", "workspace-button", connected.length ? "Hesabı yeniden bağla" : "Hesap bağla");
        link.href = "/api/baglantilar/oauth/" + encodeURIComponent(provider.id) + "/baslat?purpose=connect";
        card.append(link);
      } else if (!state.user) {
        card.append(node("p", "workspace-muted", "Giriş yaptıktan sonra bağlanabilir."));
      }
      for (const connection of connected) {
        const item = node("div", "workspace-connection-item");
        const connectionStatus = { connected: "Bağlı", reauth_required: "Yeniden giriş gerekli" }[connection.status] || connection.status;
        item.append(node("p", "", (connection.label || provider.label || provider.id) + " · " + connectionStatus));
        if (connection.provider === "github" && Array.isArray(connection.metadata?.repositories)) {
          item.append(node("p", "workspace-muted", "Depolar: " + connection.metadata.repositories.join(", ")));
        }
        const remove = node("button", "workspace-text-button", "Erişimi kaldır");
        remove.type = "button";
        remove.addEventListener("click", async () => {
          remove.disabled = true;
          try {
            await client.write("/api/baglantilar/" + encodeURIComponent(connection.id), {}, "DELETE");
            await refreshConnections();
            message("Bağlantının erişimi kaldırıldı.");
          } catch (error) { handleError(error); remove.disabled = false; }
        });
        item.append(remove);
        if (connection.provider === "mcp") {
          const discover = node("button", "workspace-text-button", "Araçları kontrol et");
          discover.type = "button";
          discover.addEventListener("click", async () => {
            discover.disabled = true;
            try {
              const data = await client.write("/api/baglantilar/" + encodeURIComponent(connection.id) + "/kesfet", {});
              const form = node("form", "workspace-tool-list");
              form.append(node("p", "workspace-muted", "Bu bağlantıda izin vereceğin araçları seç."));
              const inputs = [];
              const allowed = connection.metadata && connection.metadata.allowed_tools || [];
              for (const tool of data.tools || []) {
                const label = node("label", "workspace-tool-choice");
                const input = node("input"); input.type = "checkbox"; input.value = tool.name;
                input.checked = allowed.includes(tool.name);
                inputs.push(input); label.append(input, node("span", "", tool.name)); form.append(label);
              }
              const save = node("button", "workspace-button", "Araç izinlerini kaydet"); save.type = "submit";
              form.append(save);
              form.addEventListener("submit", async (event) => {
                event.preventDefault(); save.disabled = true;
                try {
                  await client.write("/api/baglantilar/" + encodeURIComponent(connection.id), {
                    allowed_tools: inputs.filter((input) => input.checked).map((input) => input.value),
                  }, "PATCH");
                  message("MCP araç izinleri kaydedildi."); await refreshConnections();
                } catch (error) { handleError(error); save.disabled = false; }
              });
              item.append(form);
            } catch (error) { handleError(error); }
            finally { discover.disabled = false; }
          });
          item.append(discover);
        }
        card.append(item);
      }
      container.append(card);
    }
    if (!state.providers.length) container.append(node("p", "workspace-muted", "Bağlantı bilgileri alınamadı. Yenilemeyi deneyebilirsin."));
    if (state.user) {
      const form = node("form", "workspace-mcp-form");
      const label = node("label", "", "MCP sunucu adı");
      const input = node("input"); input.required = true; input.name = "label"; input.id = "platformMcpLabel";
      label.htmlFor = input.id;
      const urlLabel = node("label", "", "HTTPS MCP adresi");
      const url = node("input"); url.type = "url"; url.required = true; url.name = "url"; url.id = "platformMcpUrl";
      url.placeholder = "https://sunucu.example/mcp"; urlLabel.htmlFor = url.id;
      const submit = node("button", "workspace-button", "MCP bağlantısı ekle"); submit.type = "submit";
      const feedback = node("p", "workspace-muted"); feedback.setAttribute("role", "status");
      form.append(node("h3", "", "Yeni MCP bağlantısı"), label, input, urlLabel, url,
        node("p", "workspace-muted", "Adresin içine parola veya anahtar koyma. Yetkilendirme gerektiğinde ayrı bağlantı adımı kullanılır."), submit, feedback);
      form.addEventListener("submit", async (event) => {
        event.preventDefault(); submit.disabled = true;
        try {
          await client.write("/api/baglantilar/mcp", { label: input.value.trim(), url: url.value.trim(), allowed_tools: [] });
          await refreshConnections(); message("MCP bağlantısı kaydedildi; araç ve yetki kontrolünü açabilirsin.");
        } catch (error) { feedback.textContent = error.message; feedback.className = "workspace-error"; }
        finally { submit.disabled = false; }
      });
      container.append(form);
    }
  }

  function renderPreview() {
    const container = byId("workspaceContent");
    container.replaceChildren();
    for (const button of document.querySelectorAll("[data-preview-kind]")) {
      const selected = button.dataset.previewKind === previewKind;
      button.setAttribute("aria-selected", String(selected));
      button.tabIndex = selected ? 0 : -1;
      if (selected) container.setAttribute("aria-labelledby", button.id);
    }
    if (previewKind === "connections") { renderConnections(container); return; }
    const run = currentRun();
    const allRuns = run ? [run, ...Object.values(state.runs).filter((child) => child.parent_id && belongsTo(child, run.id))] : [];
    const artifacts = allRuns.flatMap((entry) => entry.artifacts || []);
    if (previewKind === "browser") {
      container.append(node("h2", "workspace-panel-title", "Tarayıcı"));
      const screenshots = artifacts.filter((artifact) => artifact.kind === "browser" || String(artifact.media_type || "").startsWith("image/"));
      if (!screenshots.length) container.append(node("p", "workspace-empty", "Bu görevden tarayıcı görüntüsü alınmadı. İşçi bir görüntü kaydettiğinde burada görünür."));
      for (const artifact of screenshots) appendArtifact(container, artifact);
      return;
    }
    const kind = previewKind === "terminal" ? "terminal" : previewKind === "diff" ? "diff" : null;
    const filtered = kind ? artifacts.filter((artifact) => artifact.kind === kind) : artifacts;
    container.append(node("h2", "workspace-panel-title", { outputs: "Görev çıktıları", terminal: "Komut çıktısı", diff: "Değişiklikler" }[previewKind] || "Çıktılar"));
    if (!filtered.length) container.append(node("p", "workspace-empty", run ? "Bu bölümde henüz kaydedilmiş bir çıktı yok." : "Dosyaları ve doğrulama sonuçlarını görmek için bir görev seç."));
    for (const artifact of filtered) appendArtifact(container, artifact);
  }

  function belongsTo(child, rootId) {
    const visited = new Set();
    let entry = child;
    while (entry && entry.parent_id && !visited.has(entry.id)) {
      if (entry.parent_id === rootId) return true;
      visited.add(entry.id); entry = state.runs[entry.parent_id];
    }
    return false;
  }

  function appendArtifact(container, artifact) {
    const details = node("details", "workspace-artifact");
    details.open = selectedArtifact === artifact.id;
    details.append(node("summary", "", artifact.title || artifact.id || "Çıktı"));
    details.addEventListener("toggle", () => { if (details.open) selectedArtifact = artifact.id; });
    if (artifact.sha256) details.append(node("small", "workspace-hash", "SHA-256 · " + artifact.sha256));
    const text = artifact.content ?? artifact.text ?? artifact.snippet;
    if (text !== undefined) details.append(node("pre", "workspace-code", typeof text === "string" ? text : JSON.stringify(text, null, 2)));
    const source = artifact.href || artifact.uri;
    const origin = scope.location.origin;
    const href = safeHref(source, origin);
    const preview = previewHref(source, origin);
    const media = artifact.media_type || artifact.mime_type || '';
    if (preview && String(media).startsWith("image/")) {
      const image = node("img", "workspace-screenshot"); image.src = preview; image.alt = artifact.title || "Görev tarayıcı görüntüsü";
      details.append(image);
    }
    if (preview && /^(text\/|application\/json)/.test(media)) {
      const content = node('pre', 'workspace-code', 'İçerik yükleniyor…'); details.append(content);
      details.addEventListener('toggle', async () => {
        if (!details.open || content.dataset.loaded) return;
        try {
          const response = await scope.fetch(preview, {credentials: 'same-origin', cache: 'no-store'});
          if (!response.ok) throw new Error('Çıktı okunamadı');
          content.textContent = await response.text(); content.dataset.loaded = 'true';
        } catch (error) { content.textContent = error.message; }
      });
    }
    if (href) {
      const link = node("a", "workspace-text-button", "Çıktıyı aç");
      link.href = href; link.target = "_blank"; link.rel = "noopener noreferrer";
      details.append(link);
    } else if (text === undefined) {
      details.append(node("p", "workspace-muted", "Çıktı kaydı mevcut; indirilebilir içerik adresi henüz yok."));
    }
    container.append(details);
  }

  function render() { renderAccount(); renderTaskList(); renderRunTree(); renderEvents(); renderPreview(); }

  async function refreshRuns() {
    if (!state.user) { renderTaskList(); return; }
    const version = revision;
    try {
      const data = await client.read("/api/kosu");
      if (version !== revision) return;
      const selectedId = state.selectedId;
      for (const run of data.kosular || []) {
        const next = snapshot(state, run);
        state.runs = next.runs;
      }
      state.selectedId = selectedId;
      renderTaskList();
    } catch (error) { if (version === revision) handleError(error); }
  }

  async function refreshConnections() {
    const version = revision;
    const data = await client.read("/api/baglantilar");
    if (version !== revision) return;
    state.connections = data.connections || [];
    renderPreview();
  }

  async function selectRun(id, reveal = true) {
    if (accountRequired()) return;
    const version = revision;
    const selection = ++selectionVersion;
    try {
      const data = await client.read("/api/kosu/" + encodeURIComponent(id) + "/agac");
      if (version !== revision || selection !== selectionVersion) return;
      state = snapshot(state, data.kosu);
      selectedArtifact = null;
      expandedEvents.clear();
      render();
      if (reveal) byId("platformTaskView").scrollIntoView({block: "nearest"});
      await pollEvents();
    } catch (error) { if (version === revision) handleError(error); }
  }

  async function pollEvents() {
    if (polling || !state.user || !state.selectedId) return;
    polling = true;
    const id = state.selectedId;
    const version = revision;
    try {
      const data = await client.read("/api/kosu/" + encodeURIComponent(id) + "/olaylar?after=" + state.cursor);
      if (version !== revision || id !== state.selectedId) return;
      state = events(state, data.olaylar || []);
      const tree = await client.read("/api/kosu/" + encodeURIComponent(id) + "/agac");
      if (version !== revision || id !== state.selectedId) return;
      const previous = state.runs[id];
      state = snapshot(state, tree.kosu);
      scope.dispatchEvent(new CustomEvent('basak:work-activity', {detail: {id, has_work: hasWork(tree.kosu)}}));
      if (!previous || previous.durum !== tree.kosu.durum || previous.answer !== tree.kosu.answer) {
        scope.dispatchEvent(new CustomEvent('basak:durable-update'));
      }
      renderTaskList(); renderRunTree(); renderEvents();
      if (previewKind !== "connections") renderPreview();
    } catch (error) { if (version === revision && id === state.selectedId) handleError(error); }
    finally { polling = false; }
  }

  async function perform(id, action, data) {
    if (busy || accountRequired()) return;
    busy = true; renderRunTree();
    const version = revision;
    const selected = state.selectedId;
    try {
      const result = await client.action(id, action, data);
      if (version !== revision) return;
      if (result.kosu) {
        state = snapshot(state, result.kosu);
        if (selected && state.runs[selected]) state.selectedId = selected;
      }
      message(action === "yon" ? "Yeni yön kalıcı kuyruğa alındı." : "İşlem kaydedildi.");
      await pollEvents();
    } catch (error) { if (version === revision) handleError(error); }
    finally { busy = false; render(); }
  }

  byId("platformSteerForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = byId("platformSteerInput");
    if (!input.value.trim() || !state.selectedId) return;
    const value = input.value;
    await perform(state.selectedId, "yon", { metin: value });
    if (!byId("platformMessage").classList.contains("is-error")) input.value = "";
  });
  byId("platformCancel").addEventListener("click", () => perform(state.selectedId, "iptal", {}));
  byId("platformResume").addEventListener("click", () => perform(state.selectedId, "devam", {}));
  byId("platformRefresh").addEventListener("click", () => { refreshRuns(); pollEvents(); });
  for (const button of document.querySelectorAll("[data-preview-kind]")) {
    button.addEventListener("click", () => { previewKind = button.dataset.previewKind; renderPreview(); });
    button.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const tabs = Array.from(document.querySelectorAll("[data-preview-kind]"));
      let index = tabs.indexOf(button);
      if (event.key === "Home") index = 0;
      else if (event.key === "End") index = tabs.length - 1;
      else index = (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
      tabs[index].click(); tabs[index].focus();
    });
  }
  byId("workspaceToggle").addEventListener("click", () => showPreview(byId("workspacePreview").hidden));
  byId("workspaceClose").addEventListener("click", () => showPreview(false));
  byId("workspaceBackdrop").addEventListener("click", () => showPreview(false));
  byId("platformConnections").addEventListener("click", () => {
    previewKind = "connections"; renderPreview(); showPreview(true);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !byId("workspacePreview").hidden && scope.matchMedia("(max-width: 1100px)").matches) showPreview(false);
    if (event.key === "Tab" && !byId("workspacePreview").hidden && scope.matchMedia("(max-width: 1100px)").matches) {
      const items = Array.from(byId("workspacePreview").querySelectorAll('button:not([disabled]),a[href],input,textarea,[tabindex="0"]')).filter((item) => !item.hidden);
      if (!items.length) return;
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });

  async function start() {
    try {
      if (scope.basakKimlikHazir) await scope.basakKimlikHazir;
      const [account, providers] = await Promise.all([
        client.read("/api/hesap"), client.read("/api/baglantilar/saglayicilar"),
      ]);
      state = identity(state, account.authenticated ? account.user : null);
      state.providers = providers.providers || [];
      if (state.user) {
        await Promise.all([refreshRuns(), refreshConnections()]);
        scope.dispatchEvent(new CustomEvent("basak:platform-account", { detail: state.user }));
        if (selectedConversation?.runs?.length) await selectRun(selectedConversation.runs.at(-1).id, false);
      }
      render();
    } catch (error) {
      render(); message("Çalışma alanı bilgileri alınamadı: " + error.message, true);
    }
  }
  if (scope.matchMedia("(max-width: 1100px)").matches) {
    byId("workspacePreview").hidden = true;
    byId("workspaceToggle").setAttribute("aria-expanded", "false");
    document.querySelector(".app-shell").classList.remove("workspace-open");
  }
  render(); start();
  const poll = scope.setInterval(() => {
    if (!document.hidden) pollEvents();
  }, 3000);
  scope.addEventListener("pagehide", () => {
    scope.clearInterval(poll);
  });
})(typeof window !== "undefined" ? window : globalThis);
