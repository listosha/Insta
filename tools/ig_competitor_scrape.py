"""
Конкурент-разведка по Instagram через официальный Graph API (business_discovery).

Достаёт по каждому ПУБЛИЧНОМУ Business/Creator-аккаунту список Reels и ранжирует
их по вовлечённости (лайки + комментарии). Для разбора хуков выгружает caption.

ВАЖНО про просмотры: Graph API НЕ отдаёт play/views/reach чужих аккаунтов —
только свои. Поэтому ранжируем по лайкам+комментам как прокси (на дистанции
надёжно коррелирует с просмотрами). Реальные вьюсы — только серый скрейпер (Apify).

Токен (НОВЫЙ НЕ НУЖЕН — тот же, что публикация/аналитика). Берётся в порядке:
  1) переменная окружения INSTAGRAM_ACCESS_TOKEN (или FB_ACCESS_TOKEN при --token-key FB);
  2) файл ВНЕ репо (по умолчанию C:\\Users\\listo\\Desktop\\insta_tokens.txt) с ключами:
        INSTAGRAM_ACCESS_TOKEN=EAA...
        FB_ACCESS_TOKEN=EAA...
     (путь можно переопределить переменной INSTA_TOKENS_FILE)

  python tools/ig_competitor_scrape.py                                     # дефолтный список
  python tools/ig_competitor_scrape.py doctor_komissarova --pages 1        # тест одного
  python tools/ig_competitor_scrape.py --token-key FB doctor_komissarova   # проверить FB-токен
  python tools/ig_competitor_scrape.py --top 15 --pages 6                  # глубже/больше

Вывод: competitors-reels-data-<дата>.json (полные данные) + .md (топ-N с хуками).
"""

import json
import os
import sys
import io
import argparse
import requests
from datetime import datetime, timezone, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DEFAULT_TOKENS_FILE = os.environ.get(
    "INSTA_TOKENS_FILE",
    os.path.join(os.path.expanduser("~"), "Desktop", "insta_tokens.txt"),
)


def load_tokens_file(path):
    """Парсит файл key=value (строки с # игнорируются). Нет файла → {}."""
    tokens = {}
    if not os.path.exists(path):
        return tokens
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            tokens[k.strip().upper()] = v.strip().strip('"').strip("'")
    return tokens


def resolve_token(token_key):
    """token_key: 'INSTAGRAM' | 'FB'. Сначала env, потом файл."""
    env_name = "FB_ACCESS_TOKEN" if token_key == "FB" else "INSTAGRAM_ACCESS_TOKEN"
    tok = os.environ.get(env_name)
    src = f"env {env_name}"
    if not tok:
        tok = load_tokens_file(DEFAULT_TOKENS_FILE).get(env_name)
        src = f"{DEFAULT_TOKENS_FILE} [{env_name}]"
    if not tok:
        sys.exit(f"Токен не найден. Положи {env_name}=... в {DEFAULT_TOKENS_FILE} "
                 f"или задай переменную окружения {env_name}.")
    print(f"  Токен: {src} (…{tok[-6:]})")
    return tok


GRAPH_BASE = "https://graph.facebook.com/v21.0"
IG_USER_ID = "17841403939108726"   # наш аккаунт; business_discovery идёт ОТ него
MOSCOW = timezone(timedelta(hours=3))

# Релевантные нам конкуренты (тема пересекается с продуктами: питание/БАД/гормоны/ЖКТ/меню).
# Прямые RU — первыми; западные — референс по формату.
DEFAULT_TARGETS = [
    "doctor_komissarova",   # диетолог-эндокринолог, эталон тона
    "doctor_zubareva",      # диетолог, ближайшая БАД-модель
    "smart_manya",          # нутрициолог, лёгкий тон
    "glucosegoddess",       # референс по инфографике/монтажу
    "drmarkhyman",          # функциональная медицина
]

# Медиа-поля для каждого ролика. media_product_type отделяет REELS от обычного видео.
MEDIA_FIELDS = "id,caption,media_type,media_product_type,like_count,comments_count,timestamp,permalink"


