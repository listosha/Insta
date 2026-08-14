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

EXCLUDE_UID={"788984484"}
EXCLUDE_BOTS=["arhkarusel","megapak","guide_pay_bot","vseagenti","iimarketolog"]  # «не мои»
def person_excluded(s):
    if str(s.get("userId")) in EXCLUDE_UID: return True
    nm=(s.get("name") or "").lower()+" "+(s.get("channelName") or "").lower()
    return any(w in nm for w in ("дубровск","мария","listosh","alexey","алексей"))
def bot_excluded(s):
    cn=(s.get("channelName") or "").lower()
    return any(b in cn for b in EXCLUDE_BOTS)

by_uid={}; dropped_only_excl=set(); all_uids=set()
for s in tg:
    if not s.get("subscribed") or person_excluded(s): continue
    uid=s.get("userId");
    if not uid: continue
    all_uids.add(uid)
    if bot_excluded(s): continue   # don't SEND from these bots
    cur=by_uid.get(uid)
    pref="волшебные пилюли" in (s.get("channelName") or "").lower()
    if cur is None or (pref and "волшебные пилюли" not in (cur.get("channelName") or "").lower()):
        by_uid[uid]=s
targets=list(by_uid.values())
dropped=len(all_uids)-len(by_uid)
print("AUDIENCE after removing non-owned bots:",len(targets),"people")
print("dropped (reachable ONLY via excluded bots):",dropped)
print("by sending bot:",dict(collections.Counter((s.get('channelName') or '?') for s in targets).most_common(10)))
ids=[s["id"] for s in targets]
json.dump(ids,open(r"C:\Users\listo\Downloads\bothelp_send_targets.json","w",encoding="utf-8"))
print("saved targets:",len(ids))
