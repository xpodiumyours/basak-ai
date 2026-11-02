"""Baglanti araclarinin hata yollari: opak grup hatasi ve olu baglanti."""
import asyncio

import pytest


def test_hata_metni_ic_ice_gruplari_acar():
    from chat.hata import hata_metni
    ic = ExceptionGroup("ic", [PermissionError("Composio icin yeniden dogrulama gerekli")])
    dis = ExceptionGroup("unhandled errors in a TaskGroup", [ic])
    metin = hata_metni(dis)
    assert "yeniden dogrulama gerekli" in metin
    assert "TaskGroup" not in metin


def test_hata_metni_grup_degilse_aynen_doner():
    from chat.hata import hata_metni
    assert hata_metni(ValueError("duz hata")) == "duz hata"


def test_execute_sync_grup_hatasinin_nedenini_verir(monkeypatch):
    from chat.platform_mcp import MCPService
    service = MCPService(store=object())

    async def patlat(*a, **k):
        raise ExceptionGroup("unhandled errors in a TaskGroup (1 sub-exception)",
                             [RuntimeError("MCP adresine ulasilamadi")])

    monkeypatch.setattr(service, "execute", patlat)
    with pytest.raises(RuntimeError) as hata:
        service.execute_sync("u1", "c1", "arac", {})
    assert "MCP adresine ulasilamadi" in str(hata.value)
    assert "TaskGroup" not in str(hata.value)


def test_arac_cozumleme_uzak_slug_ve_harf_farki():
    from chat.platform_mcp import MCPService
    tools = [{"name": "mcp__c1__GITHUB_GET_REPO_ab12cd34",
              "remote_name": "GITHUB_GET_REPO"}]
    assert MCPService._eslesen_arac(tools, "mcp__c1__GITHUB_GET_REPO_ab12cd34") is tools[0]
    assert MCPService._eslesen_arac(tools, "GITHUB_GET_REPO") is tools[0]
    assert MCPService._eslesen_arac(tools, "github_get_repo") is tools[0]


def test_bilinmeyen_arac_adi_katalog_buyuklugunu_soyler():
    from chat.platform_mcp import MCPService
    tools = [{"name": "mcp__c1__GITHUB_GET_REPO_ab12cd34",
              "remote_name": "GITHUB_GET_REPO"}]
    with pytest.raises(PermissionError) as hata:
        MCPService._eslesen_arac(tools, "GITHUB_YOK")
    assert "1 arac" in str(hata.value)
    assert "GITHUB_GET_REPO" in str(hata.value)


def test_composio_baglantisi_mcp_yoluna_girmez():
    from chat.platform_mcp import MCPService
    service = MCPService(store=object())
    baglanti = {"id": "c1", "provider": "mcp", "status": "connected",
                "scopes": [], "metadata": {
                    "composio_session_id": "trs_x",
                    "url": "https://backend.composio.dev/tool_router/trs_x/mcp"}}

    async def kos():
        async with service._session("u1", baglanti):
            pass

    with pytest.raises(PermissionError) as hata:
        asyncio.run(kos())
    assert "REST" in str(hata.value)


def test_oturumsuz_composio_baglantisi_sessizce_mcp_denemez(monkeypatch):
    from chat.platform_mcp import MCPService
    service = MCPService(store=object())
    baglanti = {"id": "c1", "provider": "mcp", "status": "connected",
                "scopes": [], "metadata": {
                    "url": "https://backend.composio.dev/tool_router/trs_x/mcp",
                    "tools": [], "allowed_tools": []}}
    monkeypatch.setattr(service, "_owned", lambda u, c: baglanti)
    with pytest.raises(PermissionError) as hata:
        asyncio.run(service.execute("u1", "c1", "arac", {}))
    assert "yeniden kurun" in str(hata.value)


def test_etkin_olmayan_baglanti_arac_calistirmaz(monkeypatch):
    from chat import platform_connectors as module

    class SahteMagaza:
        def get(self, user_id, cid):
            return {"id": cid, "provider": "mcp", "status": "revoked", "metadata": {}}

    monkeypatch.setattr(module, "ConnectionStore", lambda: SahteMagaza())
    with pytest.raises(PermissionError) as hata:
        module.execute("u1", "c1", "arac", {})
    assert "etkin degil" in str(hata.value)


def test_baglanti_liste_olu_kayitlari_modele_sunmaz(monkeypatch):
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

    class SahteMagaza:
        def list(self, user_id):
            return [{"id": "olu", "status": "revoked"},
                    {"id": "canli", "status": "connected"}]

    monkeypatch.setattr(module, "require", lambda: SahteCtx())
    monkeypatch.setattr(module, "_connections", lambda: SahteMagaza())
    sonuc = module.execute("baglanti_liste", {})
    assert [c["id"] for c in sonuc["result"]] == ["canli"]
