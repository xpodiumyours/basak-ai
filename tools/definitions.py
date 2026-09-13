"""tools/definitions.py — Modele sunulan araç şemaları."""

WEB_ARAMA={"type":"function","function":{"name":"web_search","description":"Internette guncel bilgi ara.","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}}
SAYFA_OKU={"type":"function","function":{"name":"sayfa_oku","description":"Web sayfasi oku.","parameters":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}}
DOSYA_OKU={"type":"function","function":{"name":"read_file","description":"Dosya oku.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}}
KLASOR_LISTELE={"type":"function","function":{"name":"list_files","description":"Klasor listele.","parameters":{"type":"object","properties":{"folder":{"type":"string"}},"required":["folder"]}}}
GIT_DURUM={"type":"function","function":{"name":"git_durum","description":"Proje durumunu olc.","parameters":{"type":"object","properties":{"proje":{"type":"string"}},"required":["proje"]}}}
BELGE_ARA={"type":"function","function":{"name":"belge_ara","description":"Markdown belgelerinde ara.","parameters":{"type":"object","properties":{"proje":{"type":"string"},"sorgu":{"type":"string"}},"required":["proje","sorgu"]}}}
DOSYA_BILGI={"type":"function","function":{"name":"dosya_bilgi","description":"Dosya bilgisi olc.","parameters":{"type":"object","properties":{"proje":{"type":"string"},"yol":{"type":"string"}},"required":["proje","yol"]}}}
DOSYA_YAZ={"type":"function","function":{"name":"write_file_tool","description":"Yalniz knowledge altina dosya kaydet.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}}
HATIRLATMALAR={"type":"function","function":{"name":"get_reminders","description":"Hatirlatmalari getir.","parameters":{"type":"object","properties":{}}}}
GOREV_EKLE={"type":"function","function":{"name":"add_task","description":"Gorev ekle.","parameters":{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}}}
GOREV_LISTELE={"type":"function","function":{"name":"list_tasks","description":"Gorevleri listele.","parameters":{"type":"object","properties":{}}}}
GOREV_TAMAMLA={"type":"function","function":{"name":"complete_task","description":"Gorevi tamamlandi isaretle.","parameters":{"type":"object","properties":{"task_id":{"type":"integer"}},"required":["task_id"]}}}
UYGULAMA_AC={"type":"function","function":{"name":"ac_uygulama","description":"Beyaz listedeki uygulamayi ac.","parameters":{"type":"object","properties":{"uygulama":{"type":"string","description":"tarayici | notepad | calculator | file_manager | vscode"},"parametre":{"type":"string"}},"required":["uygulama"]}}}
GORUNTU_OKU={"type":"function","function":{"name":"image_analyze","description":"Goruntu incele.","parameters":{"type":"object","properties":{"path":{"type":"string"},"soru":{"type":"string"}},"required":["path"]}}}

TOOLS=[WEB_ARAMA,SAYFA_OKU,DOSYA_OKU,KLASOR_LISTELE,GIT_DURUM,BELGE_ARA,DOSYA_BILGI,DOSYA_YAZ,HATIRLATMALAR,GOREV_EKLE,GOREV_LISTELE,GOREV_TAMAMLA,UYGULAMA_AC,GORUNTU_OKU]
TANINMIS_TOOLLAR=frozenset(t["function"]["name"] for t in TOOLS)
