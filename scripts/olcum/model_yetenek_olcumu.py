"""scripts/olcum/model_yetenek_olcumu.py — gerçek araç/görüntü ölçümü.

Neden bu dosya: "hangi sağlayıcı araç çağırabiliyor, hangisi görüntüyü
gerçekten okuyor, tur başına ne kadar kota harcıyor" sorusu belgeye değil
canlıya dayanmalı. Bu script her hazır sağlayıcının GERÇEK adaptörünü
kullanır; sahte yanıt üretmez, metin içindeki JSON'u tool_call saymaz.

Ölçüm (sağlayıcı başına en fazla 3 çağrı):
  1) araç turu  — üretimdeki tool_choice ile gerçek native tool_call
  2) devam turu — tool sonucu geri verilince turun tamamlanması
  3) görüntü    — rastgele metin taşıyan PNG; cevap metni birebir eşleşmeli

Ayrıca `tools.image_analyzer.image_analyze` üretim yolu bir kez ölçülür.

Kota davranışı: tur başına gerçek token kullanımı, sağlayıcının döndürdüğü
rate-limit başlıkları ve 429/401 gibi gerçek hata durumları kaydedilir.
"Limitsiz" denmez; ölçülmeyen tavan bilinmeyen olarak kalır.

Kosum:
    python scripts/olcum/model_yetenek_olcumu.py
    python scripts/olcum/model_yetenek_olcumu.py --sadece groq,nvidia
    python scripts/olcum/model_yetenek_olcumu.py --kuru

Çıktı:
    docs/olcum-model-yetenek.md      (üretilmiş rapor, ttl 24 saat)
    data/model-yetenek-olcumu.json   (ham kayıt)
"""

import argparse
import base64
import inspect
import io
import json
import logging
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

logger = logging.getLogger(__name__)

TTL_SAAT = 24
RAPOR = KOK / "docs" / "olcum-model-yetenek.md"
HAM = KOK / "data" / "model-yetenek-olcumu.json"

# Sağlayıcıya gönderilen tek araç: yan etkisi yok, argümanı tek sayı.
PING = {
    "type": "function",
    "function": {
        "name": "ping",
        "description": "Verilen sayıyı aynen döndürür.",
        "parameters": {
            "type": "object",
            "properties": {"deger": {"type": "integer"}},
            "required": ["deger"],
        },
    },
}

_SIR_DESENLERI = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{8,}", re.IGNORECASE),
    re.compile(r"(?i)(api[_\- ]?key|token|parola|password)\s*[=:]\s*\S+"),
    # Sağlayıcı hata gövdeleri hesap kimliği taşıyabilir; rapora girmez.
    re.compile(r"\b(?:org|user|acct|account)_[A-Za-z0-9]{6,}\b"),
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}"),
]
_KOTA_BASLIKLARI = (
    "x-ratelimit-limit-requests",
    "x-ratelimit-remaining-requests",
    "x-ratelimit-limit-tokens",
    "x-ratelimit-remaining-tokens",
    "ratelimit-limit",
    "ratelimit-remaining",
    "retry-after",
)


def _temiz(metin, sinir=240):
    """Hata metnini sır ve gürültüden arındırır."""
    s = str(metin or "").replace("\n", " ")
    for desen in _SIR_DESENLERI:
        s = desen.sub("***", s)
    return s[:sinir]


