#!/usr/bin/env python3
"""
Одноразовый OAuth-помощник для Threads API.

Зачем: получить долгоживущий access_token (60 дней) и Threads user id, чтобы
положить их в GitHub Secrets репозитория listosha/Insta. Дальше токен должен
продлевать воркфлоу refresh-threads-token.yml - но его расписание закомментировано,
и пока оно так, токен снова умрёт через 60 дней (ровно это и случилось: секрет
обновляли 31.05.2026, канал встал 30.06, токен истёк около 30.07).

Запускать ЛОКАЛЬНО, один раз. Сторонних пакетов не нужно, только Python 3.
Откроется браузер с экраном авторизации Threads, после «Разрешить» редирект на
http://localhost:8086/ поймает код и обменяет его на токены.

Подготовка:
  1. В приложении Meta (том же, что для Instagram) должен быть подключён
     use-case Threads API с правами threads_basic и threads_content_publish.
  2. В настройках Threads API → Redirect Callback URLs добавить РОВНО:
        http://localhost:8086/
  3. Запустить:
        THREADS_APP_ID=...  THREADS_APP_SECRET=...  python tools/threads_oauth.py
     (Windows PowerShell:)
        $env:THREADS_APP_ID="..."; $env:THREADS_APP_SECRET="..."; python tools/threads_oauth.py

Скоупы: threads_basic (кто я) + threads_content_publish (публиковать посты и
ответы). Ответ-с-ссылкой публикуется тем же скоупом, отдельного права не нужно.

Что печатает в конце: THREADS_ACCESS_TOKEN и THREADS_USER_ID - их вручную
положить в Settings → Secrets and variables → Actions репозитория listosha/Insta.
Токен в консоли, в файлы ничего не пишется.
"""
import http.server
import json
import os
import socketserver
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser

APP_ID = os.environ.get("THREADS_APP_ID", "").strip()
APP_SECRET = os.environ.get("THREADS_APP_SECRET", "").strip()
REDIRECT_URI = "http://localhost:8086/"
SCOPES = "threads_basic,threads_content_publish"
PORT = 8086

AUTH_URL = "https://threads.net/oauth/authorize"
TOKEN_URL = "https://graph.threads.net/oauth/access_token"
LONG_URL = "https://graph.threads.net/access_token"
ME_URL = "https://graph.threads.net/v1.0/me"

result = {}


def http_get(url, params):
    full = url + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(full, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def http_post(url, params):
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def exchange(code):
    """Код -> короткий токен -> длинный токен (60 дней) -> user id."""
    short = http_post(TOKEN_URL, {
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": code,
    })
    if "access_token" not in short:
        raise RuntimeError(f"нет короткого токена: {short}")

    long_ = http_get(LONG_URL, {
        "grant_type": "th_exchange_token",
        "client_secret": APP_SECRET,
        "access_token": short["access_token"],
    })
    if "access_token" not in long_:
        raise RuntimeError(f"нет длинного токена: {long_}")

    me = http_get(ME_URL, {"fields": "id,username", "access_token": long_["access_token"]})
    return long_, me


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        def reply(text):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<html><body style='font:16px sans-serif;padding:40px'>{text}</body></html>".encode("utf-8"))

        if "error" in params:
            result["error"] = params.get("error_description", params["error"])[0]
            reply("Отказано в доступе. Можно закрыть вкладку и посмотреть в консоль.")
        elif "code" in params:
            try:
                long_, me = exchange(params["code"][0])
                result["token"] = long_["access_token"]
                result["expires_in"] = long_.get("expires_in")
                result["user"] = me
                reply("Готово. Токен получен, возвращайся в консоль - там всё напечатано.")
            except Exception as e:  # noqa: BLE001
                result["error"] = str(e)
                reply("Обмен кода на токен не удался, подробности в консоли.")
        else:
            reply("Жду редирект с кодом авторизации.")

        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *args):  # тише в консоли
        pass


def main():
    if not APP_ID or not APP_SECRET:
        print("Задай THREADS_APP_ID и THREADS_APP_SECRET в переменных окружения.")
        print("Где взять: developers.facebook.com → приложение → Threads API → Настройки.")
        sys.exit(1)

    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": APP_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "response_type": "code",
    })
    print("Открываю браузер. Если не открылся, зайди руками:\n" + url + "\n")
    webbrowser.open(url)

    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        httpd.serve_forever()

    if "error" in result:
        print("ОШИБКА:", result["error"])
        sys.exit(1)

    days = round(int(result.get("expires_in") or 0) / 86400)
    print("=" * 70)
    print(f"Аккаунт: @{result['user'].get('username')}")
    print(f"Токен живёт: ~{days} дней")
    print()
    print("Положить в GitHub Secrets репозитория listosha/Insta")
    print("(Settings → Secrets and variables → Actions):")
    print()
    print("THREADS_ACCESS_TOKEN =", result["token"])
    print("THREADS_USER_ID      =", result["user"].get("id"))
    print("=" * 70)
    print()
    print("И сразу после этого - чтобы не повторять через 60 дней:")
    print("  1. Завести секрет THREADS_REFRESH_PAT: fine-grained PAT с правом")
    print("     'Secrets: Read and write' на репозиторий listosha/Insta.")
    print("  2. Раскомментировать блок schedule в .github/workflows/refresh-threads-token.yml.")


if __name__ == "__main__":
    main()
