"""РАССЫЛКА реактивации по TG-базе. ЗАПУСКАТЬ ТОЛЬКО ПО СИГНАЛУ АЛЕКСЕЯ.
Читает заранее построенный список целей (дедуп по человеку, без Марии/Алексея),
шлёт утверждённый текст порциями с паузами, ведёт лог успехов/ошибок.
"""
import sys,io,json,time,requests
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
creds={}
with open(r"C:\Users\listo\OneDrive\Desktop\bothelp.txt",encoding="utf-8") as f:
    for line in f:
        if ":" in line and ("ID" in line or "Secret" in line):
            k,v=line.split(":",1); creds[k.strip().lower()]=v.strip()

GAME_URL="https://app.listoshenkov.ru/?section=game_iron"
TEXT=(
"Привет. Меня тут давно не было, исправляюсь.\n\n"
"Я собрал всё полезное в одно приложение. И там есть штука, которую открывают чаще всего - игра «Враги и друзья железа». "
"Пара минут, а ты увидишь, что тихонько крадёт у тебя энергию. И что её возвращает.\n\n"
f"Пройти игру: {GAME_URL}\n\n"
"Зайдёт - там же бесплатные разборы и протоколы. По анализам, по щитовидке, да много по чему. Выбери, что про тебя.\n\n"
"На днях покажу кое-что новое. Не пропадай."
)
DRY_RUN = True   # <-- ставим False ТОЛЬКО когда Алексей сказал "го"
BATCH=25; PAUSE=2.0  # порциями по 25 с паузой 2с (анти-спам)

def token():
    return requests.post("https://oauth.bothelp.io/oauth2/token",
        data={"grant_type":"client_credentials","client_id":creds["id"],"client_secret":creds["secret"]},timeout=30).json()["access_token"]

ids=json.load(open(r"C:\Users\listo\Downloads\bothelp_send_targets.json",encoding="utf-8"))
print(f"targets: {len(ids)} | DRY_RUN={DRY_RUN}")
if DRY_RUN:
    print("Сухой прогон. Ничего не отправлено. Поставь DRY_RUN=False по сигналу Алексея."); sys.exit(0)

API="https://api.bothelp.io"; tok=token(); H={"Authorization":f"Bearer {tok}","Content-Type":"application/vnd.api+json"}
ok=err=0; fails=[]
for i,sid in enumerate(ids,1):
    if i%200==0: tok=token(); H["Authorization"]=f"Bearer {tok}"  # refresh token (1h ttl)
    try:
        r=requests.post(f"{API}/v1/subscribers/{sid}/messages",headers=H,data=json.dumps([{"content":TEXT}]),timeout=30)
        if r.ok: ok+=1
        else: err+=1; fails.append((sid,r.status_code,r.text[:80]))
    except Exception as e:
        err+=1; fails.append((sid,"EXC",str(e)[:80]))
    if i%BATCH==0:
        print(f"  {i}/{len(ids)} ok={ok} err={err}"); time.sleep(PAUSE)
print(f"\nDONE. ok={ok} err={err}")
json.dump(fails,open(r"C:\Users\listo\Downloads\bothelp_send_fails.json","w",encoding="utf-8"),ensure_ascii=False)
print("fails saved -> Downloads\bothelp_send_fails.json")
