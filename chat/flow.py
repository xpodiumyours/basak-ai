"""chat/flow.py — Ana sohbet akışı."""
import json,logging
from chat.prompts import KIMLIK_BLOGU,OLCU_YONLENDIRME,BIKIMLONDIRME_YONLENDIRME,TOOL_YONLENDIRME
from chat import context as ctx
from chat.gate import temizle as _temizle
logger=logging.getLogger(__name__)
def _j(obj):return json.dumps(obj,ensure_ascii=False)
def _konusmaci_ayir(text):
 import re
 e=re.search(r"\[([^\]]+)\]\s*$",text)
 return (text,None) if not e else (text[:e.start()].strip(),e.group(1))
def _profil_isle(text,konusmaci):
 try:
  from memory.profil import ogren,unut,blok
  motor=ctx.hafiza_al()
  if not motor or not text:return "",""
  silinen=unut(motor,text)
  if silinen==-1:not_="Not: Casper hakkındaki tüm profil bilgilerini SİLDİN. Bunu doğrula."
  elif silinen:not_="Not: profilden %d kayıt sildin (istek: %s). Bunu doğrula."%(silinen,text)
  else:
   yeniler=ogren(motor,text,speaker=konusmaci or "");not_=""
   if yeniler:not_="Not: profile yeni bilgi eklendi: %s. Kısaca doğrulayıp sohbete devam et."%"; ".join("%s=%s"%(a,d) for a,d in yeniler)
  return blok(motor),not_
 except Exception as e:logger.warning("Profil islenemedi: %s",e);return "",""
_ARAC_ISARETLERI=("araştır","arastir","ara bakalım","ara bakalim","internetten","güncel","guncel","son durum","haber","fiyat","kaç para","kac para","kaça","kaca","ne kadar","rakip","pazar","hedef kitle","müşteri","musteri","trend","piyasa","kur","dolar","euro","hava durumu","hava nasıl","hava nasil","site","sayfa","link","http://","https://","www.","dosya","klasör","klasor","belge","masaüstü","masaustu","indirilenler","listele","oku","içinde ne","icinde ne","diskimde","bilgisayarımda","bilgisayarimda","planda","belgede","dokümanda","dokumanda","notlarda","hangi dosyada","geçiyor mu","geciyor mu","var mı","var mi","nerede yazıyor","nerede yaziyor","ara kodda","yaz","kaydet","not al","dosya oluştur","dosya olustur","hatırlat","hatirlat","ajanda","bugün ne var","bugun ne var","görev","gorev","yapılacak","yapilacak","tamamladım","tamamladim","aç","ac","başlat","baslat","çalıştır","calistir","vixrex","numeramatch","xses","başak projesi","basak projesi","commit","dal ","branch","ne durumda","durumu ne","ne oldu","değişti","degisti","ekran görüntüsü","ekran goruntusu","görsel","gorsel","resim","fotoğraf","fotograf",".png",".jpg",".jpeg","şu görüntü","su goruntu")
def _arac_gerek(text):
 t=(text or "").lower();return any(k in t for k in _ARAC_ISARETLERI)
def _baglam_kur(text,system_prompt,konusmaci,araclar_acik=False):
 profil_blogu,ogrenme_notu=_profil_isle(text,konusmaci);tam_prompt=system_prompt
 if araclar_acik:tam_prompt+=TOOL_YONLENDIRME
 tam_prompt+=OLCU_YONLENDIRME+BIKIMLONDIRME_YONLENDIRME
 if konusmaci:tam_prompt+="\nKonuşan: %s"%konusmaci
 mesajlar=[{"role":"system","content":KIMLIK_BLOGU},{"role":"system","content":tam_prompt}]
 anilar=[] if araclar_acik else ctx.ilgili_anilar(text)
 if anilar:mesajlar.append({"role":"system","content":"Hafızadan:\n"+"\n".join("- %s"%a["text"][:300] for a in anilar[:5])})
 if profil_blogu:mesajlar.append({"role":"system","content":profil_blogu})
 if ogrenme_notu:mesajlar.append({"role":"system","content":ogrenme_notu})
 return mesajlar
