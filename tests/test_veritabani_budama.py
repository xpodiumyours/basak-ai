"""Eski kosu govdeleri silinir, kosu ve denetim satiri kalir (2026-11-03).

Neden: `event.payload`, `action.result`, `artifact.data` tam arac katalogunu
ve arac ciktilarini tasiyor; biriken bu govdeler Neon'un ucretsiz plan
kotasini doldurup tum sistemi kilitledi. Budama, eski kosularin agir
satirlarini siler; kosu kaydi ve "hangi arac, ok/hata" bilgisi kalir.
"""
from chat import kosu_deposu
from chat.platform_runtime import RuntimeStore


def _store(tmp_path):
    clock = [1_000_000.0]
    store = RuntimeStore(kosu_deposu._SqliteDepo(str(tmp_path / 'budama.db')),
                         clock=lambda: clock[0])
    return store, clock


def _kosu(store):
    return store.create('alice', 'personal', 'test isi', require_worker=False)['id']


def test_eski_kosunun_govdeleri_silinir_kosu_kalir(tmp_path):
    store, clock = _store(tmp_path)
    run_id = _kosu(store)
    store.add_artifact('alice', run_id, {'id': 'cikti', 'data': 'x' * 500})
    with store.transaction() as tx:
        tx.execute("INSERT INTO basak_platform_action(run_id,call_id,tool,arguments,digest,"
                   "side_effect,status,result,ok,generation) VALUES(%s,%s,%s,%s,%s,0,'ok',%s,1,0)",
                   (run_id, 'c1', 'web_ara', '{}', 'd', 'y' * 500))

    clock[0] += 15 * 86400
    sayi = store.budama(14)
    assert sayi['kosu'] == 1
    assert sayi['olay'] >= 1
    assert sayi['eylem'] == 1
    assert sayi['yapay'] == 1

    with store.transaction() as tx:
        assert tx.one("SELECT COUNT(*) AS n FROM basak_platform_event WHERE run_id=%s",
                      (run_id,))['n'] == 0
        assert tx.one("SELECT COUNT(*) AS n FROM basak_platform_artifact WHERE run_id=%s",
                      (run_id,))['n'] == 0
        eylem = tx.one("SELECT tool,result FROM basak_platform_action WHERE run_id=%s", (run_id,))
    assert eylem['tool'] == 'web_ara' and eylem['result'] is None
    assert store.get('alice', run_id)['id'] == run_id  # kosu kaydi duruyor


def test_taze_kosuya_dokunulmaz(tmp_path):
    store, clock = _store(tmp_path)
    run_id = _kosu(store)
    clock[0] += 3 * 86400
    assert store.budama(14) == {'kosu': 0, 'olay': 0, 'eylem': 0, 'yapay': 0}
    with store.transaction() as tx:
        assert tx.one("SELECT COUNT(*) AS n FROM basak_platform_event WHERE run_id=%s",
                      (run_id,))['n'] > 0
