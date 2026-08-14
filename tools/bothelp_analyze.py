import sys,io,json,requests,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
creds={}
with open(r"C:\Users\listo\OneDrive\Desktop\bothelp.txt",encoding="utf-8") as f:
    for line in f:
        if ":" in line and ("ID" in line or "Secret" in line):
            k,v=line.split(":",1); creds[k.strip().lower()]=v.strip()
tok=requests.post("https://oauth.bothelp.io/oauth2/token",data={"grant_type":"client_credentials","client_id":creds["id"],"client_secret":creds["secret"]},timeout=30).json()["access_token"]
H={"Authorization":f"Bearer {tok}"}; API="https://api.bothelp.io"
S=[]; after=None; seen=set(); g=0
while g<40:
    g+=1
    rr=requests.get(API+"/v1/subscribers?perPage=200"+(f"&after={after}" if after else ""),headers=H,timeout=40).json()
    d=rr.get("data",[]); fr=[s for s in d if s["id"] not in seen]
    for s in fr: seen.add(s["id"]); S.append(s)
    nx=(rr.get("paging") or {}).get("cursor",{}).get("after")
    if not fr or nx is None or nx==after: break
    after=nx

tg=[s for s in S if s.get("channelType")=="telegram"]
# group by telegram userId -> person
people=collections.defaultdict(lambda:{"tags":set(),"reachable":False,"rows":0,"names":set()})
for s in tg:
    uid=s.get("userId") or f"row{s['id']}"
    p=people[uid]; p["rows"]+=1
    if s.get("subscribed"): p["reachable"]=True
    if s.get("name"): p["names"].add(s["name"])
    for t in (s.get("tags") or []):
        if isinstance(t,str): p["tags"].add(t)
N=len(people)
reach=sum(1 for p in people.values() if p["reachable"])
def has(p,pre): return any(t.startswith(pre) for t in p["tags"])
buyers=[u for u,p in people.items() if has(p,"оплата_")]
lm=[u for u,p in people.items() if has(p,"лм_")]
lm_only=[u for u,p in people.items() if has(p,"лм_") and not has(p,"оплата_")]
notag=[u for u,p in people.items() if not p["tags"]]
print(f"=== TELEGRAM база (схлопнуто по людям) ===")
print(f"уникальных людей: {N}  | достижимых (subscribed): {reach}  | строк-контактов: {len(tg)}")
print(f"ПОКУПАТЕЛИ (есть оплата_*): {len(buyers)}  ({len(buyers)*100//N}%)")
print(f"лид-магнит, но НЕ купили (реактивация!): {len(lm_only)}")
print(f"только лид-магнит (любой лм_): {len(lm)}  | вообще без тегов: {len(notag)}")
# product breakdown unique people
prod=collections.Counter()
for u,p in people.items():
    for t in p["tags"]:
        if t.startswith("оплата_"): prod[t]+=1
print("\nПокупки по продуктам (уник. людей):")
for t,c in prod.most_common(): print(f"  {t:40} {c}")
# multi-buyers
multi=[u for u,p in people.items() if sum(1 for t in p["tags"] if t.startswith("оплата_"))>=2]
print(f"\nкупили 2+ продукта (лучшие клиенты): {len(multi)}")
lmc=collections.Counter()
for u,p in people.items():
    for t in p["tags"]:
        if t.startswith("лм_"): lmc[t]+=1
print("\nЛид-магниты по темам (уник. людей):")
for t,c in lmc.most_common(12): print(f"  {t:30} {c}")
