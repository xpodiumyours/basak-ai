"""Workspace checks with explicit HTTP fixtures; no live provider acceptance claims.

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


def test_chat_protocol_records_are_not_user_work_and_epoch_seconds_are_correct():
    js("""
const chat={id:'r',kind:'chat',artifacts:[{id:'answer'}],checks:[{id:'response_recorded',ok:true}]};
assert.equal(ui.hasWork(chat),false);
assert.equal(ui.hasWork({...chat,artifacts:[{id:'generated-id',kind:'answer'}]}),false);
assert.equal(ui.activityEvent({type:'artifact',payload:{id:'generated-id',kind:'answer'}}),false);
assert.equal(ui.hasWork({...chat,has_work:true}),true);
assert.equal(ui.hasWork({...chat,children:[{id:'child'}]}),true);
assert.equal(ui.hasWork({...chat,artifacts:[{id:'report.pdf'}]}),true);
assert.equal(ui.hasWork({...chat,approvals:[{status:'pending'}]}),true);
assert.equal(ui.hasWork({...chat,kind:'agent'}),true);
assert.equal(ui.activityEvent({type:'checkpoint'}),false);
assert.equal(ui.activityEvent({type:'chat',payload:{tur:'runState'}}),false);
assert.equal(ui.activityEvent({type:'tool_started',payload:{tool:'hesapla'}}),true);
assert.equal(ui.activityEvent({type:'tool_started',payload:{tool:'son_cevap'}}),false);
assert.equal(ui.eventTime(1793260800),ui.eventTime(1793260800000));
assert.equal(ui.eventTime('invalid'),'');
""")


def test_disconnected_observer_reads_same_run_without_resubmitting_and_respects_stop():
    js("""
(async () => {
 let reads=0;
 const result=await ui.observeRun('same-run',async path => {
   assert.equal(path,'/api/kosu/same-run/agac'); reads++;
   return {kosu:{id:'same-run',durum:reads===1?'running':'completed',answer:reads===1?'':'Yanıt'}};
 },null,async()=>{});
 assert.equal(reads,2); assert.equal(result.tur,'bitir'); assert.equal(result.cevap,'Yanıt');
 const stopped=new AbortController(); stopped.abort();
 await assert.rejects(ui.observeRun('same-run',()=>{throw Error('must not read');},stopped.signal),{name:'AbortError'});
 const failed=await ui.observeRun('same-run',async()=>({kosu:{id:'same-run',durum:'failed',hata:'Gerçek hata'}}));
 assert.equal(failed.tur,'error'); assert.equal(failed.metin,'Gerçek hata');
})().catch(error=>{console.error(error);process.exitCode=1;});
""")


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


def test_bubbled_child_status_never_changes_parent_and_offline_turns_survive_refresh():
    js("""
let state=ui.snapshot(ui.createState('a'),{id:'root',durum:'running',children:[{id:'child',durum:'running'}]});
state=ui.events(state,[{seq:1,run_id:'root',type:'status',payload:{origin_run_id:'child',durum:'failed'}}]);
assert.equal(state.runs.root.durum,'running'); assert.equal(state.runs.child.durum,'failed');
const user={role:'user',content:'first'}, answer={role:'assistant',content:'answer'};
const later=[{role:'user',content:'offline follow-up'},{role:'assistant',content:'legacy reply'}];
assert.deepEqual(ui.mergeMessages([user,answer],[user,answer,...later]),[user,answer,...later]);
assert.deepEqual(ui.mergeMessages([user,answer],[user]),[user,answer]);
assert.deepEqual(ui.mergeMessages([user,answer],[user,...later]),[user,answer,...later]);
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
            "workspacePreview", "platformRunTree", "platformAccount"} <= set(page.ids)
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


def test_worker_online_indicator_reports_real_server_state_only():
    js("""
assert.match(ui.workerStatusText(null),/çevrimdışı/);
assert.match(ui.workerStatusText({online:false,live_workers:8}),/çevrimdışı/);
assert.equal(ui.workerStatusText({online:true,live_workers:3}),
 'Ajan işçisi çevrimiçi · 3 çalışan');
""")


