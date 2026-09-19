"""GitHub Issue #4 icin gercek Basak ajan sohbet kapisi.

Bu dosya uygulama davranisini degistirmez. GitHub Actions tarafindan
BASAK_CHAT_MESSAGE ile cagrilir; gercek Brain + mesaj_isle + TOOLS hattini
calistirir ve sonucu markdown dosyasina yazar.
"""

import json
import os
import tempfile

SONUC_DOSYASI = "github-agent-result.md"


def _yaz(metin):
    with open(SONUC_DOSYASI, "w", encoding="utf-8") as f:
        f.write(metin)


def main():
    mesaj = (os.environ.get("BASAK_CHAT_MESSAGE") or "").strip()
    if not mesaj:
        _yaz("### Başak canlı test\n\nMesaj boş geldi.")
        return

    from brain import Brain
    from chat.flow import mesaj_isle
    from chat import context as ctx
    from tools import TOOLS
    import tools as tools_mod

    b = Brain()
    ajanlar = [ad for ad, _ in b._bulut_zinciri(
        tools=True, tool_required=True)]

    if not ajanlar:
        _yaz(
            "### Başak canlı test\n\n"
            "❌ Gerçek ajan beyni hazır değil. Sekiz ücretsiz sağlayıcıdan "
            "hiçbiri bu GitHub koşusunda ajan olarak hazır değil.\n"
        )
        return

    kosulan = []
    gercek_calistir = tools_mod.calistir

    def kayitli_calistir(ad, args):
        kosulan.append(ad)
        return gercek_calistir(ad, args)

    tools_mod.calistir = kayitli_calistir

    olaylar = []

    def cb(code):
        olaylar.append(code)

    with tempfile.TemporaryDirectory() as td:
        ctx.HISTORY_FILE = os.path.join(td, "gecmis.json")
        ctx.SETTINGS_FILE = os.path.join(td, "ayar.json")
        ctx._hafiza = False

        mesaj_isle(
            mesaj,
            b,
            "Sen Başak'sın, Casper'ın kişisel asistanısın. Türkçe konuş.",
            cb,
            TOOLS,
        )

    cevap = ""
    kaynak = ""
    hata = ""

    for code in olaylar:
        if code.startswith("BasakUI.bitir("):
            ic = code[code.index("(") + 1: code.rindex(")")]
            try:
                degerler = json.loads("[" + ic + "]")
                cevap = str(degerler[0] or "")
                kaynak = str(degerler[1] or "") if len(degerler) > 1 else ""
            except Exception:
                cevap = code
        elif code.startswith("BasakUI.error("):
            ic = code[code.index("(") + 1: code.rindex(")")]
            try:
                degerler = json.loads("[" + ic + "]")
                hata = str(degerler[0] or "")
            except Exception:
                hata = code

    araclar = ", ".join(kosulan) if kosulan else "yok"
    ajan_havuzu = ", ".join(ajanlar)

    if cevap:
        sonuc = (
            "### Başak canlı test\n\n"
            f"**Mesaj:** {mesaj}\n\n"
            f"**Başak:** {cevap}\n\n"
            f"**Sağlayıcı:** {kaynak or 'doğrulanamadı'}\n\n"
            f"**Çalışan gerçek araçlar:** {araclar}\n\n"
            f"**Hazır ajan havuzu:** {ajan_havuzu}\n"
        )
    else:
        sonuc = (
            "### Başak canlı test\n\n"
            f"**Mesaj:** {mesaj}\n\n"
            f"❌ **Hata:** {hata or 'Final cevap oluşmadı'}\n\n"
            f"**Çalışan gerçek araçlar:** {araclar}\n\n"
            f"**Hazır ajan havuzu:** {ajan_havuzu}\n"
        )

    _yaz(sonuc)


if __name__ == "__main__":
    main()
