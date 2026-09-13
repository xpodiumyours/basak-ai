import subprocess
DEPOLAR={"basak":"xpodiumyours/basak-ai","vixrex":"xpodiumyours/vixrex","numeramatch":"xpodiumyours/NumeraMatch","xses":"xpodiumyours/xses"}
def _repo(proje):return DEPOLAR.get((proje or "").strip().lower())
def _gh(argv):
 try:r=subprocess.run(["gh"]+list(argv),capture_output=True,text=True,timeout=20,shell=False,encoding="utf-8",errors="replace")
 except Exception as e:return {"error":"gh calismadi: %s"%str(e)[:120]}
 if r.returncode!=0:return {"error":(r.stderr or r.stdout or "gh hata verdi").strip()[:500]}
 cikti=(r.stdout or "").strip();return {"result":(cikti[:4000]+("\n...(kisaltildi)" if len(cikti)>4000 else "")) or "[]"}
def github_durum(proje,islem="pr_list",pr_numarasi=None,durum="open"):
 repo=_repo(proje)
 if repo is None:return {"error":"Bilinmeyen proje. Projeler: basak, vixrex, numeramatch, xses"}
 islem=(islem or "pr_list").strip().lower()
 if islem=="pr_list":
  state=(durum or "open").strip().lower()
  if state not in ("open","closed","all"):return {"error":"PR durumu open, closed veya all olmali."}
  return _gh(["pr","list","--repo",repo,"--state",state,"--json","number,title,state,headRefName"])
 if islem=="pr_view":
  try:numara=int(pr_numarasi)
  except (TypeError,ValueError):return {"error":"PR numarasi gerekli."}
  if numara<1:return {"error":"PR numarasi pozitif olmali."}
  return _gh(["pr","view",str(numara),"--repo",repo,"--json","number,title,state,mergedAt,statusCheckRollup"])
 if islem=="run_list":return _gh(["run","list","--repo",repo,"--limit","5","--json","name,status,conclusion,headBranch"])
 return {"error":"Islem pr_list, pr_view veya run_list olmali."}
