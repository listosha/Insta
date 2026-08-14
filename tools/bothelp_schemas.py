import sys,io,json,requests
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
spec=requests.get("https://main.bothelp.io/swagger/api.json",timeout=20).json()
paths=spec.get("paths",{})
def deref(ref,root):
    parts=ref.lstrip("#/").split("/"); o=root
    for p in parts: o=o[p]
    return o
def show(path,method):
    op=paths.get(path,{}).get(method)
    if not op: print(f"-- {method.upper()} {path}: not found"); return
    print(f"\n### {method.upper()} {path}")
    print("summary:",op.get("summary",""))
    # params
    for pr in op.get("parameters",[]):
        print(f"  param: {pr.get('name')} in={pr.get('in')} req={pr.get('required')}")
    rb=op.get("requestBody",{})
    cont=rb.get("content",{})
    for ct,meta in cont.items():
        sch=meta.get("schema",{})
        if "$ref" in sch: sch=deref(sch["$ref"],spec)
        print(f"  body [{ct}]:",json.dumps(sch,ensure_ascii=False)[:600])
for p,m in [("/v1/subscribers/{subscriber_id}/messages","post"),
            ("/v1/subscribers/{subscriber_id}","patch"),
            ("/v1/subscribers/{subscriber_id}/bot","post"),
            ("/v1/subscribers/{subscriber_id}/funnel","post"),
            ("/v1/funnels","get"),
            ("/v1/subscribers/{subscriber_id}/customFields","patch")]:
    show(p,m)
