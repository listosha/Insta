import sys, io, json, requests, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
creds={}
with open(r"C:\Users\listo\OneDrive\Desktop\bothelp.txt",encoding="utf-8") as f:
    for line in f:
        if ":" in line and ("ID" in line or "Secret" in line):
            k,v=line.split(":",1); creds[k.strip().lower()]=v.strip()
r=requests.post("https://oauth.bothelp.io/oauth2/token",data={"grant_type":"client_credentials","client_id":creds["id"],"client_secret":creds["secret"]},timeout=30)
tok=r.json()["access_token"]; H={"Authorization":f"Bearer {tok}"}; API="https://api.bothelp.io"

print("=== endpoint discovery (/v1) ===")
for p in ["/v1/channels","/v1/tags","/v1/flows","/v1/sequences","/v1/account","/v1/me","/v1/bots","/v1/subscribers/2","/v1/variables","/v1/customFields","/v1/broadcasts","/v1/messages"]:
    try:
        rr=requests.get(API+p,headers=H,timeout=20); b=rr.text[:160].replace("\n"," ")
        print(f"GET {p:24} -> {rr.status_code} {b}")
    except Exception as e: print(p,"ERR",e)

print("\n=== subscribers summary (paging) ===")
total=0; chan=collections.Counter(); withemail=0; sample=[]; page=1; cursor=None
url=API+"/v1/subscribers?perPage=200"
while url and page<=15:
    rr=requests.get(url,headers=H,timeout=30)
    if not rr.ok: print("stop",rr.status_code,rr.text[:120]); break
    j=rr.json(); data=j.get("data",[])
    for s in data:
        total+=1
        chan[s.get("channelType","?")]+=1
        if s.get("email"): withemail+=1
        if len(sample)<3: sample.append({k:s.get(k) for k in ("id","channelType","channelName","email","subscribed")})
    # pagination
    meta=j.get("meta") or j.get("pagination") or {}
    nxt=(j.get("links") or {}).get("next") if isinstance(j.get("links"),dict) else None
    if nxt: url=nxt
    elif len(data)==200:
        page+=1; url=API+f"/v1/subscribers?perPage=200&page={page}"
    else: url=None
    page_guard=page
print("TOTAL subscribers seen:",total)
print("by channel:",dict(chan))
print("with email:",withemail)
print("sample:",json.dumps(sample,ensure_ascii=False))
