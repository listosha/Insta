import sys,io,json,requests
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
spec=requests.get("https://main.bothelp.io/swagger/api.json",timeout=20).json()
sch=spec.get("components",{}).get("schemas",{})
print("ALL schema names:")
print(", ".join(sorted(sch.keys())))
print("\n--- schemas that look message/media related ---")
for name in sch:
    low=name.lower()
    if any(w in low for w in ("message","media","image","photo","file","attach","button","content","keyboard")):
        print(f"\n### {name}")
        print(json.dumps(sch[name],ensure_ascii=False)[:700])
# also re-check the messages endpoint requestBody fully
op=spec["paths"]["/v1/subscribers/{subscriber_id}/messages"]["post"]
print("\n=== messages endpoint requestBody ===")
print(json.dumps(op.get("requestBody",{}),ensure_ascii=False)[:800])
