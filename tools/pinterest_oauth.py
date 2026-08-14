#!/usr/bin/env python3
"""
Одноразовый OAuth-помощник для Pinterest API v5.

Зачем: получить ПЕРВЫЙ refresh_token (живёт 60 дней, рефрешится бесконечно) и
access_token (30 дней). Дальше их кладём в GitHub Secrets, а воркфлоу
refresh-pinterest-token.yml продлевает access-токен сам.

Запускать ЛОКАЛЬНО (не в CI) один раз. Нужен только стандартный Python 3 —
сторонних пакетов нет. Откроется браузер с экраном авторизации Pinterest,
после "Allow" редирект на http://localhost:8085/ поймает код и обменяет его
на токены.

Подготовка:
  1. В приложении на developers.pinterest.com/apps в разделе Redirect URIs
     добавить РОВНО:  http://localhost:8085/
  2. Запустить:
        PINTEREST_APP_ID=...  PINTEREST_APP_SECRET=...  python tools/pinterest_oauth.py
     (Windows PowerShell:)
        $env:PINTEREST_APP_ID="..."; $env:PINTEREST_APP_SECRET="..."; python tools/pinterest_oauth.py

Скоупы запрашиваем: boards:read, boards:write, pins:read, pins:write.
boards:read нужен, чтобы потом узнать board_id; boards:write — иначе пин не
создаётся (см. pinterest-analysis-2026-06-01.md, раздел 1).
"""

import base64
import http.server
import json
import os
import sys
import urllib.parse
import urllib.request
import webbrowser

APP_ID = os.environ.get("PINTEREST_APP_ID")
APP_SECRET = os.environ.get("PINTEREST_APP_SECRET")
REDIRECT_URI = "http://localhost:8085/"
SCOPES = "boards:read,boards:write,pins:read,pins:write"
PORT = 8085

if not APP_ID or not APP_SECRET:
    sys.exit(
        "Задай переменные окружения PINTEREST_APP_ID и PINTEREST_APP_SECRET.\n"
        "Их видно в Manage приложения на developers.pinterest.com/apps."
    )

auth_url = "https://www.pinterest.com/oauth/?" + urllib.parse.urlencode({
    "client_id": APP_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": SCOPES,
    "state": "pinterest-oauth-local",
})


def exchange_code_for_tokens(code):
    basic = base64.b64encode(f"{APP_ID}:{APP_SECRET}".encode()).decode()
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(
        "https://api.pinterest.com/v5/oauth/token",
        data=data,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" not in params:
            # Игнорируем посторонние запросы (favicon и т.п.)
            self.send_response(204)
            self.end_headers()
            return

        code = params["code"][0]
        try:
            tokens = exchange_code_for_tokens(code)
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:500]
            self._respond(f"Обмен кода не удался: {e.code}\n{body}")
            print(f"\nОБМЕН НЕ УДАЛСЯ: {e.code}\n{body}", file=sys.stderr)
            self.server.failed = True
            return

        access = tokens.get("access_token", "")
        refresh = tokens.get("refresh_token", "")
        expires = tokens.get("expires_in", "?")
        refresh_expires = tokens.get("refresh_token_expires_in", "?")

        print("\n=== ТОКЕНЫ ПОЛУЧЕНЫ ===")
        print(f"access_token  (живёт {expires}s ≈ 30 дней):\n{access}\n")
        print(f"refresh_token (живёт {refresh_expires}s ≈ 60 дней):\n{refresh}\n")
        print("Положи их в GitHub Secrets:")
        print("  PINTEREST_ACCESS_TOKEN  = access_token")
        print("  PINTEREST_REFRESH_TOKEN = refresh_token")
        print("  PINTEREST_APP_ID        = (твой app id)")
        print("  PINTEREST_APP_SECRET    = (твой app secret)")

        self._respond(
            "Готово! Токены выведены в терминал, где запущен скрипт. "
            "Окно можно закрыть."
        )
        self.server.done = True

    def _respond(self, msg):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(msg.encode("utf-8"))

    def log_message(self, *args):
        pass  # тише в консоли


def main():
    print("Открываю браузер для авторизации Pinterest…")
    print(f"Если не открылось — перейди вручную:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = http.server.HTTPServer(("localhost", PORT), Handler)
    server.done = False
    server.failed = False
    print(f"Жду редирект на {REDIRECT_URI} … (Ctrl+C для отмены)")
    while not server.done and not server.failed:
        server.handle_request()
    sys.exit(1 if server.failed else 0)


if __name__ == "__main__":
    main()
