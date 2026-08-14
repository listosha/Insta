import sys, io, json, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
creds={}
with open(r"C:\Users\listo\OneDrive\Desktop\bothelp.txt",encoding="utf-8") as f:
    for line in f:
        if ":" in line and ("ID" in line or "Secret" in line):
            k,v=line.split(":",1); creds[k.strip().lower()]=v.strip()
tok=requests.post("https://oauth.bothelp.io/oauth2/token",data={"grant_type":"client_credentials","client_id":creds["id"],"client_secret":creds["secret"]},timeout=30).json()["access_token"]
H={"Authorization":f"Bearer {tok}"}; API="https://api.bothelp.io"

print("=== /v1/bots (channels/accounts) ===")
r=requests.get(API+"/v1/bots",headers=H,timeout=30)
print(r.status_code)
try: print(json.dumps(r.json(),ensure_ascii=False,indent=2)[:1500])
except: print(r.text[:1000])

print("\n=== try swagger spec ===")
for u in ["https://main.bothelp.io/swagger/v1/swagger.json","https://main.bothelp.io/swagger.json",
          "https://api.bothelp.io/swagger.json","https://main.bothelp.io/v1/swagger.json",
          "https://main.bothelp.io/swagger/swagger.json","https://main.bothelp.io/api-docs"]:
    try:
        rr=requests.get(u,timeout=20)
        ct=rr.headers.get("content-type","")
        print(f"{u} -> {rr.status_code} {ct[:30]}")
        if rr.ok and "json" in ct:
            spec=rr.json(); paths=spec.get("paths",{})
            print("   PATHS FOUND:",len(paths))
            for p,methods in sorted(paths.items()):
                print("   ",", ".join(m.upper() for m in methods),p)
            break
    except Exception as e: print(u,"ERR",str(e)[:80])

print("\n=== my own contacts (Alexey) ===")
# pull base via cursor, find Alexey
all_s=[]; after=None; seen=set(); g=0
while g<40:
    g+=1
    rr=requests.get(API+"/v1/subscribers?perPage=200"+(f"&after={after}" if after else ""),headers=H,timeout=40).json()
    d=rr.get("data",[]); fresh=[s for s in d if s["id"] not in seen]
    for s in fresh: seen.add(s["id"]); all_s.append(s)
    nx=(rr.get("paging") or {}).get("cursor",{}).get("after")
    if not fresh or nx is None or nx==after: break
    after=nx
alex=[s for s in all_s if "listosh" in (s.get("channelName") or "").lower() or "алексей" in (s.get("channelName") or "").lower()]
print("found",len(alex),"Alexey-like contacts; showing first 8:")
for s in alex[:8]:
    print(f"  id={s.get('id')} ch={s.get('channelType')} name={s.get('channelName')!r} userId={s.get('userId')} subscribed={s.get('subscribed')}")
