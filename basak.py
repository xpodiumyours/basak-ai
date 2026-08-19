import json
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

import requests

OLLAMA_URL = "http://127.0.0.1:11434"
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gecmis.json")

KISILIK = (
    "Senin adın Başak. Sen 'Qwen' değilsin, 'Alibaba' değilsin, hiçbir şirketin ürünü değilsin. "
    "Adın sorulduğunda 'Başak' diye cevap ver. "
    "Kullanıcının kişisel yapay zekâ asistanısın. "
    "Türkçe konuş, kısa ve net cevaplar ver. "
    "Kullanıcının adını öğren ve sonraki konuşmalarda hatırla. "
    "Bilmediğini uydurma, dürüst ol."
)

RENK = {
    "basak": "\033[96m",
    "sen": "\033[92m",
    "bilgi": "\033[90m",
    "hata": "\033[91m",
    "temiz": "\033[0m",
}


def yaz(metin, renk="temiz"):
    print(f"{RENK[renk]}{metin}{RENK['temiz']}", end="", flush=True)


def kirmizi(metin):
    yaz(metin, "hata")


def modelleri_al():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return [m["name"] for m in r.json().get("models", [])]
    except requests.ConnectionError:
        return []


def model_sec(modeller):
    if "qwen2.5:3b" in modeller:
        return "qwen2.5:3b"
    return modeller[0] if modeller else None


def kaydet(mesajlar):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(mesajlar[-20:], f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def gecmisi_yukle():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def sohbet_et(model, mesajlar, yeni_mesaj):
    mesajlar.append({"role": "user", "content": yeni_mesaj})
    kaydet(mesajlar)
    payload = {
        "model": model,
        "messages": mesajlar,
        "stream": True,
    }
    try:
        with requests.post(f"{OLLAMA_URL}/api/chat", json=payload, stream=True, timeout=300) as r:
            for satir in r.iter_lines(decode_unicode=True):
                if not satir:
                    continue
                parca = json.loads(satir)
                if parca.get("done"):
                    yaz("\n\n")
                    return
                if "message" in parca and "content" in parca["message"]:
                    yaz(parca["message"]["content"], "basak")
    except requests.RequestException as e:
        kirmizi(f"\nHata: {e}\n")


def giris():
    print()
    yaz("╔══════════════════════════════════════════╗\n", "basak")
    yaz("║          ██████╗  █████╗ ███████╗ █████╗ ██╗  ██╗  ║\n", "basak")
    yaz("║          ██╔══██╗██╔══██╗██╔════╝██╔══██╗██║ ██╔╝  ║\n", "basak")
    yaz("║          ██████╔╝███████║███████╗███████║█████╔╝   ║\n", "basak")
    yaz("║          ██╔══██╗██╔══██║╚════██║██╔══██║██╔═██╗   ║\n", "basak")
    yaz("║          ██████╔╝██║  ██║███████║██║  ██║██║  ██╗  ║\n", "basak")
    yaz("║          ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝  ║\n", "basak")
    yaz("╚══════════════════════════════════════════╝\n", "basak")
    print()


def ana_dongu(model):
    mesajlar = [{"role": "system", "content": KISILIK}]
    mesajlar += gecmisi_yukle()
    if mesajlar:
        yaz("(Önceki konuşmamızı hatırlıyorum)\n", "bilgi")
    baslangic = f"\n\033[96mBaşak\033[0m: Hoş geldin! İstediğini yaz. (/temizle /çık)\n"
    print(baslangic)
    while True:
        try:
            girisim = input("\033[92mSen\033[0m: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not girisim:
            continue
        if girisim == "/çık" or girisim == "/exit":
            kaydet(mesajlar)
            yaz("Görüşürüz!\n")
            break
        if girisim == "/temizle":
            mesajlar = []
            kaydet(mesajlar)
            yaz("(Hafıza temizlendi)\n", "bilgi")
            continue
        yaz("Başak: ")
        sohbet_et(model, mesajlar, girisim)


def main():
    if os.name == "nt":
        os.system("cls")
    modeller = modelleri_al()
    if not modeller:
        kirmizi("Ollama çalışmıyor. Önce 'Başak'ı Başlat.cmd' çalıştır.\n")
        input("Kapatmak için Enter...")
        return 1
    model = model_sec(modeller)
    if model is None:
        kirmizi("Hiçbir model yüklü değil.\n")
        input("Kapatmak için Enter...")
        return 1
    giris()
    yaz(f"Beyin: {model}\n", "bilgi")
    ana_dongu(model)
    return 0


if __name__ == "__main__":
    sys.exit(main())