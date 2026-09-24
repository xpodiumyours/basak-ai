"""Vercel kalici web calisma katmani.

Bu dosya ikinci bir Basak beyni kurmaz. HTTP + statik ekran koprusudur;
sohbet her zaman mevcut Python cekirdeginin chat.flow.mesaj_isle yolundan
gecer. Vercel'de kalici disk varsayilmaz; tarayici gecmisi istekte tasir.
"""

import asyncio
import base64
import binascii
import hmac
import json
import os
import tempfile
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
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
_PREVIEW_COOKIE = "basak_preview_oturum"
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


def _token_kimligi(request: Request):
    """X-Basak-Token dogruysa varsayilan kisi, degilse None.

    Uretimde ad+sifre girisi henuz yok (kullanici tablosu gecici diskte,
    kalici degil). Bu yuzden ortam tokeni tek gecerli ikinci kapidir.
    Karsilastirma hmac.compare_digest ile yapilir; gelen deger ASCII disi
    ise (or. "Basak123" icindeki Turkce s) compare_digest TypeError
    firlatir ve istek 500 doner — olculdu 2026-09-23. ASCII disi deger
    zaten gecersizdir: cokme yerine None.
    """
    from chat.kimlik import VARSAYILAN_KULLANICI

    beklenen = (os.environ.get("BASAK_WEB_TOKEN") or "").strip()
    if not beklenen or not beklenen.isascii():
        return None
    gelen = (request.headers.get("X-Basak-Token") or "").strip()
    if not gelen or not gelen.isascii():
        return None
    if not hmac.compare_digest(gelen, beklenen):
        return None
    return VARSAYILAN_KULLANICI


def _preview_mi():
    """Yalniz Vercel Preview deployment'i mi? Production degil."""
    return (os.environ.get("VERCEL_ENV") or "").strip().lower() == "preview"


def _preview_kimligi(request: Request):
    """Preview'e ozel, kalici veriye yetki vermeyen tarayici kimligi."""
    kid = (request.cookies.get(_PREVIEW_COOKIE) or "").strip().lower()
    if len(kid) != 17 or not kid.startswith("p"):
        return None
    if any(c not in "0123456789abcdef" for c in kid[1:]):
        return None
    return kid


