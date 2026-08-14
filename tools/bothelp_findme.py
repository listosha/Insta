import sys,io,json,requests,collections
from datetime import datetime,timezone,timedelta
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
creds={}
with open(r"C:\Users\listo\OneDrive\Desktop\bothelp.txt",encoding="utf-8") as f:
    for line in f:
        if ":" in line and ("ID" in line or "Secret" in line):
            k,v=line.split(":",1); creds[k.strip().lower()]=v.strip()
tok=requests.post("https://oauth.bothelp.io/oauth2/token",data={"grant_type":"client_credentials","client_id":creds["id"],"client_secret":creds["secret"]},timeout=30).json()["access_token"]
H={"Authorization":f"Bearer {tok}"}; API="https://api.bothelp.io"
all_s=[]; after=None; seen=set(); g=0
while g<40:
    g+=1
    rr=requests.get(API+"/v1/subscribers?perPage=200"+(f"&after={after}" if after else ""),headers=H,timeout=40).json()
    d=rr.get("data",[]); fresh=[s for s in d if s["id"] not in seen]
    for s in fresh: seen.add(s["id"]); all_s.append(s)
    nx=(rr.get("paging") or {}).get("cursor",{}).get("after")
    if not fresh or nx is None or nx==after: break
    after=nx
tg=[s for s in all_s if s.get("channelType")=="telegram"]
tg.sort(key=lambda s:s.get("createdAt",0),reverse=True)
def dt(ts):
    try: return datetime.fromtimestamp(ts,tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except: return "?"
print("Freshest 8 Telegram contacts (by createdAt):")
for s in tg[:8]:
    print(f"  id={s.get('id')} {dt(s.get('createdAt',0))}UTC name={s.get('channelName')!r} subscribed={s.get('subscribed')} tags={s.get('tags')}")
# also anyone created today
today=datetime.now(timezone.utc).date()
todays=[s for s in all_s if datetime.fromtimestamp(s.get('createdAt',0),tz=timezone.utc).date()==today]
print(f"\nContacts created TODAY ({today}): {len(todays)}")
for s in todays:
    print(f"  id={s.get('id')} {dt(s.get('createdAt',0))} ch={s.get('channelType')} name={s.get('channelName')!r} tags={s.get('tags')}")

print("\n=== Message schema ===")
spec=requests.get("https://main.bothelp.io/swagger/api.json",timeout=20).json()
def deref(r):
    o=spec
    for p in r.lstrip("#/").split("/"): o=o[p]
    return o
msg=spec["components"]["schemas"].get("Message")
print(json.dumps(msg,ensure_ascii=False,indent=1)[:1200])
