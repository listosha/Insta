import sys,io,json,requests
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
creds={}
with open(r"C:\Users\listo\OneDrive\Desktop\bothelp.txt",encoding="utf-8") as f:
    for line in f:
        if ":" in line and ("ID" in line or "Secret" in line):
            k,v=line.split(":",1); creds[k.strip().lower()]=v.strip()
tok=requests.post("https://oauth.bothelp.io/oauth2/token",data={"grant_type":"client_credentials","client_id":creds["id"],"client_secret":creds["secret"]},timeout=30).json()["access_token"]
H={"Authorization":f"Bearer {tok}"}; API="https://api.bothelp.io"
r=requests.get(API+"/v1/subscribers?perPage=5",headers=H,timeout=30); j=r.json()
print("top-level keys:",list(j.keys()))
print("data len with perPage=5:",len(j.get("data",[])))
for k in j:
    if k!="data": print(f"  {k}:",json.dumps(j[k],ensure_ascii=False)[:300])
# try cursor/offset variants
for q in ["?perPage=200&page=2","?perPage=200&offset=100","?limit=200&offset=100","?perPage=200&cursor=100"]:
    rr=requests.get(API+"/v1/subscribers"+q,headers=H,timeout=30)
    ids=[s.get("id") for s in rr.json().get("data",[])][:3]
    n=len(rr.json().get("data",[]))
    print(f"{q:34} -> {rr.status_code} n={n} first_ids={ids}")
