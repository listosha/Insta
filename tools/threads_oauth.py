#!/usr/bin/env python3
"""
Одноразовый OAuth-помощник для Threads API.

Зачем: получить долгоживущий access_token (60 дней) и Threads user id, чтобы
положить их в GitHub Secrets репозитория listosha/Insta. Дальше токен должен
продлевать воркфлоу refresh-threads-token.yml - но его расписание закомментировано,
и пока оно так, токен снова умрёт через 60 дней (ровно это и случилось: секрет
обновляли 31.05.2026, канал встал 30.06, токен истёк около 30.07).

Запускать ЛОКАЛЬНО, один раз. Откроется браузер с экраном авторизации Threads,
после «Разрешить» редирект на https://localhost:8086/ поймает код и обменяет его
на токены, а скрипт сам положит их в секреты GitHub.

Почему https: Threads не пускает авторизацию с незащищённой страницы, попытка с
http:// падает с «Небезопасный вход заблокирован» (error_code 1349187). Скрипт
поднимает локальный HTTPS с самоподписанным сертификатом (создаётся сам при
первом запуске, лежит в publisher/sync/certs, каталог в gitignore). Браузер
один раз предупредит про сертификат - это ожидаемо, надо согласиться перейти.

Подготовка:
  1. В приложении Meta (том же, что для Instagram) должен быть подключён
     use-case Threads API с правами threads_basic и threads_content_publish.
  2. В настройках Threads API -> Redirect Callback URLs добавить РОВНО:
        https://localhost:8086/
  3. Ключи приложения положить в C:\\Users\\listo\\publisher\\sync\\.env:
        THREADS_APP_ID=...        <- App settings -> Basic -> Threads App ID
        THREADS_APP_SECRET=...    <- там же Threads App Secret
     (НЕ обычные App ID и App Secret сверху той же страницы.)
  4. Запустить: python tools/threads_oauth.py

Флаги:
  --check      только проверка: ключи, свободен ли порт, ссылка авторизации
  --no-github  не писать секреты, просто напечатать значения

Скоупы: threads_basic (кто я) + threads_content_publish (публиковать посты и
ответы). Ответ-с-ссылкой публикуется тем же скоупом, отдельного права не нужно.

По умолчанию токен в консоль не печатается: он шифруется и уходит прямо в
секреты THREADS_ACCESS_TOKEN и THREADS_USER_ID репозитория listosha/Insta.
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

# Консоль Windows часто в cp1251 и падает на не-кириллических символах.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

def load_env_file():
    """Подхватываем ключи из publisher/sync/.env - он в gitignore и там же лежат
    остальные секреты проекта. Переменные окружения, если заданы, важнее файла."""
    path = os.path.join(os.path.expanduser("~"), "publisher", "sync", ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("\"'")
            if key.startswith("THREADS_") and value and not os.environ.get(key):
                os.environ[key] = value


load_env_file()

APP_ID = os.environ.get("THREADS_APP_ID", "").strip()
APP_SECRET = os.environ.get("THREADS_APP_SECRET", "").strip()
# Threads не пускает авторизацию с незащищённой страницы: попытка с http:// падает
# с «Небезопасный вход заблокирован» (error_code 1349187). Поэтому поднимаем локальный
# HTTPS с самоподписанным сертификатом - браузер один раз предупредит, это нормально.
REDIRECT_URI = "https://localhost:8086/"
SCOPES = "threads_basic,threads_content_publish"
PORT = 8086
CERT_DIR = os.path.join(os.path.expanduser("~"), "publisher", "sync", "certs")
CERT_FILE = os.path.join(CERT_DIR, "localhost-cert.pem")
KEY_FILE = os.path.join(CERT_DIR, "localhost-key.pem")

AUTH_URL = "https://threads.net/oauth/authorize"
TOKEN_URL = "https://graph.threads.net/oauth/access_token"
LONG_URL = "https://graph.threads.net/access_token"
ME_URL = "https://graph.threads.net/v1.0/me"

GH_REPO = "listosha/Insta"

result = {}


def ensure_cert():
    """Самоподписанный сертификат для localhost. Генерится один раз и переиспользуется."""
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return
    from datetime import datetime, timedelta, timezone
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    os.makedirs(CERT_DIR, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1")),
        ]), critical=False)
        .sign(key, hashes.SHA256())
    )
    with open(KEY_FILE, "wb") as f:
        f.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption()))
    with open(CERT_FILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"Сертификат для localhost создан: {CERT_DIR}")


def github_token():
    """Токен для записи секретов: сначала GITHUB_TOKEN из окружения или .env,
    иначе достаём из адреса origin репозитория publisher (он там с токеном)."""
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        return tok
    env_path = os.path.join(os.path.expanduser("~"), "publisher", "sync", ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("GITHUB_TOKEN="):
                    return line.partition("=")[2].strip().strip("\"'")
    import subprocess
    try:
        url = subprocess.run(
            ["git", "-C", os.path.join(os.path.expanduser("~"), "publisher"),
             "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, timeout=10).stdout
        import re
        m = re.search(r"(gh[ps]_[A-Za-z0-9]+)", url)
        if m:
            return m.group(1)
    except Exception:  # noqa: BLE001
        pass
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
    """Кладёт секреты в Actions репозитория. Значение шифруется публичным ключом
    репозитория (sealed box), как того требует GitHub - в открытом виде не уходит."""
    from base64 import b64encode
    from nacl import encoding, public

    token = github_token()
    if not token:
        print("Не нашёл токен GitHub - секреты не записаны, значения ниже положи руками.")
        return False

    _, key = gh_api("GET", "/actions/secrets/public-key", token)
    box = public.SealedBox(public.PublicKey(key["key"].encode("utf-8"), encoding.Base64Encoder()))

    ok = True
    for name, value in secrets.items():
        encrypted = b64encode(box.encrypt(value.encode("utf-8"))).decode("utf-8")
        try:
            status, _ = gh_api("PUT", f"/actions/secrets/{name}", token,
                               {"encrypted_value": encrypted, "key_id": key["key_id"]})
            print(f"  {name}: записан в секреты ({status})")
        except Exception as e:  # noqa: BLE001
            print(f"  {name}: НЕ записан - {e}")
            ok = False
    return ok


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
        print("Не нашёл THREADS_APP_ID и THREADS_APP_SECRET.")
        print("Заполни их в C:\\Users\\listo\\publisher\\sync\\.env либо задай переменными окружения.")
        print("Где взять: developers.facebook.com -> приложение -> App settings -> Basic ->")
        print("поля «Threads App ID» и «Threads App Secret» (НЕ обычные App ID и App Secret сверху).")
        sys.exit(1)

    print(f"client_id, который уйдёт в Threads: {APP_ID}")
    print("Сверь его с полем «Threads App ID» в App settings -> Basic.\n")

    if "--check" in sys.argv:
        # Проверка без браузера: ключи прочитаны, порт свободен, ссылка собрана.
        import socket
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", PORT))
            print(f"Порт {PORT} свободен.")
        except OSError as e:
            print(f"Порт {PORT} занят ({e}) - закрой прошлый запуск скрипта.")
        finally:
            s.close()
        print("\nСсылка авторизации:")
        print(AUTH_URL + "?" + urllib.parse.urlencode({
            "client_id": APP_ID, "redirect_uri": REDIRECT_URI,
            "scope": SCOPES, "response_type": "code",
        }))
        return

    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": APP_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "response_type": "code",
    })
    ensure_cert()
    print("Открываю браузер. Если не открылся, зайди руками:\n" + url + "\n")
    print("Браузер предупредит про сертификат localhost - это ожидаемо,")
    print("жми «Дополнительно» -> «Перейти на localhost (небезопасно)».\n")
    webbrowser.open(url)

    import ssl
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT_FILE, KEY_FILE)
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        httpd.serve_forever()

    if "error" in result:
        print("ОШИБКА:", result["error"])
        sys.exit(1)

    days = round(int(result.get("expires_in") or 0) / 86400)
    secrets = {
        "THREADS_ACCESS_TOKEN": result["token"],
        "THREADS_USER_ID": str(result["user"].get("id")),
    }

    print("=" * 70)
    print(f"Аккаунт: @{result['user'].get('username')}")
    print(f"Токен живёт: ~{days} дней")
    print()

    saved = False
    if "--no-github" not in sys.argv:
        print(f"Записываю секреты в {GH_REPO}:")
        saved = save_to_github(secrets)
        print()

    if saved:
        print("Токен в секретах, в консоли его не печатаю. Копировать никуда не нужно.")
    else:
        print("Положить руками: github.com/listosha/Insta/settings/secrets/actions")
        for k, v in secrets.items():
            print(f"{k} = {v}")
    print("=" * 70)
    print()
    print("И сразу после этого - чтобы не повторять через 60 дней:")
    print("  1. Завести секрет THREADS_REFRESH_PAT: fine-grained PAT с правом")
    print("     'Secrets: Read and write' на репозиторий listosha/Insta.")
    print("  2. Раскомментировать блок schedule в .github/workflows/refresh-threads-token.yml.")


if __name__ == "__main__":
    main()
