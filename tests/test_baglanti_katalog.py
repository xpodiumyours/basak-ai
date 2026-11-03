"""Baglanti arac katalogu: modele tam sema dokulmesini engelleyen davranis."""

import json

import pytest


def _araclar():
    return [
        {"name": "mcp__c1__GITHUB_CREATE_ISSUE_ab12", "remote_name": "GITHUB_CREATE_ISSUE",
         "description": "Creates a new issue in a repository. " * 12,
         "inputSchema": {"type": "object", "properties": {
             "owner": {"type": "string"}, "repo": {"type": "string"},
             "title": {"type": "string"}, "body": {"type": "string"}},
             "required": ["owner", "repo", "title"]}},
        {"name": "mcp__c1__GITHUB_LIST_REPOS_ab12", "remote_name": "GITHUB_LIST_REPOS",
         "description": "Lists repositories for the authenticated user.",
         "inputSchema": {"type": "object", "properties": {"per_page": {"type": "integer"}}}},
        {"name": "mcp__c1__GITHUB_GET_REPO_ab12", "remote_name": "GITHUB_GET_REPO",
         "description": "Fetches a single repository.",
         "inputSchema": {"type": "object", "properties": {"owner": {"type": "string"}}}},
    ]


def _katalog(monkeypatch, sorgu=None):
    from chat import platform_connectors as module
    monkeypatch.setattr(module, "list_tools", lambda user_id, cid: _araclar())
    return module.tool_catalog("u1", "c1", sorgu)


def test_arama_yoksa_sema_donmez(monkeypatch):
    katalog = _katalog(monkeypatch)
    assert len(katalog) == 3
    for satir in katalog:
        assert set(satir) == {"name", "remote_name", "description",
                              "parametreler", "zorunlu"}
        assert "inputSchema" not in satir
        assert len(satir["description"]) <= 183


def test_katalog_parametre_ve_zorunlu_alan_tasir(monkeypatch):
    satir = [a for a in _katalog(monkeypatch) if a["remote_name"] == "GITHUB_CREATE_ISSUE"][0]
    assert satir["parametreler"] == ["body", "owner", "repo", "title"]
    assert satir["zorunlu"] == ["owner", "repo", "title"]


def test_arama_ile_tam_sema_doner(monkeypatch):
    katalog = _katalog(monkeypatch, "issue")
    assert [a["remote_name"] for a in katalog] == ["GITHUB_CREATE_ISSUE"]
    assert katalog[0]["inputSchema"]["required"] == ["owner", "repo", "title"]


def test_arama_harf_duyarsiz_ve_uzak_adla_eslesir(monkeypatch):
    assert [a["remote_name"] for a in _katalog(monkeypatch, "GitHub_List")] == ["GITHUB_LIST_REPOS"]
    # "repo" aciklamalarda da geciyor: arama ad, uzak ad ve aciklamayi birlikte tarar.
    assert [a["remote_name"] for a in _katalog(monkeypatch, "  repo  ")] == [
        "GITHUB_CREATE_ISSUE", "GITHUB_LIST_REPOS", "GITHUB_GET_REPO"]


def test_eslesme_yoksa_bos_liste(monkeypatch):
    assert _katalog(monkeypatch, "stripe") == []


def test_yuzlerce_arac_katalogu_baglami_sismez(monkeypatch):
    from chat import platform_connectors as module

    def uret():
        liste = []
        for i in range(300):
            liste.append({
                "name": "mcp__c1__GITHUB_ARAC_%03d_ab12" % i,
                "remote_name": "GITHUB_ARAC_%03d" % i,
                "description": ("Belirli bir depoda islem yapar ve sonucu doner. " * 8).strip(),
                "inputSchema": {"type": "object", "properties": {
                    alan: {"type": "string", "description": "Aciklama metni " * 6}
                    for alan in ("owner", "repo", "baslik", "govde", "etiket", "dal")},
                    "required": ["owner", "repo"]},
            })
        return liste

    monkeypatch.setattr(module, "list_tools", lambda user_id, cid: uret())
    tam = json.dumps(uret(), ensure_ascii=False)
    katalog = json.dumps(module.tool_catalog("u1", "c1"), ensure_ascii=False)
    assert len(katalog) < len(tam) * 0.4


def test_baglanti_araclari_sorguyu_iletir(monkeypatch):
    from tools import platform as module

    class SahteKontrol:
        def check_cancelled(self):
            return None

    class SahteCtx:
        allowed_tools = None
        control = SahteKontrol()
        user_id = "u1"
        workspace_id = "w"
        run_id = "r"

    cagrilar = []
    monkeypatch.setattr(module, "require", lambda: SahteCtx())
    monkeypatch.setattr("chat.platform_connectors.tool_catalog",
                        lambda uid, cid, sorgu=None: cagrilar.append((uid, cid, sorgu)) or [])
    module.execute("baglanti_araclari", {"baglanti_id": "c1", "sorgu": "issue"})
    assert cagrilar == [("u1", "c1", "issue")]


def test_arac_semasi_sorgu_parametresi_tasir():
    from tools.definitions import BAGLANTI_ARACLARI
    sema = BAGLANTI_ARACLARI["function"]["parameters"]
    assert "sorgu" in sema["properties"]
    assert sema["required"] == ["baglanti_id"]