def _kaydet(text,cevap,kaynak,gecmis,js_callback,konusmaci):
 gecmis += [{"role":"user","content":text,"oturum":ctx.OTURUM_ID},{"role":"assistant","content":cevap,"oturum":ctx.OTURUM_ID}];ctx.kaydet(ctx.HISTORY_FILE,gecmis[-40:])
 try:
  from chat import oturum;oturum.kaydet_cift(text,cevap)
 except Exception as e:logger.warning("Oturum kaydi atlandi: %s",e)
 js_callback("BasakUI.bitir("+_j(cevap)+", "+_j(kaynak)+")")
 motor=ctx.hafiza_al()
 if motor and cevap:
  try:motor.episodik_kaydet(text,cevap,speaker=konusmaci or "",onem=ctx.onem_puanla(text))
  except Exception as e:logger.warning("Ani kaydedilemedi: %s",e)
def mesaj_isle(text,brain,system_prompt,js_callback,tools=None):
 text,konusmaci=_konusmaci_ayir((text or "").strip());js_callback("BasakUI.thinking()")
 if not text:js_callback("BasakUI.error("+_j("Bos mesaj")+")");return
 modeller=brain.yerel_modeller()
 if not modeller and not brain.bulut_musait():js_callback("BasakUI.error("+_j("Hicbir beyin yok: Ollama kapali ve bulut anahtarlari da hazir degil")+")");return
 model=ctx.yukle(ctx.SETTINGS_FILE,{}).get("model")
 if modeller:
  if model not in modeller:model=modeller[0]
 else:model=None
 gecmis=ctx.temizle_history([m for m in ctx.yukle(ctx.HISTORY_FILE,[]) if m.get("role")!="system"]);arac_acik=bool(tools) and _arac_gerek(text);mesajlar=_baglam_kur(text,system_prompt,konusmaci,arac_acik);pencere=ctx.gecmis_pencere(gecmis)
 if arac_acik:pencere=[m for m in pencere if m.get("role")=="user"][-3:]
 mesajlar+=pencere+[{"role":"user","content":text}]
 from brain.yayin import AracIstegi,SonHata
 yayin=None if arac_acik else getattr(brain,"cevapla_yayin",None)
 if yayin is not None:
  try:
   parcalar=[];kaynak=""
   for kaynak,parca in yayin(mesajlar,model):parcalar.append(parca);js_callback("BasakUI.parca("+_j(parca)+")")
   tam=_temizle("".join(p if isinstance(p,str) else str(p) if p is not None else "" for p in parcalar))
   if tam:_kaydet(text,tam,kaynak or "bulut",gecmis,js_callback,konusmaci);return
  except AracIstegi:logger.info("Model arac istedi (arac yok) — tek seferlik yol")
  except SonHata as e:logger.info("Akis acilamadi (%s) — tek seferlik yol",e.ozet)
 try:yanit,kaynak=brain.cevapla(mesajlar,model,tools=(tools if arac_acik else None))
 except Exception as e:
  hata=str(e)
  if "429" in hata or "rate" in hata.lower():js_callback("BasakUI.error("+_j("Cok fazla istek, biraz bekle")+")")
  else:js_callback("BasakUI.error("+_j("Beyin hatasi: "+hata[:150])+")")
  return
 tool_calls=yanit.get("tool_calls") if isinstance(yanit,dict) else None
 if tool_calls and tools:
  from chat.tools import arac_dongusu
  from tools import calistir
  cevap,kosan=arac_dongusu(tool_calls,mesajlar,brain,model,js_callback,calistir,tools=tools);cevap=_temizle(cevap)
  if cevap:_kaydet(text,cevap,kaynak,gecmis,js_callback,konusmaci);return
  logger.info("Arac turu bos dondu (%d arac kostu)",kosan)
 cevap=_temizle(yanit.get("content","") if isinstance(yanit,dict) else yanit)
 if not cevap:js_callback("BasakUI.error("+_j("Model bos cevap dondu")+")");return
 _kaydet(text,cevap,kaynak,gecmis,js_callback,konusmaci)
