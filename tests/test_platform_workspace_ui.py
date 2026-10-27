"""Executable workspace behavior checks; no provider calls or browser simulation data.

The reducer and HTTP controller are the same code loaded by the real page.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js is required")


def js(body):
    proc = subprocess.run(
        [NODE, "-e", "const assert=require('node:assert/strict'); const ui=require('./web/platform.js');\n" + body],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout


def test_event_replay_is_ordered_and_idempotent():
    js("""
let state=ui.createState('alice');
state=ui.snapshot(state,{id:'r1',durum:'queued',istek:'task',children:[]});
state=ui.events(state,[
 {seq:3,run_id:'r1',type:'status',payload:{durum:'verifying'}},
 {seq:1,run_id:'r1',type:'status',payload:{durum:'running'}},
 {seq:2,run_id:'r1',type:'tool_done',payload:{tool:'web_search',ok:false}},
 {seq:2,run_id:'r1',type:'tool_done',payload:{tool:'web_search',ok:false}}
]);
assert.equal(state.cursor,3); assert.equal(state.log.length,3);
assert.equal(state.runs.r1.durum,'verifying');
state=ui.events(state,[{seq:2,run_id:'r1',type:'status',payload:{durum:'completed'}}]);
assert.equal(state.runs.r1.durum,'verifying');
assert.equal(ui.statusText(state.runs.r1.durum),'Doğrulanıyor');
""")


def test_account_change_clears_task_and_connection_data():
    js("""
let state=ui.snapshot(ui.createState('alice'),{id:'private',durum:'running',children:[]});
state.connections=[{id:'alice-token-reference'}];
state=ui.identity(state,{id:'bob',name:'Bob'});
assert.equal(state.principal,'bob'); assert.deepEqual(state.runs,{});
assert.deepEqual(state.connections,[]); assert.equal(state.selectedId,null);
state=ui.identity(state,null); assert.equal(state.principal,'');
""")


def test_child_failure_and_artifacts_are_not_replaced_with_fake_success():
    js("""
let state=ui.snapshot(ui.createState('a'),{id:'root',durum:'running',children:[{id:'child',durum:'running'}]});
state=ui.events(state,[
 {seq:1,run_id:'child',type:'status',payload:{durum:'failed',hata:'timeout'}},
 {seq:2,run_id:'child',type:'artifact',payload:{id:'f1',kind:'file',title:'x.txt'}},
 {seq:3,run_id:'child',type:'check',payload:{id:'c1',ok:false,evidence:'test failed'}}
]);
assert.equal(state.runs.child.durum,'failed');
assert.equal(state.runs.root.durum,'running');
assert.equal(state.runs.child.artifacts[0].id,'f1');
assert.equal(state.runs.child.checks[0].ok,false);
assert.equal(ui.statusText('made-up'),'Durum alınamadı');
""")


def test_safe_links_reject_script_tokens_and_cross_origin_preview():
    js("""
assert.equal(ui.safeHref('javascript:alert(1)','https://basak.test'),null);
assert.equal(ui.safeHref('https://u:p@evil.test/x','https://basak.test'),null);
assert.equal(ui.safeHref('https://example.com/?access_token=secret','https://basak.test'),null);
assert.equal(ui.previewHref('https://evil.test/file','https://basak.test'),null);
assert.equal(ui.previewHref('/api/kosu/r1/artifacts/f','https://basak.test'),'https://basak.test/api/kosu/r1/artifacts/f');
assert.equal(ui.safeHref('https://github.com/a/b/pull/1','https://basak.test'),'https://github.com/a/b/pull/1');
""")


def test_cancel_and_steer_use_real_http_contract_and_surface_errors():
    js("""
(async()=>{
 const calls=[];
 const client=ui.createClient(async(path,options)=>{
   calls.push({path,options});
   return {ok:!path.endsWith('/yon'),status:path.endsWith('/yon')?409:200,
     json:async()=>path.endsWith('/yon')?{error:'run already closed'}:{ok:true,kosu:{id:'r/1',durum:'cancelled'}}};
 });
 const result=await client.action('r/1','iptal',{});
 assert.equal(result.kosu.durum,'cancelled');
 assert.equal(calls[0].path,'/api/kosu/r%2F1/iptal');
 assert.equal(calls[0].options.method,'POST');
 assert.equal(calls[0].options.credentials,'same-origin');
 await assert.rejects(client.action('r/1','yon',{metin:'new'}),/run already closed/);
 await assert.rejects(client.action('r1','delete',{}),/Geçersiz/);
})();
""")


def test_http_unauthorized_is_not_treated_as_empty_tasks():
    js("""
(async()=>{
 const client=ui.createClient(async()=>({ok:false,status:401,json:async()=>({error:'sign in required'})}));
 try { await client.read('/api/kosu'); assert.fail('must reject'); }
 catch(e) { assert.equal(e.status,401); assert.match(e.message,/sign in required/); }
})();
""")


def test_index_has_unique_labels_and_preserves_chat_entrypoints():
    from html.parser import HTMLParser

    class Page(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids = []
            self.scripts = []

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if "id" in attrs:
                self.ids.append(attrs["id"])
            if tag == "script":
                self.scripts.append(attrs.get("src", ""))

    page = Page()
    page.feed((ROOT / "web/index.html").read_text(encoding="utf-8"))
    assert len(page.ids) == len(set(page.ids))
    assert {"chat", "message", "send", "historyList", "platformTaskList",
            "workspacePreview", "platformTaskForm", "platformAccount"} <= set(page.ids)
    assert any(src.startswith("/platform.js") for src in page.scripts)


def test_waiting_children_summary_and_check_evidence_are_human_readable():
    js("""
assert.equal(ui.statusText('waiting_children'),'Alt ajanlar bekleniyor');
const counts=ui.childProgress({children:[
 {durum:'completed'}, {durum:'running'}, {durum:'queued'}, {durum:'uncertain'}
]});
assert.deepEqual(counts,{total:4,completed:1,running:1,failed:1,pending:1});
assert.equal(ui.evidenceText({id:'postcondition', evidence:{verified:true}}),
 'postcondition · Tarayıcı doğrulandı');
assert.equal(ui.evidenceText({id:'build', evidence:{exit_code:0}}),
 'build · Çıkış kodu 0');
assert(!ui.evidenceText({id:'secret', evidence:{access_token:'HIDDEN_SECRET'}})
 .includes('HIDDEN_SECRET'));
""")


def test_approval_details_display_targets_not_form_or_token_values():
    js("""
const a={preview:{operation:'github_write_file',
 target:{repository:'team/app',branch:'feat/task',path:'src/app.py'}}};
assert.match(ui.approvalDetails(a),/Depo: team\\/app/);
assert.match(ui.approvalDetails(a),/Dosya: src\\/app.py/);
const b={preview:{operation:'yaz',target:{session_id:'session'}}};
assert.match(ui.approvalDetails(b),/Tarayıcı oturumu: session/);
assert(!ui.approvalDetails(b).includes('password'));
""")