def _simdi():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _commit():
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(KOK),
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        kirli = subprocess.run(
            ["git", "status", "--porcelain"], cwd=str(KOK),
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        return sha + ("-dirty" if kirli else "")
    except (OSError, subprocess.SubprocessError):
        return "bilinmiyor"


def _token_resmi():
    """Rastgele harf/rakam taşıyan küçük PNG üretir.

    Rastgele metin, metin-only modelin renk tahminiyle doğru cevap
    vermesini engeller; görüntüyü gerçekten okuyan model kodu yazar.
    """
    from PIL import Image, ImageDraw, ImageFont

    kod = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
                  for _ in range(5))
    resim = Image.new("RGB", (360, 120), (255, 255, 255))
    cizim = ImageDraw.Draw(resim)
    yazi = None
    for aday in ("arial.ttf", "DejaVuSans.ttf", "calibri.ttf"):
        try:
            yazi = ImageFont.truetype(aday, 64)
            break
        except OSError:
            continue
    if yazi is None:
        yazi = ImageFont.load_default()
    cizim.text((24, 22), kod, fill=(0, 0, 0), font=yazi)
    tampon = io.BytesIO()
    resim.save(tampon, format="PNG")
    return kod, tampon.getvalue()


def _veri_urlu(png):
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def _kota_gozlemi(istemci):
    """Ayrı ve minimal bir çağrıyla rate-limit başlıklarını okur.

    Adaptörün dönüşü ham HTTP yanıtını taşımadığı için bu tek çağrı
    `with_raw_response` kullanır; araç/görüntü ölçümüne karışmaz.
    """
    try:
        ham = istemci.client.chat.completions.with_raw_response.create(
            model=getattr(istemci, "model", None),
            messages=[{"role": "user", "content": "ping"}],
        )
        basliklar = {}
        for ad in _KOTA_BASLIKLARI:
            deger = ham.headers.get(ad)
            if deger is not None:
                basliklar[ad] = str(deger)
        return {"ok": True, "durum": ham.status_code,
                "basliklar": basliklar}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "hata": _hata(e)}


def _zaman_asimi(istemci, saniye):
    """Adaptörün kendi OpenAI istemcisine üst sınır koyar."""
    try:
        istemci.client = istemci.client.with_options(
            timeout=float(saniye), max_retries=0)
    except (AttributeError, TypeError):
        logger.debug("istemciye zaman aşımı konulamadı", exc_info=True)


def _cagri_kwargulari(istemci, tool_choice):
    """Adaptörün gerçekten kabul ettiği argümanları seçer."""
    try:
        parametreler = inspect.signature(istemci.cevapla).parameters
    except (TypeError, ValueError):
        parametreler = {}
    kw = {}
    if "tool_choice" in parametreler:
        kw["tool_choice"] = tool_choice
    return kw


def _hata(e):
    durum = getattr(e, "status_code", None)
    if durum is None:
        yanit = getattr(e, "response", None)
        durum = getattr(yanit, "status_code", None)
    return {"tur": type(e).__name__, "durum": durum, "mesaj": _temiz(e)}


def _kullanim(yanit):
    k = yanit.get("_kullanim") if isinstance(yanit, dict) else None
    return k if isinstance(k, dict) else None


def _arac_turu(istemci, tool_choice):
    t0 = time.time()
    kayit = {"ok": False, "tool_choice": tool_choice}
    try:
        yanit = istemci.cevapla(
            [{"role": "user", "content": "ping aracını deger=42 ile çağır."}],
            tools=[PING], **_cagri_kwargulari(istemci, tool_choice))
        kayit["sure_sn"] = round(time.time() - t0, 2)
        kayit["token"] = _kullanim(yanit)
        araclar = []
        for cagri in (yanit.get("tool_calls") or []):
            fonksiyon = (cagri or {}).get("function") or {}
            araclar.append({
                "id": cagri.get("id"),
                "ad": fonksiyon.get("name"),
                "arguman": _temiz(fonksiyon.get("arguments"), 120),
            })
        kayit["araclar"] = araclar
        kayit["metin"] = _temiz(yanit.get("content"), 160)
        kayit["ok"] = bool(araclar)
        if not araclar:
            kayit["neden"] = "native tool_call yok"
        return kayit, yanit
    except Exception as e:  # noqa: BLE001 - her sağlayıcı hatası kayda geçer
        kayit["sure_sn"] = round(time.time() - t0, 2)
        kayit["hata"] = _hata(e)
        return kayit, None