def _preview_cerezi(resp, kid):
    resp.set_cookie(
        _PREVIEW_COOKIE,
        kid,
        max_age=24 * 3600,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return resp


def _uretim_kapisi_hazir():
    """Uretimde kimlik karari verilebilir mi? Preview ayri ve izoledir."""
    import kullanici as kullanici_modulu

    if _preview_mi():
        return True
    if not kullanici_modulu.uretim_mi():
        return True
    return bool(kullanici_modulu.env_anahtari()
                or (os.environ.get("BASAK_WEB_TOKEN") or "").strip())



_HAFIZA_SIFIRLAMA_ANAHTARI = "clean_start_20260923_v1"


def _hafizayi_bir_kez_sifirla():
    """Canlı hafızayı bir kez tamamen boşaltır ve eski 61 testi geri getirmez.

    Kullanıcı isteğiyle 23 Eylül 2026'da temiz başlangıç kararı alındı.
    İşlem üretimde advisory lock ile tek kez yapılır. Eski ölçüm kaynakları
    da temizlenir; böylece memory/postgres.py içindeki eski taşıma yolu
    daha sonra 61 kaydı yeniden içeri alamaz.
    """
    import kullanici as kullanici_modulu

    if not kullanici_modulu.uretim_mi():
        return True

    dsn = ""
    for ad in ("DATABASE_URL", "POSTGRES_URL", "NEON_DATABASE_URL"):
        dsn = (os.environ.get(ad) or "").strip()
        if dsn:
            break
    if not dsn:
        return False

    try:
        import psycopg
        with psycopg.connect(
            dsn, autocommit=False, connect_timeout=10
        ) as conn:
            try:
                conn.prepare_threshold = None
            except Exception:
                pass
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_advisory_xact_lock(hashtext("
                    "'basak_clean_start_20260923_v1'))"
                )
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS basak_memory_meta ("
                    " user_id TEXT NOT NULL,"
                    " anahtar TEXT NOT NULL,"
                    " deger TEXT NOT NULL,"
                    " PRIMARY KEY (user_id, anahtar)"
                    ")"
                )
                cur.execute(
                    "SELECT deger FROM basak_memory_meta "
                    "WHERE user_id=%s AND anahtar=%s",
                    ("__system__", _HAFIZA_SIFIRLAMA_ANAHTARI),
                )
                satir = cur.fetchone()
                if satir is not None and str(satir[0]).strip().lower() == "true":
                    conn.commit()
                    return True

                # Aktif kullanıcı hafızası.
                cur.execute("SELECT to_regclass(%s)", ("public.basak_memories",))
                if cur.fetchone()[0] is not None:
                    cur.execute("DELETE FROM public.basak_memories")

                # 61 deneme anısının geldiği eski kaynaklar.
                cur.execute("SELECT to_regclass(%s)", ("basak.anilar",))
                if cur.fetchone()[0] is not None:
                    cur.execute('DELETE FROM "basak"."anilar"')
                cur.execute("SELECT to_regclass(%s)", ("public.memories",))
                if cur.fetchone()[0] is not None:
                    cur.execute("DELETE FROM public.memories")

                # Eski kişi/meta işaretleri de yeni başlangıca taşınmaz.
                cur.execute("DELETE FROM basak_memory_meta")
                cur.execute(
                    "INSERT INTO basak_memory_meta "
                    "(user_id, anahtar, deger) VALUES (%s,%s,%s)",
                    ("__system__", _HAFIZA_SIFIRLAMA_ANAHTARI, "true"),
                )
            conn.commit()
        return True
    except Exception:
        return False


def _kimlik(request: Request):
    """Istegin kisi kimligi; None = 401/503 gerekir.

    Preview: Vercel korumasi arkasinda, izole ve kalici hafizasiz test
    kimligi. Production: imzali cookie/token ve fail-closed kurali.
    """
    import kullanici as kullanici_modulu
    from chat.kimlik import VARSAYILAN_KULLANICI, kullanici_kur

    if _preview_mi():
        kid = _preview_kimligi(request)
        if kid is None:
            return None
        kullanici_kur(kid)
        return kid

    if kullanici_modulu.uretim_mi() and not _hafizayi_bir_kez_sifirla():
        return None

    token = request.cookies.get(kullanici_modulu.cookie_adi()) or ""
    try:
        kid = kullanici_modulu.oturum_coz(token) if token else None
    except RuntimeError:
        # Uretimde oturum anahtari yok — imza dogrulanamaz, kabul edilmez.
        kid = None
    if kid is None:
        if kullanici_modulu.uretim_mi():
            kid = _token_kimligi(request)
            if kid is None:
                return None
        elif not kullanici_modulu.giris_zorunlu_mu():
            kid = VARSAYILAN_KULLANICI
        else:
            return None
    kullanici_kur(kid)
    return kid


def _giris_engeli():
    """Kimlik veya temiz başlangıç hazır değilse güvenli biçimde dur."""
    import kullanici as kullanici_modulu
    if _preview_mi():
        return JSONResponse({"error": "preview kimligi gerekli"}, status_code=401)
    if kullanici_modulu.uretim_mi() and not _hafizayi_bir_kez_sifirla():
        return JSONResponse(
            {"error": "kalici hafiza temiz baslangica hazirlanamadi"},
            status_code=503,
        )
    if not _uretim_kapisi_hazir():
        return JSONResponse(
            {"error": "sunucu kimlik dogrulayamiyor: BASAK_OTURUM_ANAHTARI "
                      "veya BASAK_WEB_TOKEN ortam degiskeni tanimli degil"},
            status_code=503,
        )
    return JSONResponse({"error": "giris gerekli"}, status_code=401)


_AKIS_MIME = "application/x-ndjson"
_AKIS_SESSIZLIK_SN = 10.0
_AKIS_SON = object()


class _AkisIptal(Exception):
    """İstemci akışı kapattığında kalan Başak adımlarını bırak."""


def _canli_akis_isteniyor(request: Request):
    """Yeni web istemcisi canli NDJSON akis istiyor mu?

    Accept basligi yoksa mevcut toplu JSON davranisi aynen korunur.
    """
    return _AKIS_MIME in (request.headers.get("accept") or "").lower()


async def _canli_olaylar(kuyruk, gorev, istek, iptal=None):
    """Worker olaylarini ayni HTTP yanitinda satir satir tasir.

    bitir/error ekrana hemen gider; ancak worker tamamen bitmeden stream
    kapanmaz. İstemci bağlantıyı kapatırsa iptal bayrağı worker'a taşınır.
    """
    gorev.add_done_callback(lambda _g: kuyruk.put_nowait(_AKIS_SON))
    terminal_goruldu = False

    try:
        while True:
            try:
                olay = await asyncio.wait_for(
                    kuyruk.get(), timeout=_AKIS_SESSIZLIK_SN
                )
            except asyncio.TimeoutError:
                yield json.dumps(
                    {"istek": istek, "tur": "ping"},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ) + "\n"
                continue

            if olay is _AKIS_SON:
                if not terminal_goruldu:
                    yield json.dumps(
                        {
                            "istek": istek,
                            "tur": "error",
                            "metin": "Basak yaniti tamamlanmadan bitti.",
                        },
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ) + "\n"
                return

            if isinstance(olay, dict) and olay.get("tur") in ("bitir", "error"):
                terminal_goruldu = True

            yield json.dumps(
                olay, ensure_ascii=False, separators=(",", ":")
            ) + "\n"
    except asyncio.CancelledError:
        if iptal is not None:
            iptal.set()
        raise
    finally:
        if iptal is not None and not gorev.done():
            iptal.set()


class _OlayToplayici:
    def __init__(self, istek, yayinla=None, iptal=None):
        self.istek = istek
        self.olaylar = []
        self.cevap = ""
        self.kaynak = ""
        self.hata = ""
        self.yayinla = yayinla
        self.iptal = iptal

    def iptal_edildi(self):
        return bool(self.iptal is not None and self.iptal.is_set())

    def olay(self, tur, **veri):
        if self.iptal_edildi():
            raise _AkisIptal()
        olay = {"istek": self.istek, "tur": str(tur)}
        olay.update(veri)
        self.olaylar.append(olay)
        if self.yayinla is not None:
            try:
                self.yayinla(olay)
            except Exception:
                pass
        return olay

    def __call__(self, kod):
        if self.iptal_edildi():
            raise _AkisIptal()
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
            if self.yayinla is not None:
                try:
                    self.yayinla(olay)
                except Exception:
                    pass
        except _AkisIptal:
            raise
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



def _oturum_cerezi(resp, kid):
    """Kimliği JS'nin okuyamadığı imzalı çerezde bir yıl korur."""
    import kullanici as kullanici_modulu

    token = kullanici_modulu.oturum_tokeni_uret(
        kid, omur_sn=365 * 24 * 3600
    )
    resp.set_cookie(
        kullanici_modulu.cookie_adi(), token,
        max_age=365 * 24 * 3600,
        path="/",
        httponly=True,
        secure=kullanici_modulu.uretim_mi(),
        samesite="lax",
    )
    return resp


@app.post("/api/kimlik")
async def kimlik_hazirla(request: Request):
    """Kayıt/giriş olmadan tarayıcıya ayrı Başak ID verir."""
    import kullanici as kullanici_modulu
    from chat.kimlik import kullanici_kur

    if _preview_mi():
        kid = _preview_kimligi(request) or ("p" + uuid.uuid4().hex[:16])
        kullanici_kur(kid)
        resp = JSONResponse({
            "ok": True,
            "kullanici": kid,
            "basak_id": "Preview " + kid[-8:],
            "kayit_gerekli": False,
            "preview": True,
            "kalici_hafiza": False,
        }, headers={"Cache-Control": "no-store"})
        return _preview_cerezi(resp, kid)

    if kullanici_modulu.uretim_mi() and not _hafizayi_bir_kez_sifirla():
        return _giris_engeli()

    kid = _kimlik(request)
    if kid is None:
        if not _uretim_kapisi_hazir():
            return _giris_engeli()
        try:
            kid = kullanici_modulu.yeni_anonim_kimlik()
            kullanici_kur(kid)
        except RuntimeError:
            return _giris_engeli()

    try:
        resp = JSONResponse({
            "ok": True,
            "kullanici": kid,
            "basak_id": kullanici_modulu.gorunur_kimlik(kid),
            "kayit_gerekli": False,
        }, headers={"Cache-Control": "no-store"})
        return _oturum_cerezi(resp, kid)
    except RuntimeError:
        return _giris_engeli()


@app.get("/api/durum")
async def durum(request: Request):
    # 2026-09-23: bu uc kimliksizdi — saglayici listesi, model adlari,
    # commit sha ve arac sayisi tokensiz okunabiliyordu. Canlidaki eski
    # surum (a98ee76) bu ucu koruyordu; kisi-hafiza commit'inde koruma
    # dustu. Olculdu ve geri konuldu.
    if _kimlik(request) is None:
        return _giris_engeli()
    beyin, tools = _cekirdek()
    try:
        zincir = beyin._bulut_zinciri(tools=True)
    except Exception:
        zincir = []
    modeller = []
    try:
        from brain import registry
        from brain.stats import model_stats_al
        istat = model_stats_al()
        for ad, istemci in zincir:
            kart = registry.kart(ad)
            kullan = {}
            try:
                giris_saat = istat.istek_sayisi(ad, "saat")
                istek_gun = istat.istek_sayisi(ad, "gun")
                istek_ay = istat.istek_sayisi(ad, "ay")
                tin, tout = istat.token_bugun(ad)
                kullan = {
                    "saatlik_istek": giris_saat,
                    "gunluk_istek": istek_gun,
                    "aylik_istek": istek_ay,
                    "gunluk_token_giris": tin,
                    "gunluk_token_cikis": tout,
                    "kalan_saatlik_istek": (
                        None if kart.get("saatlik_istek") is None
                        else max(0, int(kart["saatlik_istek"]) - giris_saat)),
                    "kalan_gunluk_istek": (
                        None if kart.get("gunluk_istek") is None
                        else max(0, int(kart["gunluk_istek"]) - istek_gun)),
                    "kalan_aylik_istek": (
                        None if kart.get("aylik_istek") is None
                        else max(0, int(kart["aylik_istek"]) - istek_ay)),
                    "kalan_gunluk_token": (
                        None if not kart.get("gunluk_token")
                        else max(0, int(kart["gunluk_token"]) - tin - tout)),
                }
            except Exception:
                kullan = {}
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
                "kullanim": kullan,
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
        "tasima": "canli-ndjson",
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
    akis_kuruldu = False
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
        akis = _canli_akis_isteniyor(request)
        dongu = asyncio.get_running_loop() if akis else None
        kuyruk = asyncio.Queue() if akis else None
        iptal = threading.Event() if akis else None

        def _yayinla(olay):
            if dongu is not None and kuyruk is not None:
                dongu.call_soon_threadsafe(kuyruk.put_nowait, olay)

        kayit = _OlayToplayici(
            uuid.uuid4().hex[:12],
            yayinla=_yayinla if akis else None,
            iptal=iptal,
        )

        def _kos(akis_hatasi=False, gecici_temizle=False):
            try:
                from chat.flow import mesaj_isle
                from chat.kimlik import kullanici_kur
                from chat.prompts import kisilik_blogu
                kullanici_kur(kid)  # thread contextvar'i — kisi izolasyonu
                # Preview normal Başak davranışını çalıştırır. Veri/hafıza
                # izolasyonu memory katmanında Preview'e özel /tmp SQLite ile
                # yapılır; davranış misafir moduna zorlanmaz.
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
            except _AkisIptal:
                return
            except Exception as e:
                if not akis_hatasi:
                    raise
                _yayinla({
                    "istek": kayit.istek,
                    "tur": "error",
                    "metin": "Basak calistirilamadi: %s" % str(e)[:300],
                })
            finally:
                if gecici_temizle and ek_yol:
                    try:
                        os.remove(ek_yol)
                    except OSError:
                        pass

        if akis:
            gorev = asyncio.create_task(
                asyncio.to_thread(_kos, True, True)
            )
            akis_kuruldu = True
            return StreamingResponse(
                _canli_olaylar(kuyruk, gorev, kayit.istek, iptal),
                media_type=_AKIS_MIME,
                headers={
                    "Cache-Control": "no-cache, no-transform",
                    "X-Content-Type-Options": "nosniff",
                },
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
        if ek_yol and not akis_kuruldu:
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
        max_age=0, path="/", httponly=True,
        secure=kullanici_modulu.uretim_mi(), samesite="lax",
    )
    return resp


app.mount("/", StaticFiles(directory=str(WEB), html=True), name="web")
