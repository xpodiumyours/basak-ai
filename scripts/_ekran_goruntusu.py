"""Gecici goruntu dogrulama betigi — web/ arayuzunu gercek tarayicida acar.

Kullanim: .venv/bin/python scripts/_ekran_goruntusu.py
Cikti: artifacts/web-*.png (AGENTS.md §5 gercek calistirma kaniti)
"""
import sys

from playwright.sync_api import sync_playwright

TEMEL = "http://127.0.0.1:3006/"


def main() -> int:
    with sync_playwright() as p:
        # channel="chromium": yeni headless mod (tam Chromium); yalın
        # headless-shell bu ortamda textarea + grid düzeninde çöküyor.
        tarayici = p.chromium.launch(channel="chromium", args=["--disable-gpu"])

        # ── Mobil (telefon boyutu, kullanıcının gördüğü ekran) ──
        sayfa = tarayici.new_page(viewport={"width": 393, "height": 852},
                                  device_scale_factor=2)
        sayfa.goto(TEMEL, wait_until="networkidle")
        sayfa.screenshot(path="artifacts/web-mobil-karsilama.png")

        # Ayarlar paneli (çekmece) açık
        sayfa.click("#panelButton")
        sayfa.wait_for_timeout(600)
        sayfa.screenshot(path="artifacts/web-mobil-panel.png")
        sayfa.keyboard.press("Escape")
        sayfa.wait_for_timeout(300)

        # Sohbet balonları + cevap eylemleri (aynı DOM yapısı, gerçek CSS)
        sayfa.evaluate(
            """() => {
              const chat = document.getElementById('chat');
              document.getElementById('hero').hidden = true;
              const user = document.createElement('div');
              user.className = 'message-row user';
              user.innerHTML = '<div class="bubble"><div class="icerik">Bu hafta fatura özetimi çıkarır mısın?</div></div>';
              const asst = document.createElement('div');
              asst.className = 'message-row assistant';
              asst.innerHTML = '<div class="bubble">'
                + '<div class="assistant-head"><span class="assistant-mark">B</span><span>Başak</span></div>'
                + '<div class="icerik"><p>Elbette. Ekim ayına ait üç fatura tespit ettim; toplam tutar 2.480 TL. Detayları ister misin?</p></div>'
                + '<div class="cevap-eylem"><button class="eylem-dugme">Kopyala</button>'
                + '<button class="eylem-dugme">Markdown</button>'
                + '<button class="eylem-dugme">Sesli oku</button></div>'
                + '</div>';
              chat.appendChild(user);
              chat.appendChild(asst);
            }"""
        )
        sayfa.wait_for_timeout(200)
        sayfa.screenshot(path="artifacts/web-mobil-sohbet.png")

        # ── Masaüstü ──
        masa = tarayici.new_page(viewport={"width": 1280, "height": 820})
        masa.goto(TEMEL, wait_until="networkidle")
        masa.click("#panelButton")
        masa.wait_for_timeout(600)
        masa.screenshot(path="artifacts/web-masaustu-panel.png")
        masa.keyboard.press("Escape")
        masa.wait_for_timeout(300)
        masa.screenshot(path="artifacts/web-masaustu.png")

        tarayici.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
