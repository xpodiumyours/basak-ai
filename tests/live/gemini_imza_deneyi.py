"""tests/live/gemini_imza_deneyi.py — KOK NEDEN SONDAJI (elle kosulur).

Amac: "ajan dongusunun devami baska saglayiciya giderse ne olur?"
sorusunu 3 canli Gemini cagrisiyla olcmek. Kota harcar; bu yuzden
pytest paketine DAHIL DEGILDIR (tests/live/ altindaki --live kapisi
yalniz test_*.py dosyalarini kosar).

Kosum:
    python tests/live/gemini_imza_deneyi.py

Olculen (2026-09-20, gemini-3-flash-preview):
    TUR-1  -> tool_call imzali gelir (extra_content.google.thought_signature)
    A) imza AYNEN geri verilir      -> BASARILI (tur-2 tamam)
    B) imza DUSURULUR (baska
       saglayicidan gelmis gibi)    -> 400 "Function call is missing a
                                       thought_signature in functionCall
                                       parts"
Yargi: saglayici degistiren devam turu native protokolu kirar. Duzeltme
chat/tools.py'dedir (devam turu basladigi saglayiciya baglanir); kilit
testi: tests/test_p2_canli_oncesi.py::test_provider_ozel_gemini_imzasi_failoverda_temizlenir
"""

import json
import os
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from brain.gemini import GeminiClient          # noqa: E402

SEMA = [{"type": "function", "function": {
    "name": "simdi", "description": "Su anki tarih ve saati doner.",
    "parameters": {"type": "object", "properties": {}}}}]
SORU = ("Su anki tarih ve saati ogrenmek zorundasin. simdi aracini kullan, "
        "sonucu degerlendir ve tek cumle soyle.")
ARAC_SONUCU = json.dumps({"result": "20 Eylul 2026 Pazar, 12:30"},
                         ensure_ascii=False)


def _istemci():
    with open(KOK / "ayarlar.json", encoding="utf-8-sig") as f:
        ayar = json.load(f)
    return GeminiClient(ayar["gemini_key"])


def main():
    istemci = _istemci()
    print("model:", istemci.model, flush=True)

    y1 = istemci.cevapla([{"role": "user", "content": SORU}],
                         tools=SEMA, tool_choice="auto")
    tc = (y1.get("tool_calls") or [{}])[0]
    imza = bool((tc.get("extra_content") or {}).get("google"))
    print("TUR-1: tool_call=%s | imza tasiniyor mu=%s"
          % ((tc.get("function") or {}).get("name"), imza), flush=True)

    def tur2(tool_calls, etiket):
        msj = [
            {"role": "user", "content": SORU},
            {"role": "assistant", "content": "", "tool_calls": tool_calls},
            {"role": "tool", "tool_call_id": tool_calls[0]["id"],
             "name": tool_calls[0]["function"]["name"],
             "content": ARAC_SONUCU},
        ]
        try:
            y = istemci.cevapla(msj, tools=SEMA, tool_choice="auto")
            print("%s: BASARILI | %s"
                  % (etiket, (y.get("content") or "").strip()[:90]),
                  flush=True)
            return "OK"
        except Exception as e:                      # noqa: BLE001
            print("%s: HATA | %s" % (etiket, str(e)[:260]), flush=True)
            return "HATA"

    print("\n--- A) kendi imzali tool_call ---", flush=True)
    a = tur2([tc], "A")

    print("\n--- B) imzasiz tool_call (capraz saglayici) ---", flush=True)
    b = tur2([{k: v for k, v in tc.items() if k != "extra_content"}], "B")

    print("\nSONUC: A=%s  B=%s" % (a, b), flush=True)
    if a == "OK" and b == "HATA":
        print("YARGI: capraz-saglayici devami 400'un kok nedeni (DOGRU)",
              flush=True)
    elif a == "OK" and b == "OK":
        print("YARGI: capraz-saglayici devami 400 uretmiyor (CURUDU)",
              flush=True)
    else:
        print("YARGI: belirsiz — A da hata verdi, baska neden aranmali",
              flush=True)


if __name__ == "__main__":
    main()
