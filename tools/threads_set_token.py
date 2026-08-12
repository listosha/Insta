#!/usr/bin/env python3
"""
Кладёт готовый токен Threads в секреты GitHub, минуя OAuth.

Зачем: в дашборде Meta есть «Генератор маркеров пользователя» - он выдаёт
долгосрочный токен для тестировщика Threads в один клик. Это проще, чем OAuth-флоу
(который упирается то в запрет http, то в список разрешённых redirect-адресов).

Как пользоваться:
  1. developers.facebook.com -> приложение -> Threads API -> «Генератор маркеров
     пользователя» -> «Сгенерировать маркер доступа» напротив своего аккаунта.
  2. Вставить значение в C:\\Users\\listo\\publisher\\sync\\.env строкой:
        THREADS_ACCESS_TOKEN=IGAA...
  3. python tools/threads_set_token.py

Что делает скрипт:
  - проверяет токен запросом /me (кто это и сколько живёт),
  - забирает оттуда же Threads user id,
  - шифрует и кладёт THREADS_ACCESS_TOKEN и THREADS_USER_ID в секреты
    репозитория listosha/Insta,
  - предлагает вычистить токен из .env, чтобы он не лежал на диске лишнего.

Токен нигде не печатается.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ENV_PATH = os.path.join(os.path.expanduser("~"), "publisher", "sync", ".env")
GH_REPO = "listosha/Insta"
ME_URL = "https://graph.threads.net/v1.0/me"
DEBUG_URL = "https://graph.threads.net/debug_token"


def read_env(key):
    if os.environ.get(key):
        return os.environ[key].strip()
    if not os.path.exists(ENV_PATH):
        return ""
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith(key + "="):
                return line.partition("=")[2].strip().strip("\"'")
    return ""


def http_get(url, params):
    with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def github_token():
    tok = read_env("GITHUB_TOKEN")
    if tok:
        return tok
    import re
    import subprocess
    try:
        url = subprocess.run(
            ["git", "-C", os.path.join(os.path.expanduser("~"), "publisher"),
             "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, timeout=10).stdout
        m = re.search(r"(gh[ps]_[A-Za-z0-9]+)", url)
        return m.group(1) if m else ""
    except Exception:  # noqa: BLE001
        return ""


def gh_api(method, path, token, payload=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GH_REPO}{path}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        method=method,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8")
        return r.status, (json.loads(body) if body.strip() else {})


def save_to_github(secrets):
    from base64 import b64encode
    from nacl import encoding, public

    token = github_token()
    if not token:
        print("Токен GitHub не найден - секреты не записаны.")
        return False
    _, key = gh_api("GET", "/actions/secrets/public-key", token)
    box = public.SealedBox(public.PublicKey(key["key"].encode("utf-8"), encoding.Base64Encoder()))
    ok = True
    for name, value in secrets.items():
        enc = b64encode(box.encrypt(value.encode("utf-8"))).decode("utf-8")
        try:
            status, _ = gh_api("PUT", f"/actions/secrets/{name}", token,
                               {"encrypted_value": enc, "key_id": key["key_id"]})
            print(f"  {name}: записан ({status})")
        except Exception as e:  # noqa: BLE001
            print(f"  {name}: НЕ записан - {e}")
            ok = False
    return ok


def scrub_env():
    """Убирает значение токена из .env, оставляя пустой ключ."""
    if not os.path.exists(ENV_PATH):
        return
    out = []
    changed = False
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("THREADS_ACCESS_TOKEN=") and line.strip() != "THREADS_ACCESS_TOKEN=":
                out.append("THREADS_ACCESS_TOKEN=\n")
                changed = True
            else:
                out.append(line)
    if changed:
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.writelines(out)
        print("Значение токена из .env вычищено (ключ остался пустым).")


def main():
    token = read_env("THREADS_ACCESS_TOKEN")
    if not token:
        print("В .env нет THREADS_ACCESS_TOKEN.")
        print(f"Впиши туда токен из генератора маркеров и запусти снова: {ENV_PATH}")
        sys.exit(1)

    try:
        me = http_get(ME_URL, {"fields": "id,username", "access_token": token})
    except Exception as e:  # noqa: BLE001
        print(f"Токен не принят Threads: {e}")
        print("Проверь, что скопирован целиком и что это маркер для аккаунта Threads.")
        sys.exit(1)

    print(f"Токен рабочий. Аккаунт: @{me.get('username')}, id {me.get('id')}")

    try:
        info = http_get(DEBUG_URL, {"input_token": token, "access_token": token})
        data = info.get("data", {})
        exp = data.get("expires_at")
        if exp:
            from datetime import datetime, timezone
            left = (datetime.fromtimestamp(exp, timezone.utc) - datetime.now(timezone.utc)).days
            print(f"Живёт ещё примерно {left} дней.")
    except Exception:  # noqa: BLE001
        pass

    print(f"\nЗаписываю секреты в {GH_REPO}:")
    if save_to_github({"THREADS_ACCESS_TOKEN": token, "THREADS_USER_ID": str(me.get("id"))}):
        print()
        scrub_env()
        print("\nГотово. Дальше: завести THREADS_REFRESH_PAT и включить расписание")
        print("в .github/workflows/refresh-threads-token.yml, иначе токен умрёт через 60 дней.")


if __name__ == "__main__":
    main()
