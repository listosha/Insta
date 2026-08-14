import sys, io, json, csv, requests, collections
from datetime import datetime, timezone
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
creds={}
with open(r"C:\Users\listo\OneDrive\Desktop\bothelp.txt",encoding="utf-8") as f:
    for line in f:
        if ":" in line and ("ID" in line or "Secret" in line):
            k,v=line.split(":",1); creds[k.strip().lower()]=v.strip()
tok=requests.post("https://oauth.bothelp.io/oauth2/token",data={"grant_type":"client_credentials","client_id":creds["id"],"client_secret":creds["secret"]},timeout=30).json()["access_token"]
H={"Authorization":f"Bearer {tok}"}; API="https://api.bothelp.io"

all_s=[]; seen=set(); after=None; guard=0
while guard<500:
    guard+=1
    url=API+"/v1/subscribers?perPage=200"+(f"&after={after}" if after else "")
    rr=requests.get(url,headers=H,timeout=40)
    if not rr.ok: print("stop",rr.status_code,rr.text[:120]); break
    j=rr.json(); data=j.get("data",[])
    fresh=[s for s in data if s.get("id") not in seen]
    for s in fresh: seen.add(s["id"]); all_s.append(s)
    nxt=(j.get("paging") or {}).get("cursor",{}).get("after")
    if not fresh or nxt is None or nxt==after: break
    after=nxt
print("pages:",guard,"| TOTAL unique subscribers:",len(all_s))
chan=collections.Counter(s.get("channelType","?") for s in all_s)
print("by channel:",dict(chan))
print("with email:",sum(1 for s in all_s if s.get("email")),"| subscribed=true:",sum(1 for s in all_s if s.get("subscribed")))
tagc=collections.Counter()
for s in all_s:
    if isinstance(s.get("tags"),list):
        for x in s["tags"]: tagc[x if isinstance(x,str) else json.dumps(x,ensure_ascii=False)]+=1
print("Top tags:",dict(tagc.most_common(20)))
ig=[s for s in all_s if s.get("channelType")=="instagram"]
print("INSTAGRAM:",len(ig),"| names:",dict(collections.Counter(s.get("channelName") for s in ig)))
out=r"C:\Users\listo\Downloads\bothelp-export.csv"
keys=sorted({k for s in all_s for k in s.keys()})
with open(out,"w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=keys); w.writeheader()
    for s in all_s: w.writerow({k:(json.dumps(s.get(k),ensure_ascii=False) if isinstance(s.get(k),(list,dict)) else s.get(k,"")) for k in keys})
print("CSV ->",out)
