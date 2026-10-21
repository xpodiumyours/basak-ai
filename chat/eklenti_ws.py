"""chat/eklenti_ws.py — tarayıcı eklentisinin BULUT kanalı (WebSocket).

Neden bu dosya: eklenti artık yerel Python köprüsüne değil, doğrudan
canlı Başak'a bağlanır. Sohbet ve sayfa istekleri AYNI bağlantıdan
yürür; böylece model döngüsü, eklentinin bağlı olduğu instance üzerinde
kalır. Vercel'de bağlantı tek instance'a çivilendiği için instance'lar
arası yönlendirme sorunu doğmaz.

Tek beyin kuralı (AGENTS.md §9): burada model seçimi, sağlayıcı zinciri
veya ikinci bir araç çalıştırıcı YOKTUR. Gelen metin `chat.flow.mesaj_isle`
ile çekirdeğe verilir; kanal yalnız taşıyıcıdır.

Sınırlar
--------
- Fonksiyon azami süresi (Vercel Hobby: 300 sn) dolunca bağlantı kapanır;
  eklenti yeniden bağlanır. Uzun tek tur 300 sn'de kesilir.
- Kalıcı disk yok: geçmiş istek gövdesiyle gelir (web ekranındaki gibi).
- Bağlantı kopunca bekleyen araç istekleri açık hatayla döner.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from tools import tarayici_kanal

logger = logging.getLogger(__name__)

router = APIRouter()


class _CevapToplayici:
    """`mesaj_isle` olaylarını tek cevaba indirger (panel için).

    Web ekranı olay kuyruğu kullanır; eklenti tek cevap alır. Fark yalnız
    taşıyıcıdadır — çekirdek yolu aynı (`chat.flow.mesaj_isle`).
    """

    def __init__(self):
        self.cevap = ""
        self.kaynak = ""
        self.hata = ""
        self.bitti = False

    def olay(self, tur, **veri):
        logger.debug("eklenti kanali olayi: %s %s", tur, sorted(veri))

    def __call__(self, kod):
        try:
            if not str(kod).startswith("BasakUI."):
                return
            ad, icerik = kod[8:].split("(", 1)
            parca = json.loads("[%s]" % icerik.rsplit(")", 1)[0])
            if ad == "bitir":
                self.bitti = True
                self.cevap = str(parca[0] or "")
                self.kaynak = str(parca[1] or "") if len(parca) > 1 else ""
            elif ad == "error":
                self.hata = str(parca[0] or "")
        except Exception:
            logger.debug("kanal UI kodu cozulemedi: %r", str(kod)[:120],
                         exc_info=True)


def _kimlik_coz(websocket):
    """Bağlantı çerezinden kişi kimliği; yoksa None (misafir)."""
    import kullanici as kullanici_modulu

    try:
        token = websocket.cookies.get(kullanici_modulu.cookie_adi()) or ""
        return kullanici_modulu.oturum_coz(token) if token else None
    except (RuntimeError, ValueError, KeyError):
        logger.debug("kanal kimligi cozulemedi", exc_info=True)
        return None


def _gecmis_coz(ham):
    """Panelden gelen konuşma geçmişini API biçimine indirger.

    Yalnız yapı denetlenir (rol + metin); metin kırpılmaz, yeniden
    yazılmaz. Geçersiz giriş `None` döner: o zaman sunucudaki geçmiş
    kullanılır.
    """
    if not isinstance(ham, list):
        return None
    temiz = []
    for mesaj in ham:
        if not isinstance(mesaj, dict):
            continue
        rol = str(mesaj.get("role") or "").strip()
        if rol not in ("user", "assistant"):
            continue
        icerik = mesaj.get("content")
        if not isinstance(icerik, str) or not icerik.strip():
            continue
        temiz.append({"role": rol, "content": icerik})
    return temiz or None


def _cevapla(metin, kid, kanal, gecmis=None):
    """Çekirdeği çalıştırır (iş parçacığında); panel cevabını döndürür."""
    from chat.flow import mesaj_isle
    from chat.kimlik import kullanici_kur
    from chat.prompts import kisilik_blogu

    import app as uygulama

    beyin, toollar = uygulama._cekirdek()
    kullanici_kur(kid or "misafir")
    tarayici_kanal.kanal_kur(kanal)
    ayikla = _CevapToplayici()
    try:
        mesaj_isle(metin, beyin, kisilik_blogu(kid, misafir=not kid),
                   ayikla, toollar, misafir=not kid,
                   gecmis_override=_gecmis_coz(gecmis))
    finally:
        tarayici_kanal.kanal_temizle()
    if ayikla.hata and not ayikla.cevap:
        return {"hata": ayikla.hata}
    return {"cevap": ayikla.cevap, "kaynak": ayikla.kaynak}


@router.websocket("/api/eklenti")
async def eklenti_kanali(websocket: WebSocket):
    """Eklenti bağlantısı: sohbet + sayfa istekleri aynı kanaldan."""
    await websocket.accept()
    loop = asyncio.get_running_loop()
    kid = _kimlik_coz(websocket)
    kullanici = kid or "misafir"
    kanal = tarayici_kanal.Kanal(
        loop,
        lambda cid, islem, veri: websocket.send_json(
            {"id": cid, "islem": islem, "veri": veri}),
        "ws-%s-%d" % (kullanici, id(websocket)),
        kullanici=kullanici,
    )
    logger.info("eklenti kanali acildi: %s", kanal.kimlik)

    async def _sohbet(mesaj):
        kimlik = mesaj.get("id")
        veri = mesaj.get("veri") or {}
        metin = str((veri.get("metin")) or "").strip()
        if not metin:
            await websocket.send_json(
                {"id": kimlik, "ok": False, "hata": "mesaj boş"})
            return
        try:
            sonuc = await asyncio.to_thread(
                _cevapla, metin, kid, kanal, veri.get("gecmis"))
        except Exception as hata:            # noqa: BLE001 - kanal kesilmesin
            logger.warning("kanal sohbet hatasi: %s", hata)
            sonuc = {"hata": "Başak çalıştırılamadı: %s" % str(hata)[:200]}
        if "hata" in sonuc:
            await websocket.send_json(
                {"id": kimlik, "ok": False, "hata": sonuc["hata"]})
        else:
            await websocket.send_json(
                {"id": kimlik, "ok": True, "sonuc": sonuc})

    try:
        while True:
            mesaj = await websocket.receive_json()
            if not isinstance(mesaj, dict):
                continue
            if mesaj.get("islem") == "sohbet":
                asyncio.create_task(_sohbet(mesaj))
            elif mesaj.get("islem"):
                await websocket.send_json({
                    "id": mesaj.get("id"), "ok": False,
                    "hata": "bilinmeyen işlem: %s" % mesaj.get("islem")})
            else:
                kanal.cevap_yaz(mesaj)
    except WebSocketDisconnect:
        logger.debug("eklenti kanali istemci tarafinda kapandi: %s",
                     kanal.kimlik)
    except Exception as hata:                # noqa: BLE001 - kanal sonu
        logger.info("eklenti kanali bitti (%s): %s", kanal.kimlik, hata)
    finally:
        kanal.kapat()
        logger.info("eklenti kanali kapandi: %s", kanal.kimlik)
