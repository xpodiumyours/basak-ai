"""Vercel kalici web calisma katmani.

Bu dosya ikinci bir Basak beyni kurmaz. HTTP + statik ekran koprusudur;
sohbet her zaman mevcut Python cekirdeginin chat.flow.mesaj_isle yolundan
gecer. Vercel'de kalici disk varsayilmaz; tarayici gecmisi istekte tasir.
"""

import asyncio
import base64
import binascii
import json
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
WEB = BASE / "web"

if os.environ.get("VERCEL"):
    os.environ.setdefault(
        "BASAK_STATE_DIR", os.path.join(tempfile.gettempdir(), "basak")
    )

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

_BEYIN = None
_TOOLS = None
# Kişilik artık isteğe göre chat.prompts.kisilik_blogu ile üretilir;
# sabit "Casper'in asistanısın" metni web'de yabancıya sızmaz.


def _cekirdek():
    global _BEYIN, _TOOLS
    if _BEYIN is None or _TOOLS is None:
        from brain import Brain
        from tools import TOOLS
        _BEYIN = Brain()
        _TOOLS = TOOLS
    return _BEYIN, _TOOLS


def _kimlik(request: Request):
    """Istegin kisi kimligi; None = 401 gerekir.

    Once imzali cookie; gecerliyse chat.kimlik contextvar'ina kurulur.
    Kullanici tablosu bosken tek-kullanici modu (casper) — eski
    yerel/test davranisi bozulmaz.
    """
    import kullanici as kullanici_modulu
    from chat.kimlik import VARSAYILAN_KULLANICI, kullanici_kur

    token = request.cookies.get(kullanici_modulu.cookie_adi()) or ""
    kid = kullanici_modulu.oturum_coz(token)
    if kid is None:
        if not kullanici_modulu.giris_zorunlu_mu():
            kid = VARSAYILAN_KULLANICI
        else:
            return None
    kullanici_kur(kid)
    return kid


def _giris_engeli():
    return JSONResponse({"error": "giris gerekli"}, status_code=401)


class _OlayToplayici:
    def __init__(self, istek):
        self.istek = istek
        self.olaylar = []
        self.cevap = ""
        self.kaynak = ""
        self.hata = ""

    def __call__(self, kod):
        try:
            if not isinstance(kod, str) or not kod.startswith("BasakUI."):
                return
            ad, icerik = kod[8:].split("(", 1)
            parca = json.loads("[%s]" % icerik.rsplit(")", 1)[0])
            olay = {"istek": self.istek, "tur": ad}
            if ad in ("parca", "error", "toolStatus"):
                olay["metin"] = parca[0] if parca else ""
            elif ad == "bitir":
                olay["cevap"] = parca[0] if parca else ""
                olay["kaynak"] = parca[1] if len(parca) > 1 else ""
                self.cevap = olay["cevap"]
                self.kaynak = olay["kaynak"]
            elif ad != "thinking":
                return
            if ad == "error":
                self.hata = olay.get("metin", "")
            self.olaylar.append(olay)
        except Exception:
            return


def _gecmis(body):
    sonuc = []
    for m in body.get("gecmis") or []:
        if not isinstance(m, dict):
            continue
        rol = m.get("role")
        icerik = m.get("content")
        if rol not in ("user", "assistant") or not isinstance(icerik, str):
            continue
        sonuc.append({"role": rol, "content": icerik})
    return sonuc


def _gorsel_kaydet(ek):
    if not isinstance(ek, dict) or ek.get("tur") != "image":
        return None
    data_url = ek.get("data_url")
    if not isinstance(data_url, str) or not data_url.startswith("data:image/"):
        raise ValueError("Gecersiz fotograf verisi")
    try:
        baslik, veri = data_url.split(",", 1)
        mime = baslik.split(";", 1)[0].split(":", 1)[1].lower()
        ham = base64.b64decode(veri, validate=True)
    except (ValueError, binascii.Error) as e:
        raise ValueError("Fotograf cozumlenemedi") from e
    if len(ham) > 10 * 1024 * 1024:
        raise ValueError("Fotograf 10 MB sinirini asiyor")
    uzanti = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(mime, ".jpg")
    yol = os.path.join(
        tempfile.gettempdir(), "basak-%s%s" % (uuid.uuid4().hex, uzanti)
    )
    with open(yol, "wb") as f:
        f.write(ham)
    return {
        "ad": os.path.basename(str(ek.get("ad") or "fotograf")),
        "tur": "image",
        "path": yol,
    }


