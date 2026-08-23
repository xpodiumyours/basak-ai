# _probe_temizle.py — gecmis.json'dan probe kirliligini temizler (yedekli)
import json
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SORU = "VixRex'te durum ne?"
p = "gecmis.json"
shutil.copy(p, p + ".yedek-probe")

with open(p, encoding="utf-8-sig") as f:
    k = json.load(f)

temiz = []
atlanir = False
silinen = 0
for m in k:
    if atlanir:
        atlanir = False
        silinen += 1
        continue
    if m.get("role") == "user" and m.get("content") == SORU:
        silinen += 1
        atlanir = True  # ardindaki asistan cevabini da atla
        continue
    temiz.append(m)

with open(p, "w", encoding="utf-8") as f:
    json.dump(temiz, f, ensure_ascii=False, indent=2)

print("Once: %d kayit -> Sonra: %d (silinen kayit: %d)" % (len(k), len(temiz), silinen))