def _devam_turu(istemci, ilk_mesajlar, ilk_yanit, tool_choice):
    """Tool sonucu geri verilince tur tamamlanıyor mu?"""
    t0 = time.time()
    kayit = {"ok": False}
    araclar = ilk_yanit.get("tool_calls") if isinstance(ilk_yanit, dict) else None
    if not araclar:
        kayit["neden"] = "ilk turda araç yok"
        return kayit
    cagri = araclar[0]
    cagri_id = cagri.get("id") or "cagri-1"
    ad = ((cagri.get("function") or {}).get("name")) or "ping"
    mesajlar = list(ilk_mesajlar) + [
        {"role": "assistant", "content": "", "tool_calls": araclar},
        {"role": "tool", "tool_call_id": cagri_id,
         "name": ad, "content": "42"},
    ]
    try:
        yanit = istemci.cevapla(
            mesajlar, tools=[PING], **_cagri_kwargulari(istemci, tool_choice))
        kayit["sure_sn"] = round(time.time() - t0, 2)
        kayit["token"] = _kullanim(yanit)
        kayit["metin"] = _temiz(yanit.get("content"), 160)
        kayit["ok"] = bool(yanit.get("content") or yanit.get("tool_calls"))
        if not kayit["ok"]:
            kayit["neden"] = "boş yanıt"
        return kayit
    except Exception as e:  # noqa: BLE001
        kayit["sure_sn"] = round(time.time() - t0, 2)
        kayit["hata"] = _hata(e)
        return kayit


def _goruntu_turu(istemci, kod, url):
    """Rastgele kodu görüntüden okuyabiliyor mu?"""
    t0 = time.time()
    kayit = {"ok": False, "beklenen": kod}
    try:
        yanit = istemci.cevapla([{
            "role": "user",
            "content": [
                {"type": "text",
                 "text": "Görüntüdeki büyük harf ve rakamlardan oluşan "
                         "metni aynen yaz. Yalnız metni yaz."},
                {"type": "image_url", "image_url": {"url": url}},
            ],
        }])
        kayit["sure_sn"] = round(time.time() - t0, 2)
        kayit["token"] = _kullanim(yanit)
        metin = str(yanit.get("content") or "")
        kayit["cevap"] = _temiz(metin, 120)
        kayit["ok"] = kod in metin.upper()
        if not kayit["ok"]:
            kayit["neden"] = "beklenen kod cevapta yok"
        return kayit
    except Exception as e:  # noqa: BLE001
        kayit["sure_sn"] = round(time.time() - t0, 2)
        kayit["hata"] = _hata(e)
        return kayit


def _goruntu_araci(kod, png):
    """Üretimdeki image_analyze yolunu bir kez ölçer."""
    from tools.image_analyzer import image_analyze

    yol = os.path.join(tempfile.gettempdir(), "basak-olcum-%s.png" % kod)
    with open(yol, "wb") as f:
        f.write(png)
    t0 = time.time()
    try:
        sonuc = image_analyze(
            yol,
            soru="Görüntüdeki büyük harf ve rakamlardan oluşan metni "
                 "aynen yaz. Yalnız metni yaz.",
        )
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "sure_sn": round(time.time() - t0, 2),
                "hata": _hata(e)}
    finally:
        try:
            os.remove(yol)
        except OSError:
            logger.debug("geçici görüntü silinemedi: %s", yol, exc_info=True)
    metin = str((sonuc or {}).get("result") or "")
    return {
        "ok": bool(metin) and kod in metin.upper(),
        "sure_sn": round(time.time() - t0, 2),
        "model": (sonuc or {}).get("model"),
        "yedek": (sonuc or {}).get("yedek"),
        "cevap": _temiz(metin, 120),
        "hata": ({"mesaj": _temiz((sonuc or {}).get("error"), 240)}
                 if (sonuc or {}).get("error") else None),
    }