@pytest.mark.parametrize('width,height', [(1440, 900), (390, 844)])
def test_real_chromium_pending_chat_title_reload_and_view_preservation(width, height, tmp_path):
    import functools
    import threading
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    playwright = pytest.importorskip('playwright.sync_api')
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT / 'web')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    artifact = {'id': 'report-file', 'title': 'Kaynakli rapor.md', 'media_type': 'text/markdown',
                'href': '/api/kosu/research-child/artifacts/report-file'}
    run = {'id': 'durable-test', 'kind': 'chat', 'durum': 'waiting_children', 'istek': 'Long task',
           'children': [{'id': 'research-child', 'parent_id': 'durable-test', 'durum': 'completed',
                         'istek': 'Resmi kaynaklari incele', 'answer': 'Kaynaklar incelendi.',
                         'artifacts': [artifact]}],
           'artifacts': [], 'checks': [], 'approvals': [], 'seq': 1}
    errors = []
    try:
        with playwright.sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={'width': width, 'height': height})
            page.on('pageerror', lambda error: errors.append(str(error)))
            def api(route):
                path = route.request.url.split('?', 1)[0]
                data = {'ok': True}
                if path.endswith('/api/kimlik'):
                    data.update(kullanici='alice', basak_id='Alice')
                elif path.endswith('/api/hesap'):
                    data.update(authenticated=True, user={'id': 'alice', 'name': 'Alice'})
                elif path.endswith('/agac'):
                    data['kosu'] = run
                elif path.endswith('/api/kosu/sohbetler'):
                    data['chats'] = [{'id': 'saved-thread', 'title': 'Saved title',
                        'messages': [{'role': 'user', 'content': 'Long task'}],
                        'runs': [{'id': 'durable-test', 'state': run['durum'], 'has_work': bool(run['children'])}],
                        'pendingRuns': [{'id': 'durable-test', 'state': 'waiting_children'}]}]
                elif path.endswith('/olaylar'):
                    data['olaylar'] = [{'seq': 1, 'run_id': 'durable-test', 'type': 'tool_done',
                        'payload': {'origin_run_id': 'research-child', 'tool': 'sayfa_oku', 'ok': True}}]
                elif path.endswith('/artifacts/report-file'):
                    route.fulfill(status=200, content_type='text/markdown', body='# Kaynakli rapor\nGercek HTTP dosya onizleme testi.')
                    return
                else:
                    data.update(kosular=[], olaylar=[], connections=[], providers=[])
                route.fulfill(status=200, content_type='application/json', body=json.dumps(data))
            page.route('**/api/**', api)
            page.goto('http://127.0.0.1:%d/index.html' % server.server_port)
            page.wait_for_function("typeof olayiIsle === 'function' && window.basakKimlik?.kullanici")
            assert page.locator('.chat-main').is_visible()
            assert not page.locator('#workspacePreview').is_visible()
            page.evaluate("""() => {
                const b = bubble('assistant', ''); balonlar.set('durable-test', b);
                olayiIsle({istek:'durable-test', kosu_id:'durable-test', tur:'durableRun',
                  conversation_id:'saved-thread', conversation_title:'Saved title', display_text:'Long task'});
                olayiIsle({istek:'durable-test', tur:'checkpoint'});
            }""")
            page.wait_for_function("document.querySelector('#historyList').textContent.includes('Saved title')")
            assert page.locator('.chat-main').is_visible()
            assert page.locator('#platformTaskView').is_visible()
            assert page.locator('[data-platform-view]').count() == 0
            assert page.locator('#platformTaskForm').count() == 0
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.evaluate('localStorage.clear()')
            page.reload()
            page.wait_for_function("window.basakKimlik?.kullanici")
            if page.locator('#sidebarToggle').is_visible():
                page.locator('#sidebarToggle').click()
            page.get_by_role('button', name='Saved title', exact=True).click()
            assert page.get_by_role('button', name='Çalışmayı göster', exact=True).is_visible()
            assert page.locator('#chat').inner_text().startswith('Long task')
            page.get_by_role('button', name='Çalışmayı göster', exact=True).click()
            page.locator('#platformRunTree').get_by_text('Resmi kaynaklari incele', exact=True).wait_for()
            page.locator('#platformRunTree summary').get_by_text('Araç işlemleri · 1', exact=True).wait_for()
            if width < 760:
                page.wait_for_function("document.querySelector('#sidebar').getBoundingClientRect().right <= 0")
            page.screenshot(path=str(tmp_path / ('unified-chat-%d.png' % width)), full_page=True)
            page.get_by_role('button', name='Kaynakli rapor.md', exact=True).click()
            page.get_by_text('# Kaynakli rapor', exact=False).wait_for()
            assert page.locator('#workspacePreview').is_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            if width < 1100:
                assert page.locator('#workspacePreview').get_attribute('aria-modal') == 'true'
            page.keyboard.press('Escape') if width < 1100 else page.locator('#workspaceClose').click()
            assert not page.locator('#workspacePreview').is_visible()
            assert not errors, errors
            # An ordinary reply keeps its durable history but exposes no task UI.
            run.update(durum='completed', answer='Merhaba!', children=[],
                       artifacts=[{'id': 'generated-answer-id', 'kind': 'answer', 'title': 'Basak sonucu'}],
                       checks=[{'id': 'response_recorded', 'ok': True}])
            page.reload()
            page.wait_for_function("window.basakKimlik?.kullanici")
            if page.locator('#sidebarToggle').is_visible():
                page.locator('#sidebarToggle').click()
            page.get_by_role('button', name='Saved title', exact=True).click()
            page.wait_for_timeout(1200)
            assert not page.locator('#platformTaskView').is_visible()
            assert page.get_by_role('button', name='Çalışmayı göster', exact=True).count() == 0
            assert 'response_recorded' not in page.locator('body').inner_text()
            # The real app's stream reader reconnects through GET for the same run.
            recovered = page.evaluate("""async () => {
                const b=bubble('assistant',''); balonlar.set('durable-test',b);
                const bytes=new TextEncoder().encode(JSON.stringify({tur:'durableRun',
                  istek:'durable-test',kosu_id:'durable-test',conversation_id:'saved-thread',display_text:'Merhaba'})+'\\n');
                const stream=new ReadableStream({start(c){c.enqueue(bytes);c.close();}});
                return await canliYanitiOku(new Response(stream),b);
            }""")
            assert recovered['ok'] is True and recovered['cevap'] == 'Merhaba!'
            assert not page.locator('#platformTaskView').is_visible()
            assert page.locator('.topbar #workspaceToggle').count() == 0
            assert page.locator('.sidebar #workspaceToggle').count() == 1
            actions = page.locator('.cevap-eylem').last
            assert not actions.get_by_role('button', name='Kopyala', exact=True).is_visible()
            actions.locator('summary').click()
            assert actions.get_by_role('button', name='Kopyala', exact=True).is_visible()
            page.keyboard.press('Escape')
            assert not actions.get_by_role('button', name='Kopyala', exact=True).is_visible()
            assert actions.locator('summary').evaluate('(e)=>e===document.activeElement')
            actions.locator('summary').press('Enter')
            with page.expect_download() as downloaded:
                actions.get_by_role('button', name='Markdown', exact=True).click()
            assert Path(downloaded.value.path()).read_text(encoding='utf-8') == 'Merhaba!'
            page.keyboard.press('Escape')
            if page.locator('#sidebarToggle').is_visible():
                page.locator('#sidebarToggle').click()
            page.locator('#workspaceToggle').click()
            assert page.locator('#workspacePreview').is_visible()
            page.locator('#workspaceClose').click()
            assert not page.locator('#workspacePreview').is_visible()
            if page.locator('#sidebarToggle').is_visible():
                page.mouse.click(width - 12, height / 2)
            page.screenshot(path=str(tmp_path / ('ordinary-chat-%d.png' % width)), full_page=True)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize('width,height', [(1440, 900), (390, 844)])
