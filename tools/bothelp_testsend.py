import sys,io,json,requests
from datetime import datetime,timezone
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
creds={}
with open(r"C:\Users\listo\OneDrive\Desktop\bothelp.txt",encoding="utf-8") as f:
    for line in f:
        if ":" in line and ("ID" in line or "Secret" in line):
            k,v=line.split(":",1); creds[k.strip().lower()]=v.strip()
tok=requests.post("https://oauth.bothelp.io/oauth2/token",data={"grant_type":"client_credentials","client_id":creds["id"],"client_secret":creds["secret"]},timeout=30).json()["access_token"]
H={"Authorization":f"Bearer {tok}"}; API="https://api.bothelp.io"

# re-pull to catch any contact created/updated just now
all_s=[]; after=None; seen=set(); g=0
while g<40:
    g+=1
    rr=requests.get(API+"/v1/subscribers?perPage=200"+(f"&after={after}" if after else ""),headers=H,timeout=40).json()
    d=rr.get("data",[]); fr=[s for s in d if s["id"] not in seen]
    for s in fr: seen.add(s["id"]); all_s.append(s)
    nx=(rr.get("paging") or {}).get("cursor",{}).get("after")
    if not fr or nx is None or nx==after: break
    after=nx
today=datetime.now(timezone.utc).date()
todays=[s for s in all_s if datetime.fromtimestamp(s.get('createdAt',0),tz=timezone.utc).date()==today and s.get("channelType")=="telegram"]
if todays:
    todays.sort(key=lambda s:s.get("createdAt",0),reverse=True); target=todays[0]; why="created today"
else:
    target=next((s for s in all_s if s.get("id")==3330),None); why="fallback id=3330 (Волшебные пилюли)"
print("TARGET:",why,"->",{k:target.get(k) for k in ("id","channelType","channelName","subscribed")})

sid=target["id"]
body=[{"content":"Проверка связи ✅ Это тестовое сообщение через API (Claude Code). Если видишь его — автоматическая отправка работает. Можно удалить."}]
for ct in ("application/vnd.api+json","application/json"):
    h=dict(H); h["Content-Type"]=ct
    r=requests.post(f"{API}/v1/subscribers/{sid}/messages",headers=h,data=json.dumps(body),timeout=30)
    print(f"\nPOST messages [{ct}] -> {r.status_code}: {r.text[:300]}")
    if r.ok: break
