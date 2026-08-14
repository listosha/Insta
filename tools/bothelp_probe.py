import sys, io, json, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

creds = {}
with open(r"C:\Users\listo\OneDrive\Desktop\bothelp.txt", encoding="utf-8") as f:
    for line in f:
        if ":" in line and ("ID" in line or "Secret" in line):
            k, v = line.split(":", 1)
            creds[k.strip().lower()] = v.strip()
CLIENT_ID = creds.get("id")
CLIENT_SECRET = creds.get("secret")
print("client_id read:", CLIENT_ID[:12], "...  secret read:", bool(CLIENT_SECRET))

TOKEN_URL = "https://oauth.bothelp.io/oauth2/token"
API = "https://api.bothelp.io"

def get_token():
    # try form-data client_credentials
    for attempt in ("body", "basic"):
        if attempt == "body":
            data = {"grant_type": "client_credentials", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
            r = requests.post(TOKEN_URL, data=data, timeout=30)
        else:
            r = requests.post(TOKEN_URL, data={"grant_type": "client_credentials"}, auth=(CLIENT_ID, CLIENT_SECRET), timeout=30)
        print(f"  token attempt [{attempt}] -> HTTP {r.status_code}: {r.text[:200]}")
        if r.ok:
            return r.json().get("access_token")
    return None

tok = get_token()
if not tok:
    sys.exit("No token obtained.")
print("\nTOKEN OK (len", len(tok), ")\n")

H = {"Authorization": f"Bearer {tok}"}
candidates = [
    "/accounts", "/account", "/channels", "/subscribers", "/subscribers?perPage=1",
    "/tags", "/flows", "/sequences", "/v1/subscribers", "/v2/subscribers",
    "/v1/channels", "/v1/tags", "/swagger.json", "/swagger", "/me",
]
for path in candidates:
    try:
        r = requests.get(API + path, headers=H, timeout=20)
        body = r.text[:220].replace("\n", " ")
        print(f"GET {path:28} -> {r.status_code}  {body}")
    except Exception as e:
        print(f"GET {path:28} -> ERR {e}")