def test_real_chromium_connectors_panel_manages_and_toggles(width, height, tmp_path):
    """Bağlantılar paneli: iki giriş satırı, izin formu ve aç/kapa anahtarı."""
    import functools
    import threading
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    playwright = pytest.importorskip('playwright.sync_api')
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT / 'web')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    connection = {
        'id': 'conn-github', 'provider': 'mcp', 'status': 'connected',
        'label': 'Composio GitHub', 'scopes': [],
        'metadata': {
            'composio_toolkit': 'github', 'composio_session_id': 'trs_fixture_123456',
            'url': 'https://backend.composio.dev/tool_router/fixture',
            'tools': [{'name': 'github_read', 'remote_name': 'GITHUB_READ'},
                      {'name': 'github_write', 'remote_name': 'GITHUB_WRITE'}],
            'allowed_tools': ['github_read'],
        },
    }
    patched = []
    errors = []
    try:
        with playwright.sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={'width': width, 'height': height})
            page.on('pageerror', lambda error: errors.append(str(error)))
            def api(route):
                request = route.request
                path = request.url.split('?', 1)[0]
                method = request.method
                if path.endswith('/api/kimlik'):
                    data = {'ok': True, 'kullanici': 'alice', 'basak_id': 'Alice'}
                elif path.endswith('/api/hesap'):
                    data = {'ok': True, 'authenticated': True, 'user': {'id': 'alice', 'name': 'Alice'}}
                elif path.endswith('/api/baglantilar/saglayicilar'):
                    data = {'providers': [
                        {'id': 'github', 'label': 'GitHub', 'configured': True, 'login': True,
                         'scopes': [], 'login_only': True, 'verification_required': True},
                        {'id': 'composio', 'label': 'Composio', 'configured': True, 'reason': None,
                         'login': False, 'scopes': [], 'toolkits': []},
                        {'id': 'mcp', 'label': 'MCP', 'configured': True, 'reason': None,
                         'login': False, 'scopes': []}]}
                elif path.endswith('/api/baglantilar/composio/katalog'):
                    data = {'toolkits': [{'id': 'gmail', 'label': 'Gmail',
                                          'description': 'E-postalar ve taslaklar', 'logo': ''}],
                            'next_cursor': ''}
                elif path.endswith('/kesfet'):
                    data = {'tools': connection['metadata']['tools']}
                elif path.endswith('/api/baglantilar') and method == 'GET':
                    data = {'connections': [connection]}
                elif path.endswith('/api/baglantilar/conn-github') and method == 'PATCH':
                    body = json.loads(request.post_data or '{}')
                    patched.append(body)
                    metadata = dict(connection['metadata'])
                    if 'enabled' in body:
                        metadata['enabled'] = bool(body['enabled'])
                        if body['enabled'] is False:
                            metadata['disabled_tools'] = list(metadata['allowed_tools'])
                            metadata['allowed_tools'] = []
                        else:
                            metadata.pop('disabled_tools', None)
                    if 'allowed_tools' in body:
                        metadata['allowed_tools'] = list(body['allowed_tools'])
                    connection['metadata'] = metadata
                    data = connection
                else:
                    data = {'ok': True, 'kosular': [], 'olaylar': [],
                            'connections': [], 'providers': []}
                route.fulfill(status=200, content_type='application/json', body=json.dumps(data))
            page.route('**/api/**', api)
            page.goto('http://127.0.0.1:%d/index.html' % server.server_port)
            page.wait_for_function("typeof olayiIsle === 'function' && window.basakKimlik?.kullanici")
            if page.locator('#sidebarToggle').is_visible():
                page.locator('#sidebarToggle').click()
            page.locator('#platformConnections').click()
            page.locator('[data-connector-view="add"]').wait_for()
            # İki giriş satırı, yönet görünümü açıkken yönet satırı seçili.
            assert page.locator('[data-connector-view="manage"]').get_attribute('aria-pressed') == 'true'
            assert page.locator('[data-connector-view="add"]').is_visible()
            assert page.get_by_role('heading', name='Bağlı hesaplarım').is_visible()
            row = page.locator('.workspace-connector-item')
            assert row.get_by_text('Composio GitHub', exact=False).is_visible()
            assert row.get_by_text('Bağlı', exact=False).is_visible()
            # İzin formu: kesfet çağrısıyla gelir, seçili araç işaretli açılır.
            page.get_by_role('button', name='Yönet', exact=True).click()
            page.locator('.workspace-tool-list').wait_for()
            assert page.locator('.workspace-tool-list input[value="github_read"]').is_checked()
            assert not page.locator('.workspace-tool-list input[value="github_write"]').is_checked()
            # Anahtar: açıkken kapat, sunucuya enabled:false gider, kapalıyken araçlar yok.
            switch = page.locator('.workspace-switch')
            assert switch.get_attribute('aria-checked') == 'true'
            switch.click()
            page.wait_for_function(
                "document.querySelector('.workspace-switch').getAttribute('aria-checked') === 'false'")
            assert patched and patched[-1] == {'enabled': False}
            assert connection['metadata']['allowed_tools'] == []
            # Uygulama ekle görünümü: arama ve katalog satırı.
            page.locator('[data-connector-view="add"]').click()
            page.wait_for_function(
                "document.querySelector('.workspace-connector-heading')?.textContent === 'Uygulama keşfet'")
            assert page.locator('input[aria-label="Bağlanacak uygulama ara"]').is_visible()
            assert page.locator('a[href*="composio/baslat?toolkit=gmail"]').is_visible()
            assert page.locator('[data-connector-view="add"]').get_attribute('aria-pressed') == 'true'
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.screenshot(path=str(tmp_path / ('connectors-%d.png' % width)), full_page=True)
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
