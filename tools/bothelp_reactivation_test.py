import sys,io,json,requests
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
creds={}
with open(r"C:\Users\listo\OneDrive\Desktop\bothelp.txt",encoding="utf-8") as f:
    for line in f:
        if ":" in line and ("ID" in line or "Secret" in line):
            k,v=line.split(":",1); creds[k.strip().lower()]=v.strip()
tok=requests.post("https://oauth.bothelp.io/oauth2/token",data={"grant_type":"client_credentials","client_id":creds["id"],"client_secret":creds["secret"]},timeout=30).json()["access_token"]
H={"Authorization":f"Bearer {tok}"}; API="https://api.bothelp.io"

GAME_URL="https://app.listoshenkov.ru/?section=game_iron"
text=(
"Привет. Меня тут давно не было, исправляюсь.\n\n"
"Я собрал всё полезное в одно приложение. И там есть штука, которую открывают чаще всего - игра «Враги и друзья железа». "
"Пара минут, а ты увидишь, что тихонько крадёт у тебя энергию. И что её возвращает.\n\n"
f"Пройти игру: {GAME_URL}\n\n"
"Зайдёт - там же бесплатные разборы и протоколы. По анализам, по щитовидке, да много по чему. Выбери, что про тебя.\n\n"
"На днях покажу кое-что новое. Не пропадай."
)
sid=1849
body=[{"content":text}]
for ct in ("application/vnd.api+json","application/json"):
    h=dict(H); h["Content-Type"]=ct
    r=requests.post(f"{API}/v1/subscribers/{sid}/messages",headers=h,data=json.dumps(body),timeout=30)
    print(f"POST -> {r.status_code}: {r.text[:200]}")
    if r.ok: break
