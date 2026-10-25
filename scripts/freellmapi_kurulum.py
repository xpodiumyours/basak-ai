"""Mevcut Basak biletlerini FreeLLMAPI'ye tek JSON ile aktarir.

Calistirma: python -m scripts.freellmapi_kurulum --kontrol
Gercek cikti: python -m scripts.freellmapi_kurulum
Anahtarlar stdout'a yazilmaz; cikti varsayilan olarak gitignore kapsaminda.
Resmi sozlesme: docs/en/install/01-install.md, Declarative startup config.
"""

import argparse
import json
import os
from pathlib import Path


BILETLER = (
    ("groq", "GROQ_API_KEY", "groq_key"),
    ("google", "GEMINI_API_KEY", "gemini_key"),
    ("zhipu", "ZAI_API_KEY", "zai_key"),
    ("cohere", "COHERE_API_KEY", "cohere_key"),
    ("nvidia", "NVIDIA_API_KEY", "nvidia_key"),
    ("kilo", "KILO_API_KEY", "kilo_key"),
    ("openrouter", "OPENROUTER_API_KEY", "openrouter_key"),
    ("mistral", "MISTRAL_API_KEY", "mistral_key"),
)


def yapilandirma(ayar=None, ortam=None):
    """Bilinen biletleri resmi platform kimliklerine cevirir; ag cagrisi yok."""
    ayar = ayar or {}
    ortam = os.environ if ortam is None else ortam
    biletler = []
    for platform, env, alan in BILETLER:
        key = (ortam.get(env) or ayar.get(alan) or "").strip()
        if key:
            biletler.append({"platform": platform, "key": key, "label": "basak"})
    account = (ortam.get("CLOUDFLARE_ACCOUNT_ID") or ayar.get("cloudflare_account_id") or "").strip()
    token = (ortam.get("CLOUDFLARE_API_TOKEN") or ayar.get("cloudflare_api_token") or "").strip()
    if bool(account) != bool(token):
        raise ValueError("Cloudflare hesap kimligi ve token birlikte gerekli")
    if account and token:
        biletler.append({"platform": "cloudflare", "key": account + ":" + token,
                         "label": "basak"})
    if not biletler:
        raise ValueError("Aktarilacak mevcut saglayici anahtari bulunamadi; bos kurulum uretilmedi")
    veri = {"keys": biletler, "routing": {"strategy": "priority"}}
    email = (ortam.get("FREELLMAPI_ADMIN_EMAIL") or "").strip()
    password = ortam.get("FREELLMAPI_ADMIN_PASSWORD") or ""
    if email or password:
        if "@" not in email or len(password) < 12:
            raise ValueError("Panel e-postasi ve en az 12 karakterli parola birlikte gerekli")
        veri["admin"] = {"email": email, "password": password}
    return veri


def guvenli_yaz(yol, veri):
    """Var olani ezmeden, yalniz sahibinin okuyabildigi dosya olusturur."""
    yol = Path(yol)
    if not yol.name.startswith(".env."):
        raise ValueError("Sirli cikti .env. ile baslamali; gitignore disina yazilmaz")
    fd = os.open(yol, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(veri, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kontrol", action="store_true", help="Yalniz bilet sayisini bildirir")
    parser.add_argument("--ayarlar", type=Path, default=Path(__file__).resolve().parents[1] / "ayarlar.json")
    parser.add_argument("--cikti", type=Path, default=Path(".env.freellmapi-config.json"))
    args = parser.parse_args()
    try:
        ayar = json.loads(args.ayarlar.read_text(encoding="utf-8-sig")) if args.ayarlar.exists() else {}
        if not isinstance(ayar, dict):
            raise ValueError("Ayar dosyasi JSON nesnesi olmali")
        veri = yapilandirma(ayar)
        if not args.kontrol:
            if "admin" not in veri:
                raise ValueError("Ilk kurulum icin FREELLMAPI_ADMIN_EMAIL ve FREELLMAPI_ADMIN_PASSWORD gerekli")
            guvenli_yaz(args.cikti, veri)
        print("%d saglayici hazir: %s" % (len(veri["keys"]), ", ".join(k["platform"] for k in veri["keys"])))
        if not args.kontrol:
            print("Sirli yapilandirma dosyasi olusturuldu. FREEAPI_CONFIG_PATH ile gateway'e baglayin.")
    except (OSError, ValueError):
        # JSON ayrisma hatasinin metni sirli satiri icerebilir.
        print("Kurulum tamamlanamadi: mevcut biletleri, panel bilgilerini ve cikti dosyasini kontrol edin.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