def fetch_account(username, max_pages, access_token):
    """Тянет профиль + до max_pages страниц медиа через business_discovery."""
    media = []
    profile = {}
    after = None
    for page in range(max_pages):
        media_edge = f"media.limit(50){'' if after is None else f'.after({after})'}{{{MEDIA_FIELDS}}}"
        field = f"business_discovery.username({username}){{followers_count,media_count,{media_edge}}}"
        r = requests.get(
            f"{GRAPH_BASE}/{IG_USER_ID}",
            params={"fields": field, "access_token": access_token},
            timeout=60,
        )
        if not r.ok:
            return None, f"{r.status_code}: {r.text[:300]}"
        bd = r.json().get("business_discovery")
        if not bd:
            return None, f"no business_discovery in response: {r.text[:300]}"
        if not profile:
            profile = {"followers_count": bd.get("followers_count"),
                       "media_count": bd.get("media_count")}
        m = bd.get("media", {})
        media.extend(m.get("data", []))
        after = m.get("paging", {}).get("cursors", {}).get("after")
        if not after or not m.get("paging", {}).get("next"):
            break
    return {"profile": profile, "media": media}, None


def is_reel(item):
    # business_discovery отдаёт media_product_type для свежих медиа; на старых — fallback на VIDEO.
    mpt = item.get("media_product_type")
    if mpt:
        return mpt == "REELS"
    return item.get("media_type") == "VIDEO"


def first_line(caption, n=160):
    if not caption:
        return "(без подписи)"
    line = caption.strip().splitlines()[0]
    return (line[:n] + "…") if len(line) > n else line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*", default=None, help="Instagram usernames (без @)")
    ap.add_argument("--top", type=int, default=10, help="сколько топ-рилсов выводить на аккаунт")
    ap.add_argument("--pages", type=int, default=4, help="страниц медиа на аккаунт (×50 роликов)")
    ap.add_argument("--token-key", choices=["INSTAGRAM", "FB"], default="INSTAGRAM",
                    help="какой токен использовать (по умолчанию INSTAGRAM)")
    args = ap.parse_args()

    targets = args.targets if args.targets else DEFAULT_TARGETS
    stamp = datetime.now(MOSCOW).strftime("%Y-%m-%d")
    results = {}

    print(f"\n{'='*70}\n  КОНКУРЕНТ-РАЗВЕДКА INSTAGRAM — {stamp}\n{'='*70}")
    access_token = resolve_token(args.token_key)
    print("  Ранжируем по (лайки+комменты): API не отдаёт просмотры чужих аккаунтов.\n")

    for username in targets:
        print(f"  → @{username} …", end=" ")
        data, err = fetch_account(username, args.pages, access_token)
        if err:
            print(f"ОШИБКА: {err}")
            results[username] = {"error": err}
            continue
        reels = [m for m in data["media"] if is_reel(m)]
        for m in reels:
            m["engagement"] = (m.get("like_count") or 0) + (m.get("comments_count") or 0)
        reels.sort(key=lambda m: m["engagement"], reverse=True)
        results[username] = {"profile": data["profile"],
                             "total_media_fetched": len(data["media"]),
                             "reels_found": len(reels),
                             "top_reels": reels[:args.top]}
        fc = data["profile"].get("followers_count")
        print(f"подписчиков ~{fc:,}, рилсов в выборке: {len(reels)}" if fc else f"рилсов: {len(reels)}")

    json_path = f"competitors-reels-data-{stamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    md_path = f"competitors-reels-data-{stamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Топ-рилсы конкурентов (по вовлечённости) — {stamp}\n\n")
        f.write("> Ранжирование по (лайки+комменты): Graph API не отдаёт просмотры чужих "
                "аккаунтов. Caption = первая строка (обычно хук).\n\n")
        for username, r in results.items():
            if r.get("error"):
                f.write(f"## @{username}\n\n⚠️ Ошибка: `{r['error']}`\n\n")
                continue
            fc = r["profile"].get("followers_count")
            f.write(f"## @{username} — ~{fc:,} подписчиков\n\n" if fc else f"## @{username}\n\n")
            f.write("| # | Лайки | Комм. | Дата | Хук (1-я строка) | Ссылка |\n")
            f.write("|--:|--:|--:|---|---|---|\n")
            for i, m in enumerate(r["top_reels"], 1):
                d = (m.get("timestamp") or "")[:10]
                hook = first_line(m.get("caption")).replace("|", "/")
                f.write(f"| {i} | {m.get('like_count') or 0:,} | {m.get('comments_count') or 0:,} | "
                        f"{d} | {hook} | [▶]({m.get('permalink','')}) |\n")
            f.write("\n")

    print(f"\n  Сохранено: {json_path}  +  {md_path}\n{'='*70}\n")


if __name__ == "__main__":
    main()
