import json,logging
logger=logging.getLogger(__name__);TUR_SINIRI=4;ARAC_SONUC_TAVAN=4000
DURUM_METNI={"web_search":"İnternette aranıyor","sayfa_oku":"Sayfa okunuyor","read_file":"Dosya okunuyor","list_files":"Klasör listeleniyor","git_durum":"Proje durumu ölçülüyor","git_gecmis":"Git geçmişi okunuyor","git_degisenler":"Değişiklikler ölçülüyor","belge_ara":"Belgelerde aranıyor","dosya_bilgi":"Dosya bilgisi ölçülüyor","icerik_ara":"Kodda aranıyor","github_durum":"GitHub durumu ölçülüyor","write_file_tool":"Dosya yazılıyor","get_reminders":"Hatırlatmalar kontrol ediliyor","add_task":"Görev ekleniyor","list_tasks":"Görevler listeleniyor","complete_task":"Görev tamamlanıyor","ac_uygulama":"Uygulama açılıyor","image_analyze":"Görüntü inceleniyor"}
DURUM_ALANI=("query","url","path","folder","proje","sorgu","text","task_id","uygulama","islem","dosya","taban")
def _j(o):return json.dumps(o,ensure_ascii=False)
def parse_args(h):
 if isinstance(h,dict):return h
 try:
  c=json.loads(h or "{}");return c if isinstance(c,dict) else {}
 except (ValueError,TypeError):return {}
def _durum(n,a):
 e=DURUM_METNI.get(n,"Çalışıyor");d=""
 for x in DURUM_ALANI:
  if (a or {}).get(x):d=str(a[x])[:70];break
 return "%s: %s"%(e,d) if d else e+"..."
def sonucu_donustur(s):
 if isinstance(s,dict):
  if s.get("error"):return "Hata: %s"%s["error"]
  return str(s.get("result",""))
 return str(s)
def _kaynak_satiri(c,k):return c if not k or not c else c+"\n\nKaynaklar: "+"; ".join(k[:5])
def arac_dongusu(tool_calls,mesajlar,brain,model,js_callback,calistir,tools=None,tur_siniri=TUR_SINIRI):
 from chat.gate import temizle
 from tools.definitions import TANINMIS_TOOLLAR
 expanded=list(mesajlar);kaynaklar=[];kosan=0;tur_sonuclari=[]
 for tur in range(tur_siniri):
  tur_sonuclari=[]
  for call in tool_calls:
   f=call.get("function",{});ad=f.get("name","");args=parse_args(f.get("arguments","{}"))
   if ad not in TANINMIS_TOOLLAR:continue
   js_callback("BasakUI.toolStatus("+_j(_durum(ad,args))+")");net=sonucu_donustur(calistir(ad,args));tur_sonuclari.append((ad,net))
   if not net.startswith("Hata:"):
    kosan+=1;etiket=next((str(args[x]) for x in DURUM_ALANI if args.get(x)),ad)[:60]
    if etiket not in kaynaklar:kaynaklar.append(etiket)
  if not tur_sonuclari:break
  expanded=expanded+[{"role":"assistant","content":"","tool_calls":tool_calls}]
  for i,(_ad,sonuc) in enumerate(tur_sonuclari):
   k=sonuc if len(sonuc)<=ARAC_SONUC_TAVAN else sonuc[:ARAC_SONUC_TAVAN].rstrip()+"... [devami kirpildi]"
   expanded.append({"role":"tool","tool_call_id":tool_calls[i].get("id","call_%d"%i),"content":k})
  o="\n".join("%s: %s"%(ad,net[:800]) for ad,net in tur_sonuclari);sonraki=tools if tur<tur_siniri-1 else None
  expanded+=[{"role":"user","content":"Araç sonuçları:\n"+o+"\n\nŞimdi sonuçları doğal Türkçe ile özetle; olmayan şeyi uydurma."}]
  try:yanit,_=brain.cevapla(expanded,model,tools=sonraki)
  except Exception as e:logger.warning("Arac turu sonrasi cevap alinamadi: %s",e);break
  yeni=yanit.get("tool_calls")
  if yeni:tool_calls=yeni;continue
  cevap=temizle(yanit.get("content",""))
  if cevap:return _kaynak_satiri(cevap,kaynaklar),kosan
  break
 return "\n".join(net for _ad,net in tur_sonuclari if net),kosan
