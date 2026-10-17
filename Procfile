# Basak — Linux/konteyner calisma sozlesmesi (P2.3).
#
# Vercel'de platform `app.py`yi kendisi calistirir (`vercel.json`); bu satir
# Vercel DISINDAKI ortamlar icindir (Koyeb run command, Heroku tarzi
# platformlar, yerel `uvicorn`). Komut `requirements.txt`teki `uvicorn`
# pininden gelir; ayri bir calisma bicimi uretilmez.
#
# Onay olcutu (olculdu 2026-10-14): bu satirdaki komut, temiz bir sanal
# ortamda `requirements.txt` kurulduktan sonra acilir ve `/healthz` 200 doner.
web: uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