def _saglayici_olc(ad, istemci, kod, url, *, arac=True, goruntu=True,
                   kota=True, ara=1.2):
    from brain import registry

    model = getattr(istemci, "model", None) or "bilinmiyor"
    tool_choice = registry.ajan_tool_choice(ad)
    kayit = {
        "saglayici": ad,
        "model": model,
        "tool_choice": tool_choice,
    }
    if not arac:
        kayit["arac"] = {"ok": False, "neden": "atlandı"}
        kayit["devam"] = {"ok": False, "neden": "atlandı"}
    else:
        ilk_mesajlar = [
            {"role": "user", "content": "ping aracını deger=42 ile çağır."}]
        olcum, yanit = _arac_turu(istemci, tool_choice)
        kayit["arac"] = olcum
        time.sleep(ara)
        kayit["devam"] = (
            _devam_turu(istemci, ilk_mesajlar, yanit, tool_choice)
            if yanit is not None else {"ok": False, "neden": "ilk tur yok"})
    if goruntu:
        time.sleep(ara)
        kayit["goruntu"] = _goruntu_turu(istemci, kod, url)
    else:
        kayit["goruntu"] = {"ok": False, "neden": "atlandı"}
    # Kota yoklaması EN SONDA: dakika/saniye sınırı olan sağlayıcıda
    # beceri turunu 429'a düşürmesin.
    if kota:
        time.sleep(ara)
        kayit["kota"] = _kota_gozlemi(istemci)
    else:
        kayit["kota"] = {"ok": False, "neden": "atlandı"}
    kayit["olculdu"] = _simdi()
    return kayit


def _ozet(satirlar, goruntu_araci):
    def say(alan):
        return sum(1 for s in satirlar if (s.get(alan) or {}).get("ok"))

    return {
        "saglayici": len(satirlar),
        "arac_tur1": "%d/%d" % (say("arac"), len(satirlar)),
        "arac_devam": "%d/%d" % (say("devam"), len(satirlar)),
        "goruntu": "%d/%d" % (say("goruntu"), len(satirlar)),
        "goruntu_araci": "gecti" if goruntu_araci.get("ok") else "kaldi",
    }


def _kota_metni(kota):
    if not isinstance(kota, dict):
        return "—"
    if kota.get("hata"):
        return "hata %s" % (kota["hata"].get("durum") or "?")
    basliklar = kota.get("basliklar") or {}
    istek = (basliklar.get("x-ratelimit-remaining-requests")
             or basliklar.get("ratelimit-remaining"))
    token = basliklar.get("x-ratelimit-remaining-tokens")
    parca = []
    if istek is not None:
        parca.append("istek %s" % istek)
    if token is not None:
        parca.append("token %s" % token)
    return " / ".join(parca) or "başlık yok"


