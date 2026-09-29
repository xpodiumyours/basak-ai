"""web/araclar.js duman testi — Node ile HESAPLAR blogunu calistirir.

Kullanim:  python web/araclar_duman.py
Cikis 0 = 8 yeni arac beklenen degeri uretti.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
BLOK_RE = re.compile(r"var HESAPLAR = \{.*?\n  \};", re.DOTALL)

TESTLER = [
    ("character-remover", ["Merhaba, Dünya!", ""], "Merhaba Dünya"),
    ("character-remover", ["aabbcc", "b"], "aacc"),
    ("character-replacer", ["aab", "a>e"], "eeb"),
    ("character-replacer", ["aabb", "a>e|b>f"], "eeff"),
    ("tabs-to-space", ["a\tb", ""], "a    b"),
    ("tabs-to-space", ["a\tb", "2"], "a  b"),
    ("text-splitter", ["bir iki", "kelime"], "1. bir\n2. iki"),
    ("text-splitter", ["a\nb", ""], "1. a\n2. b"),
    ("text-splitter", ["Ali geldi. Veli gitti.", "cumle"],
     "1. Ali geldi.\n2. Veli gitti."),
    ("space-remover", ["  a   b  "], "a b"),
    ("space-remover", ["  a   b\n   c  d  "], "a b\nc d"),
    ("comma-inserter", ["a\nb\nc"], "a, b, c"),
    ("comma-inserter", ["elma armut"], "elma, armut"),
    ("json-formatter", ['{"b":2,"a":1}', ""],
     '{\n  "b": 2,\n  "a": 1\n}'),
    ("json-formatter", ["[1,2]", "4"], "[\n    1,\n    2\n]"),
    ("html-entities", ['<b>"x"</b>', ""],
     "&lt;b&gt;&quot;x&quot;&lt;/b&gt;"),
    ("html-entities", ["&lt;b&gt;", "decode"], "<b>"),
    ("html-entities", ["&#65;", "decode"], "A"),
]

HATA_TESTLER = [
    ("character-remover", ["", ""]),
    ("character-replacer", ["abc", ""]),
    ("character-replacer", ["abc", "yanlis"]),
    ("tabs-to-space", ["sekmesiz", ""]),
    ("tabs-to-space", ["a\tb", "99"]),
    ("text-splitter", ["", ""]),
    ("space-remover", ["   "]),
    ("comma-inserter", ["   "]),
    ("json-formatter", ["{bozuk", ""]),
    ("json-formatter", ["{}", "99"]),
    ("html-entities", ["", ""]),
]


def main():
    kaynak = (KOK / "araclar.js").read_text(encoding="utf-8")
    eslesme = BLOK_RE.search(kaynak)
    if not eslesme:
        print("BLOK-YOK")
        return 1
    blok = eslesme.group(0).replace("var HESAPLAR =", "", 1).strip()
    assert blok.endswith("};")
    program = (
        "const fs=require('fs');\n"
        "const HESAPLAR=%s\n"
        "const cases=JSON.parse(fs.readFileSync(0,'utf8'));\n"
        "(async()=>{\n"
        "  const out=[];\n"
        "  for(const [ad,girdi,hataMi] of cases){\n"
        "    const fn=HESAPLAR[ad];\n"
        "    if(!fn){out.push([ad,'FONKSIYON-YOK']);continue;}\n"
        "    try{\n"
        "      const s=String(await fn(girdi));\n"
        "      out.push([ad, hataMi ? 'HATA-BEKLENIYORDU' : s]);\n"
        "    }catch(e){ out.push([ad, hataMi ? 'HATA-OK' : ('HATA:'+(e&&e.message))]); }\n"
        "  }\n"
        "  console.log(JSON.stringify(out));\n"
        "})();\n" % blok
    )
    durumlar = [(ad, girdi, False) for ad, girdi, _b in TESTLER]
    durumlar += [(ad, girdi, True) for ad, girdi in HATA_TESTLER]
    girdi = json.dumps(durumlar, ensure_ascii=False)
    proc = subprocess.run(
        ["node", "-e", program], input=girdi.encode("utf-8"),
        capture_output=True, cwd=str(KOK), timeout=60,
    )
    if proc.returncode != 0:
        print(proc.stderr.decode("utf-8", "replace").strip()[-2000:])
        return 1
    sonuclar = json.loads(proc.stdout.decode("utf-8").strip())
    beklenen = {i: b for i, (_a, _g, b) in enumerate(TESTLER)}
    basarisiz = 0
    for i, (ad, sonuc) in enumerate(sonuclar):
        if i < len(TESTLER):
            if sonuc != beklenen[i]:
                basarisiz += 1
                print("FARK %s: %r <> %r" % (ad, sonuc, beklenen[i]))
            else:
                print("OK %s" % ad)
        elif sonuc != "HATA-OK":
            basarisiz += 1
            print("HATA-BEKLENIYORDU-AMA %s: %r" % (ad, sonuc))
        else:
            print("OK(hata) %s" % ad)
    print("%d/%d" % (len(sonuclar) - basarisiz, len(sonuclar)))
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(main())
