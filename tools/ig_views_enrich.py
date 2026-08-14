"""
Дообогащает топ-рилсы конкурентов РЕАЛЬНЫМИ просмотрами через Apify.

Graph API не отдаёт просмотры чужих аккаунтов (только лайки/комменты). Apify-актор
`apify/instagram-scraper` парсит публичные reel-страницы и возвращает playCount/videoViewCount.
Берём ТОЛЬКО уже отобранный шорт-лист (топ-N из competitors-reels-data-<date>.json),
чтобы не платить за лишнее.

Стоимость: Apify тарифицирует по результатам — десятки рилсов = центы-доллары за прогон.

Токен Apify (НЕ коммитить): переменная окружения APIFY_TOKEN, либо файл вне репо
(C:\\Users\\listo\\Desktop\\insta_tokens.txt) c ключом APIFY_TOKEN=...

Запуск:
  python tools/ig_views_enrich.py                       # последний competitors-reels-data-*.json
  python tools/ig_views_enrich.py --data competitors-reels-data-2026-06-16.json --top 5
"""

import os
import sys
import io
import glob
import json
import argparse
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DEFAULT_TOKENS_FILE = os.environ.get(
    "INSTA_TOKENS_FILE",
    os.path.join(os.path.expanduser("~"), "Desktop", "insta_tokens.txt"),
)
APIFY_ACTOR = "apify~instagram-scraper"
APIFY_ENDPOINT = f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items"


def get_apify_token():
    tok = os.environ.get("APIFY_TOKEN")
    if tok:
        return tok
    path = DEFAULT_TOKENS_FILE
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip().upper().startswith("APIFY_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit(f"Нет APIFY_TOKEN (env или {DEFAULT_TOKENS_FILE} c APIFY_TOKEN=...).")


def latest_data_file():
    files = sorted(glob.glob("competitors-reels-data-*.json"))
    if not files:
        sys.exit("Не найден competitors-reels-data-*.json — сперва запусти ig_competitor_scrape.py.")
    return files[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None, help="путь к competitors-reels-data-*.json")
    ap.add_argument("--top", type=int, default=10, help="сколько топ-рилсов с аккаунта обогащать")
    args = ap.parse_args()

    token = get_apify_token()
    data_path = args.data or latest_data_file()
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    # Собираем permalink-и шорт-листа
    url_to_ref = {}
    for username, r in data.items():
        if r.get("error"):
            continue
        for m in r.get("top_reels", [])[:args.top]:
            url = m.get("permalink")
            if url:
                url_to_ref[url] = m
    urls = list(url_to_ref)
    if not urls:
        sys.exit("Нет ссылок для обогащения.")
    print(f"  Запрашиваю реальные просмотры по {len(urls)} рилсам через Apify…")

    resp = requests.post(
        APIFY_ENDPOINT,
        params={"token": token},
        json={"directUrls": urls, "resultsType": "posts", "resultsLimit": len(urls),
              "addParentData": False},
        timeout=600,
    )
    if not resp.ok:
        sys.exit(f"Apify error {resp.status_code}: {resp.text[:300]}")
    items = resp.json()

    matched = 0
    for it in items:
        url = it.get("url") or it.get("inputUrl")
        ref = url_to_ref.get(url)
        if not ref and it.get("shortCode"):
            for k, v in url_to_ref.items():
                if it["shortCode"] in k:
                    ref = v
                    break
        if not ref:
            continue
        views = it.get("videoPlayCount") or it.get("videoViewCount") or it.get("playCount")
        ref["views"] = views
        matched += 1

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Обогащено {matched}/{len(urls)} рилсов реальными просмотрами. Записано в {data_path}.")

    # Пересобираем .md с колонкой просмотров
    md_path = data_path.replace(".json", ".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Топ-рилсы конкурентов (+ реальные просмотры из Apify) — {data_path}\n\n")
        for username, r in data.items():
            if r.get("error"):
                f.write(f"## @{username}\n\n⚠️ {r['error'][:120]}\n\n")
                continue
            fc = r["profile"].get("followers_count")
            f.write(f"## @{username} — ~{fc:,} подписчиков\n\n" if fc else f"## @{username}\n\n")
            f.write("| # | Просмотры | Лайки | Комм. | Дата | Хук | Ссылка |\n|--:|--:|--:|--:|---|---|---|\n")
            for i, m in enumerate(r.get("top_reels", [])[:args.top], 1):
                v = m.get("views")
                vs = f"{v:,}" if isinstance(v, int) else "—"
                cap = (m.get("caption") or "").strip().splitlines()
                hook = (cap[0][:120] if cap else "").replace("|", "/")
                f.write(f"| {i} | {vs} | {m.get('like_count') or 0:,} | {m.get('comments_count') or 0:,} | "
                        f"{(m.get('timestamp') or '')[:10]} | {hook} | [▶]({m.get('permalink','')}) |\n")
            f.write("\n")
    print(f"  Обновлён {md_path} (колонка «Просмотры»).")


if __name__ == "__main__":
    main()