def _markdown(meta, satirlar, goruntu_araci):
    cizgi = [
        "---",
        "uretildi: %s" % meta["uretildi"],
        "commit: %s" % meta["commit"],
        "komut: %s" % meta["komut"],
        "ttl_saat: %d" % meta["ttl_saat"],
        "sonuc: %s" % json.dumps(meta["sonuc"], ensure_ascii=False),
        "---",
        "",
        "# Model yetenek ölçümü",
        "",
        "Bu dosya `scripts/olcum/model_yetenek_olcumu.py` tarafından "
        "üretilir; elle düzenlenmez. %d saat sonra bayat sayılır."
        % TTL_SAAT,
        "",
        "## Sonuç",
        "",
        "| Sağlayıcı | Model | Araç (tur 1) | Devam turu | Görüntü | "
        "Tur token (giriş/çıkış) | Kalan kota | Not |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in satirlar:
        arac = s.get("arac") or {}
        devam = s.get("devam") or {}
        goruntu = s.get("goruntu") or {}
        token = (arac.get("token") or {})
        token_metni = (
            "%s/%s" % (token.get("giris"), token.get("cikis"))
            if token else "—")
        notlar = []
        for etiket, kayit in (("araç", arac), ("devam", devam),
                              ("görüntü", goruntu), ("kota", s.get("kota"))):
            if not isinstance(kayit, dict):
                continue
            if kayit.get("hata"):
                h = kayit["hata"]
                notlar.append("%s: %s %s" % (
                    etiket, h.get("durum") or h.get("tur") or "",
                    h.get("mesaj") or ""))
            elif kayit.get("neden"):
                notlar.append("%s: %s" % (etiket, kayit["neden"]))
        cizgi.append("| %s | `%s` | %s | %s | %s | %s | %s | %s |" % (
            s["saglayici"], s["model"],
            "geçti" if arac.get("ok") else "kaldı",
            "geçti" if devam.get("ok") else "kaldı",
            "geçti" if goruntu.get("ok") else "kaldı",
            token_metni,
            _kota_metni(s.get("kota")),
            _temiz("; ".join(notlar), 220) or "—",
        ))
    cizgi += [
        "",
        "## Görüntü aracı (üretim yolu)",
        "",
        "`tools.image_analyzer.image_analyze` → **%s** (%s sn, model: %s%s)"
        % ("geçti" if goruntu_araci.get("ok") else "kaldı",
           goruntu_araci.get("sure_sn"),
           goruntu_araci.get("model") or "—",
           ", yedek: %s" % goruntu_araci.get("yedek")
           if goruntu_araci.get("yedek") else ""),
        "",
        "## Yöntem ve sınırlar",
        "",
        "- Araç turu, üretimdeki `tool_choice` değeriyle gerçek adaptör "
        "üzerinden koştu; metin içindeki JSON tool_call sayılmadı.",
        "- Görüntü testi rastgele 5 karakterlik bir kod taşıyan PNG "
        "kullandı; yalnız kodu birebir okuyan yanıt geçti.",
        "- Görüntü testi sağlayıcının **varsayılan sohbet modeliyle** "
        "yapıldı. Sağlayıcının ayrı bir görüntü modeli olabilir; o yol "
        "`image_analyze` satırında ölçülür.",
        "- Kota: tur başına gerçek token ve sağlayıcının döndürdüğü "
        "rate-limit başlıkları kaydedildi. Günlük/aylık tavan bu ölçümde "
        "taranmadı; ölçülmeyen tavan bilinmeyen sayılır. \"Limitsiz\" "
        "denmez.",
        "- Tek koşu, tek örnek. Tekrarlı ölçüm için script yeniden koşulur; "
        "sonuç `ttl_saat` sonrası bayat kabul edilir.",
    ]
    if meta.get("birlestirildi"):
        cizgi.append(
            "- Bu rapor `--birlestir` ile tamamlandı; her sağlayıcının "
            "ölçüm zamanı ham JSON'daki `olculdu` alanındadır.")
    cizgi += [
        "",
        "## Ham kayıt",
        "",
        "`data/model-yetenek-olcumu.json`",
        "",
    ]
    return "\n".join(cizgi)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sadece", default="",
                    help="virgüllü sağlayıcı listesi (varsayılan: hepsi)")
    ap.add_argument("--kuru", action="store_true",
                    help="yalnız hazır sağlayıcıları listeler, çağrı yapmaz")
    ap.add_argument("--saniye", type=float, default=45.0,
                    help="çağrı başına üst sınır")
    ap.add_argument("--aracsiz", action="store_true", help="araç turunu atla")
    ap.add_argument("--goruntsuz", action="store_true",
                    help="görüntü turunu atla")
    ap.add_argument("--kotasiz", action="store_true",
                    help="rate-limit başlığı gözlemini atla")
    ap.add_argument("--ara", type=float, default=1.2,
                    help="çağrılar arası bekleme (saniye)")
    ap.add_argument("--birlestir", action="store_true",
                    help="önceki ham kaydı koru, seçilen sağlayıcıları tazele")
    ap.add_argument("--cikti", default=str(HAM), help="ham JSON yolu")
    ap.add_argument("--rapor", default=str(RAPOR), help="rapor yolu")
    ap.add_argument("--yeniden-yaz", action="store_true",
                    help="çağrı yapmadan mevcut ham kayıttan raporu üret")
    args = ap.parse_args()

    if args.yeniden_yaz:
        ham_yolu = Path(args.cikti)
        try:
            veri = json.loads(ham_yolu.read_text(encoding="utf-8"))
            meta = dict(veri.get("meta") or {})
            meta["yeniden_yazildi"] = _simdi()
            rapor_yolu = Path(args.rapor)
            rapor_yolu.parent.mkdir(parents=True, exist_ok=True)
            rapor_yolu.write_text(
                _markdown(meta, veri.get("saglayicilar") or [],
                          veri.get("goruntu_araci") or {}),
                encoding="utf-8")
            print("Rapor: %s" % rapor_yolu)
            return 0
        except (OSError, ValueError, TypeError) as e:
            print("Ham kayıt okunamadı: %s" % _temiz(e))
            return 2

    from brain import Brain

    beyin = Brain()
    hazir = sorted(a for a in beyin._providers
                   if a != "genel" and beyin._providers[a] is not None)
    istenen = [a.strip() for a in args.sadece.split(",") if a.strip()]
    hedefler = [a for a in hazir if not istenen or a in istenen]
    if not hedefler:
        print("Hazır sağlayıcı yok (istenen: %s)" % (istenen or "hepsi"))
        return 2
    if args.kuru:
        for ad in hedefler:
            print("%s -> %s" % (ad, getattr(beyin._providers[ad],
                                            "model", "?")))
        return 0

    kod, png = _token_resmi()
    url = _veri_urlu(png)
    satirlar = []
    for ad in hedefler:
        istemci = beyin._providers[ad]
        _zaman_asimi(istemci, args.saniye)
        print("[%s] %s ölçülüyor..." % (ad, getattr(istemci, "model", "?")))
        satirlar.append(_saglayici_olc(
            ad, istemci, kod, url,
            arac=not args.aracsiz, goruntu=not args.goruntsuz,
            kota=not args.kotasiz, ara=args.ara))

    goruntu_araci = ({"ok": False, "neden": "atlandı"}
                     if args.goruntsuz else _goruntu_araci(kod, png))
    if args.birlestir and HAM.exists():
        try:
            eski = json.loads(HAM.read_text(encoding="utf-8"))
            birlesik = {
                s["saglayici"]: s for s in eski.get("saglayicilar", [])
                if isinstance(s, dict) and s.get("saglayici")
            }
            for s in satirlar:
                birlesik[s["saglayici"]] = s
            satirlar = [birlesik[ad] for ad in sorted(birlesik)]
            if args.goruntsuz:
                goruntu_araci = (eski.get("goruntu_araci")
                                 or goruntu_araci)
        except (OSError, ValueError, TypeError, KeyError):
            print("UYARI: önceki ham kayıt okunamadı, birleştirme atlandı")
    meta = {
        "uretildi": _simdi(),
        "commit": _commit(),
        "komut": ("python scripts/olcum/model_yetenek_olcumu.py "
                  + " ".join(sys.argv[1:])).strip(),
        "ttl_saat": TTL_SAAT,
        "birlestirildi": bool(args.birlestir),
    }
    meta["sonuc"] = _ozet(satirlar, goruntu_araci)
    print(json.dumps(meta["sonuc"], ensure_ascii=False, indent=2))

    ham_yolu = Path(args.cikti)
    rapor_yolu = Path(args.rapor)
    ham_yolu.parent.mkdir(parents=True, exist_ok=True)
    with open(ham_yolu, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "saglayicilar": satirlar,
                   "goruntu_araci": goruntu_araci},
                  f, ensure_ascii=False, indent=2)
    rapor_yolu.parent.mkdir(parents=True, exist_ok=True)
    rapor_yolu.write_text(_markdown(meta, satirlar, goruntu_araci),
                          encoding="utf-8")
    print("Rapor: %s" % rapor_yolu)
    print("Ham:   %s" % ham_yolu)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
