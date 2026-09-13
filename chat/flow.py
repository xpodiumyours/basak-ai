import json,logging
from chat.prompts import KIMLIK_BLOGU,OLCU_YONLENDIRME,BIKIMLONDIRME_YONLENDIRME,TOOL_YONLENDIRME
from chat import context as ctx
from chat.gate import temizle as _temizle
logger=logging.getLogger(__name__)
def _j(o):return json.dumps(o,ensure_ascii=False)
def _konusmaci_ayir(t):
 import re
 e=re.search(r"\[([^\]]+)\]\s*$",t);return (t,None) if not e else (t[:e.start()].strip(),e.group(1))
def _profil_isle(t,k):
 try:
  from memory.profil import ogren,unut,blok
  m=ctx.hafiza_al()
  if not m or not t:return "",""
  s=unut(m,t)
  if s==-1:n="Not: Casper hakkındaki tüm profil bilgilerini SİLDİN. Bunu doğrula."
  elif s:n="Not: profilden %d kayıt sildin (istek: %s). Bunu doğrula."%(s,t)
  else:
   y=ogren(m,t,speaker=k or "");n=""
   if y:n="Not: profile yeni bilgi eklendi: %s. Kısaca doğrulayıp sohbete devam et."%"; ".join("%s=%s"%(a,d) for a,d in y)
  return blok(m),n
 except Exception as e:logger.warning("Profil islenemedi: %s",e);return "",""
_ARAC_ISARETLERI=("araştır","arastir","ara bakalım","ara bakalim","internetten","güncel","guncel","son durum","haber","fiyat","kaç para","kac para","kaça","kaca","ne kadar","rakip","pazar","hedef kitle","müşteri","musteri","trend","piyasa","kur","dolar","euro","hava durumu","hava nasıl","hava nasil","site","sayfa","link","http://","https://","www.","dosya","klasör","klasor","belge","masaüstü","masaustu","indirilenler","listele","oku","içinde ne","icinde ne","diskimde","bilgisayarımda","bilgisayarimda","planda","belgede","dokümanda","dokumanda","notlarda","hangi dosyada","geçiyor mu","geciyor mu","var mı","var mi","nerede yazıyor","nerede yaziyor","ara kodda","pr","pull request","ci","birleşti mi","birlesti mi","test geçti mi","test gecti mi","kontroller","yaz","kaydet","not al","dosya oluştur","dosya olustur","hatırlat","hatirlat","ajanda","bugün ne var","bugun ne var","görev","gorev","yapılacak","yapilacak","tamamladım","tamamladim","aç","ac","başlat","baslat","çalıştır","calistir","vixrex","numeramatch","xses","başak projesi","basak projesi","commit","dal ","branch","ne durumda","durumu ne","ne oldu","değişti","degisti","ekran görüntüsü","ekran goruntusu","görsel","gorsel","resim","fotoğraf","fotograf",".png",".jpg",".jpeg","şu görüntü","su goruntu")
def _arac_gerek(t):
 t=(t or "").lower();return any(k in t for k in _ARAC_ISARETLERI)
def _baglam_kur(t,s,k,araclar_acik=False):
 p,n=_profil_isle(t,k);q=s+(TOOL_YONLENDIRME if araclar_acik else "")+OLCU_YONLENDIRME+BIKIMLONDIRME_YONLENDIRME
 if k:q+="\nKonuşan: %s"%k
 m=[{"role":"system","content":KIMLIK_BLOGU},{"role":"system","content":q}];a=[] if araclar_acik else ctx.ilgili_anilar(t)
 if a:m.append({"role":"system","content":"Hafızadan:\n"+"\n".join("- %s"%x["text"][:300] for x in a[:5])})
 if p:m.append({"role":"system","content":p})
 if n:m.append({"role":"system","content":n})
 return m
def _kaydet(t,c,k,g,j,s):
 g += [{"role":"user","content":t,"oturum":ctx.OTURUM_ID},{"role":"assistant","content":c,"oturum":ctx.OTURUM_ID}];ctx.kaydet(ctx.HISTORY_FILE,g[-40:])
 try:
  from chat import oturum;oturum.kaydet_cift(t,c)
 except Exception as e:logger.warning("Oturum kaydi atlandi: %s",e)
 j("BasakUI.bitir("+_j(c)+", "+_j(k)+")");m=ctx.hafiza_al()
 if m and c:
  try:m.episodik_kaydet(t,c,speaker=s or "",onem=ctx.onem_puanla(t))
  except Exception as e:logger.warning("Ani kaydedilemedi: %s",e)
def mesaj_isle(t,b,s,j,tools=None):
 t,k=_konusmaci_ayir((t or "").strip());j("BasakUI.thinking()")
 if not t:j("BasakUI.error("+_j("Bos mesaj")+")");return
 mods=b.yerel_modeller()
 if not mods and not b.bulut_musait():j("BasakUI.error("+_j("Hicbir beyin yok: Ollama kapali ve bulut anahtarlari da hazir degil")+")");return
 model=ctx.yukle(ctx.SETTINGS_FILE,{}).get("model")
 if mods:
  if model not in mods:model=mods[0]
 else:model=None
 g=ctx.temizle_history([x for x in ctx.yukle(ctx.HISTORY_FILE,[]) if x.get("role")!="system"]);acik=bool(tools) and _arac_gerek(t);m=_baglam_kur(t,s,k,acik);p=ctx.gecmis_pencere(g)
 if acik:p=[x for x in p if x.get("role")=="user"][-3:]
 m+=p+[{"role":"user","content":t}]
 from brain.yayin import AracIstegi,SonHata
 y=None if acik else getattr(b,"cevapla_yayin",None)
 if y is not None:
  try:
   ps=[];kaynak=""
   for kaynak,parca in y(m,model):ps.append(parca);j("BasakUI.parca("+_j(parca)+")")
   tam=_temizle("".join(x if isinstance(x,str) else str(x) if x is not None else "" for x in ps))
   if tam:_kaydet(t,tam,kaynak or "bulut",g,j,k);return
  except AracIstegi:logger.info("Model arac istedi (arac yok) — tek seferlik yol")
  except SonHata as e:logger.info("Akis acilamadi (%s) — tek seferlik yol",e.ozet)
 try:r,kaynak=b.cevapla(m,model,tools=(tools if acik else None))
 except Exception as e:
  h=str(e);j("BasakUI.error("+_j("Cok fazla istek, biraz bekle" if "429" in h or "rate" in h.lower() else "Beyin hatasi: "+h[:150])+")");return
 tc=r.get("tool_calls") if isinstance(r,dict) else None
 if tc and tools:
  from chat.tools import arac_dongusu
  from tools import calistir
  c,n=arac_dongusu(tc,m,b,model,j,calistir,tools=tools);c=_temizle(c)
  if c:_kaydet(t,c,kaynak,g,j,k);return
  logger.info("Arac turu bos dondu (%d arac kostu)",n)
 c=_temizle(r.get("content","") if isinstance(r,dict) else r)
 if not c:j("BasakUI.error("+_j("Model bos cevap dondu")+")");return
 _kaydet(t,c,kaynak,g,j,k)
