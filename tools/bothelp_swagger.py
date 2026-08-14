import sys,io,re,json,requests
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
# 1) fetch swagger HTML, find spec url
html=requests.get("https://main.bothelp.io/swagger",timeout=20).text
cands=set(re.findall(r'["\'](/[^"\']*?(?:api-docs|swagger[^"\']*|openapi[^"\']*)\.?(?:json|yaml)?)["\']',html))
cands|=set(re.findall(r'url\s*:\s*["\']([^"\']+)["\']',html))
print("spec candidates in HTML:",cands)
base="https://main.bothelp.io"
tryurls=[base+c if c.startswith("/") else c for c in cands]+[
  base+"/v3/api-docs",base+"/openapi.json",base+"/api/swagger.json",
  base+"/docs/swagger.json","https://api.bothelp.io/v3/api-docs","https://api.bothelp.io/openapi.json"]
spec=None
for u in tryurls:
    try:
        r=requests.get(u,timeout=20); ct=r.headers.get("content-type","")
        ok=r.ok and ("json" in ct or r.text.strip().startswith("{"))
        print(f"{u} -> {r.status_code} {ct[:25]} {'JSON!' if ok else ''}")
        if ok and not spec:
            try: spec=r.json()
            except: pass
    except Exception as e: print(u,"ERR",str(e)[:60])
if spec:
    paths=spec.get("paths",{})
    print("\nPATHS:",len(paths))
    for p,m in sorted(paths.items()):
        print("  ",", ".join(x.upper() for x in m if x.lower() in("get","post","put","patch","delete")),p)
