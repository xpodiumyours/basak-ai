import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
import app


def test_html_girisi_onbelleklenmez():
    with TestClient(app.app) as c:
        r = c.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert r.headers.get("cache-control") == "no-store"


def test_varliklar_pin_ile_onbelleklenebilir():
    with TestClient(app.app) as c:
        r = c.get("/app.js")
    assert r.status_code == 200
    assert r.headers.get("cache-control") != "no-store"
