(function (scope) {
  "use strict";
  if (typeof document === "undefined") return;
  let profile = { enabled: false, authenticated: false, owner: false };
  const element = (tag, text) => { const n = document.createElement(tag); if (text) n.textContent = text; return n; };
  async function api(path, body) {
    const r = await fetch("/api/ozel-erisim" + path, {
      method: body === undefined ? "GET" : "POST", credentials: "same-origin",
      headers: body === undefined ? {} : {"Content-Type":"application/json"},
      body: body === undefined ? undefined : JSON.stringify(body), cache:"no-store"
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || data.detail || "İşlem tamamlanamadı.");
    return data;
  }
  function dialog(title, locked) {
    const box = element("dialog"); box.className = "private-dialog";
    const heading = element("h2", title); heading.id = "private-title-" + Date.now();
    box.setAttribute("aria-labelledby", heading.id); box.append(heading);
    if (locked) box.addEventListener("cancel", e => e.preventDefault());
    else {
      const close = element("button", "Kapat"); close.type="button";
      close.addEventListener("click", () => { box.close(); box.remove(); }); box.append(close);
    }
    document.body.append(box); box.showModal(); return box;
  }
  function help(message) {
    const box=dialog("Başak sana özel", true);
    box.append(element("p", message || "Bu alan davetlilere açık. Sana gönderilen özel bağlantıyı açman yeterli; hesap veya e-posta doğrulaması gerekmiyor."));
    return box;
  }
  async function people() {
    const box=dialog("Paylaştığın kişiler", false);
    const intro=element("p", "Her kişinin konuşmaları ayrı kalır. Yeni bağlantıyı yalnız o kişiyle paylaş.");
    const list=element("div"), form=element("form"), label=element("label", "Kişinin adı");
    const input=element("input"); input.required=true; input.maxLength=100; input.id="private-person-name"; label.htmlFor=input.id;
    const add=element("button", "Özel bağlantı oluştur"); add.type="submit";
    const feedback=element("p"); feedback.setAttribute("role","status");
    form.append(label,input,add); box.append(intro,form,feedback,list);
    async function refresh() {
      const data=await api("/davetler"); list.replaceChildren();
      for (const entry of data.invites) {
        const row=element("div"); row.className="private-person";
        row.append(element("span", entry.label + (entry.role==="owner" ? " · Sen" : entry.enabled ? " · Açık" : " · Kapalı")));
        if (entry.enabled && entry.role!=="owner") {
          const revoke=element("button", "Erişimi kapat"); revoke.type="button";
          revoke.addEventListener("click", async () => {
            revoke.disabled=true;
            try { await api("/davetler/"+encodeURIComponent(entry.id)+"/kapat",{}); await refresh(); }
            catch(e) { feedback.textContent=e.message; revoke.disabled=false; }
          }); row.append(revoke);
        } list.append(row);
      }
    }
    form.addEventListener("submit", async e => {
      e.preventDefault(); add.disabled=true; feedback.replaceChildren();
      try {
        const data=await api("/davetler", {label:input.value.trim()});
        const url=new URL("/",location.origin); url.hash="davet="+data.code;
        const copyLabel=element("label", "Paylaşılacak özel bağlantı");
        const field=element("input"); field.id="private-created-link"; copyLabel.htmlFor=field.id; field.readOnly=true; field.value=url.href;
        const copy=element("button", "Bağlantıyı kopyala"); copy.type="button";
        copy.addEventListener("click", async () => {
          try { await navigator.clipboard.writeText(field.value); copy.textContent="Kopyalandı"; }
          catch { field.focus(); field.select(); copy.textContent="Bağlantıyı seçtim; kopyalayabilirsin"; }
        });
        feedback.append(copyLabel,field,copy); input.value=""; await refresh();
      } catch(e) { feedback.textContent=e.message; }
      finally { add.disabled=false; }
    });
    try { await refresh(); input.focus(); } catch(e) { feedback.textContent=e.message; }
  }
  const controller={get enabled(){return profile.enabled;}, openHelp:help,
    decorate(container) {
      if (profile.owner) {
        const button=element("button", "Paylaştığım kişiler"); button.type="button"; button.className="workspace-text-button";
        button.addEventListener("click",people); container.append(button);
      }
    }};
  scope.BasakPrivateAccess=controller;
  document.documentElement.dataset.privatePending="true";
  async function start() {
    const params=new URLSearchParams(location.hash.slice(1));
    const code=params.get("davet");
    if (code) {
      document.documentElement.dataset.privatePending="true";
      document.querySelectorAll('.private-dialog').forEach(box => { box.close(); box.remove(); });
      // Fragments are never sent to the server; remove the bearer link before other navigation.
      history.replaceState(null,"",location.pathname+location.search);
      const box=help("Özel bağlantın açılıyor…");
      async function redeem() {
        try { await api("/ac",{code}); location.replace(location.pathname+location.search); }
        catch(e) {
          box.replaceChildren(element("h2","Bağlantı açılamadı"),element("p",e.message));
          const retry=element("button","Tekrar dene"); retry.addEventListener("click",redeem); box.append(retry);
        }
      }
      await redeem(); return;
    }
    try {
      profile=await api("");
      if (profile.enabled && !profile.authenticated) help();
      scope.dispatchEvent(new Event("basak:private-ready"));
    } catch { help("Başak’a şu anda ulaşılamıyor. Biraz sonra sayfayı yenileyebilirsin."); }
    finally { delete document.documentElement.dataset.privatePending; }
  }
  scope.addEventListener("hashchange", () => {
    if (new URLSearchParams(location.hash.slice(1)).has("davet")) start();
  });
  controller.ready = start();
})(typeof window!=="undefined" ? window : globalThis);