@app.get("/api/durum")
async def durum(request: Request):
    beyin, tools = _cekirdek()
    try:
        zincir = beyin._bulut_zinciri(tools=True)
    except Exception:
        zincir = []
    modeller = []
    try:
        from brain import registry
        for ad, istemci in zincir:
            kart = registry.kart(ad)
            modeller.append({
                "ad": ad,
                "model": getattr(istemci, "model", None) or "dogrulanamadi",
                "gucleri": list(kart.get("gucleri") or []),
                "limit": {
                    "saatlik_istek": kart.get("saatlik_istek"),
                    "gunluk_istek": kart.get("gunluk_istek"),
                    "aylik_istek": kart.get("aylik_istek"),
                    "gunluk_token": kart.get("gunluk_token"),
                },
                "kullanim": {},
            })
    except Exception:
        pass
    return {
        "ok": bool(zincir),
        "runtime": "vercel",
        "commit": (os.environ.get("VERCEL_GIT_COMMIT_SHA") or "vercel")[:7],
        "saglayicilar": [ad for ad, _ in zincir],
        "beklenen_saglayicilar": [],
        "eksik_saglayicilar": [],
        "modeller": modeller,
        "arac_sayisi": len(tools),
        "tasima": "tek-http-cevap",
    }


@app.post("/api/sohbet")
async def sohbet(request: Request):
    kid = _kimlik(request)
    if kid is None:
        return _giris_engeli()
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Gecersiz JSON"}, status_code=400)
    metin = str((body or {}).get("metin") or "").strip()
    ek_yol = None
    try:
        ek = _gorsel_kaydet((body or {}).get("ek"))
        if ek:
            ek_yol = ek["path"]
            metin = (metin or "Bu goruntuyu acikla.") + (
                "\n\nKullanici bu mesaja bir dosya ekledi. "
                "Dosya verisi: %s" % json.dumps(
                    {"ad": ek["ad"], "tur": ek["tur"], "path": ek["path"]},
                    ensure_ascii=False,
                )
            )
        if not metin:
            return JSONResponse({"error": "Bos mesaj"}, status_code=400)

        beyin, tools = _cekirdek()
        kayit = _OlayToplayici(uuid.uuid4().hex[:12])

        def _kos():
            from chat.flow import mesaj_isle
            from chat.kimlik import kullanici_kur
            from chat.prompts import kisilik_blogu
            kullanici_kur(kid)  # thread contextvar'i — kisi izolasyonu
            misafir = bool((body or {}).get("misafir", False))
            mesaj_isle(
                metin,
                beyin,
                kisilik_blogu(kid, misafir=misafir),
                kayit,
                tools,
                misafir=misafir,
                gecmis_override=_gecmis(body or {}),
            )

        await asyncio.to_thread(_kos)
        if kayit.hata and not kayit.cevap:
            return {
                "ok": False,
                "istek": kayit.istek,
                "error": kayit.hata,
                "olaylar": kayit.olaylar,
            }
        return {
            "ok": bool(kayit.cevap),
            "istek": kayit.istek,
            "cevap": kayit.cevap,
            "kaynak": kayit.kaynak,
            "olaylar": kayit.olaylar,
        }
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse(
            {"error": "Basak calistirilamadi: %s" % str(e)[:300]},
            status_code=500,
        )
    finally:
        if ek_yol:
            try:
                os.remove(ek_yol)
            except OSError:
                pass


@app.get("/api/sohbetler")
async def sohbetler(request: Request):
    if _kimlik(request) is None:
        return _giris_engeli()
    return {"liste": []}


@app.post("/api/yeni")
async def yeni(request: Request):
    if _kimlik(request) is None:
        return _giris_engeli()
    return {"ok": True}


@app.post("/api/giris")
async def giris(request: Request):
    """POST /api/giris — ad + sifre -> HttpOnly cookie."""
    import kullanici as kullanici_modulu

    try:
        uzunluk = int(request.headers.get("content-length") or 0)
    except ValueError:
        uzunluk = 0
    if uzunluk <= 0 or uzunluk > 4096:
        return JSONResponse({"error": "govde boyu"}, status_code=400)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "gecersiz json"}, status_code=400)
    body = body or {}
    ad = str(body.get("ad") or "").strip()
    sifre = str(body.get("sifre") or "")
    kid = kullanici_modulu.giris_kontrol(ad, sifre)
    if kid is None:
        return JSONResponse(
            {"error": "ad veya sifre hatali"}, status_code=401)
    token = kullanici_modulu.oturum_tokeni_uret(kid)
    resp = JSONResponse(
        {"ok": True, "kullanici": kid},
        headers={"Cache-Control": "no-store"},
    )
    resp.set_cookie(
        kullanici_modulu.cookie_adi(), token,
        max_age=7 * 24 * 3600, path="/", httponly=True, samesite="lax",
    )
    return resp


@app.post("/api/cikis")
async def cikis():
    """POST /api/cikis — cookie'yi siler."""
    import kullanici as kullanici_modulu

    resp = JSONResponse(
        {"ok": True}, headers={"Cache-Control": "no-store"})
    resp.set_cookie(
        kullanici_modulu.cookie_adi(), "",
        max_age=0, path="/", httponly=True, samesite="lax",
    )
    return resp


app.mount("/", StaticFiles(directory=str(WEB), html=True), name="web")
