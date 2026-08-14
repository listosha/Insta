import sys,io,json,requests
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
    d=rr.get("data",[]); fr=[s for s in d if s["id"] not in seen]
    for s in fr: seen.add(s["id"]); all_s.append(s)
    nx=(rr.get("paging") or {}).get("cursor",{}).get("after")
    if not fr or nx is None or nx==after: break
    after=nx
print("total base:",len(all_s))
needles=["listosha","listosh","алексей","alexey"]
def hit(s):
    blob=json.dumps(s,ensure_ascii=False).lower()
    return any(n in blob for n in needles)
found=[s for s in all_s if hit(s)]
print("matches:",len(found))
from collections import Counter
print("by channel:",dict(Counter(s.get("channelType") for s in found)))
tg=[s for s in found if s.get("channelType")=="telegram"]
print("\nTELEGRAM matches:",len(tg))
for s in tg[:15]:
    print("  ",{k:s.get(k) for k in ("id","channelName","userId","subscribed","email")})
# also show available fields once
if all_s: print("\nfields per subscriber:",sorted(all_s[0].keys()))
