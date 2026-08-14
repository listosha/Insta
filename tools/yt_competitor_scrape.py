"""
Конкурент-разведка по YouTube через официальный YouTube Data API v3.

В отличие от Instagram, YouTube отдаёт РЕАЛЬНЫЕ просмотры публично. По каждому каналу
достаём топ-видео по просмотрам + лайки/комменты + длительность (Shorts vs длинное),
выгружаем заголовки для разбора структуры.

Ключ (бесплатный, ~2 мин): Google Cloud Console → новый проект → включить
«YouTube Data API v3» → Credentials → API key. НЕ коммитить:
  переменная окружения YOUTUBE_API_KEY, либо файл вне репо
  (C:\\Users\\listo\\Desktop\\insta_tokens.txt) c ключом YOUTUBE_API_KEY=...

Запуск:
  python tools/yt_competitor_scrape.py                       # дефолтный список
  python tools/yt_competitor_scrape.py @DrEricBergDC UCH8OTOBqGHGgEg94lHD3wOA "Максим Кузнецов"
  python tools/yt_competitor_scrape.py --top 15

Принимает: @handle, channelId (UC...24 симв), или просто имя (тогда ищем по названию).
Вывод: competitors-youtube-data-<дата>.json + .md (топ-N с метриками).
"""

import os
import sys
import io
import json
import argparse
import re
import requests
from datetime import datetime, timezone, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DEFAULT_TOKENS_FILE = os.environ.get(
    "INSTA_TOKENS_FILE",
    os.path.join(os.path.expanduser("~"), "Desktop", "insta_tokens.txt"),
)
API = "https://www.googleapis.com/youtube/v3"
MOSCOW = timezone(timedelta(hours=3))

# Релевантные нам каналы (питание / БАД-добавки / гормоны / ЖКТ / метаболизм).
# Где знаю channelId — ставлю его (надёжнее поиска по имени).
DEFAULT_CHANNELS = [
    "UCH8OTOBqGHGgEg94lHD3wOA",   # Борис Цацулин / CMT — научный подход (добавки!) ★
    "Максим Кузнецов эндокринолог",  # гормоны простым языком
    "Алексей Головенко гастроэнтеролог",  # ЖКТ, мифы
    "UC70a-puDtzzqzVlrEmBAIew",   # Инна Кононенко, диетолог-нутрициолог
    "Алексей Ковальков диетолог",
    "@DrEricBergDC",              # Dr. Eric Berg, 14.5M — кето/голодание/ЖКТ ★ референс
    "Thomas DeLauer",            # метаболизм/гормоны/голодание
]


def load_creds():
    """Собирает креды из env + файла вне репо. Ключи приводим к верхнему регистру."""
    keys = ["YOUTUBE_API_KEY", "YOUTUBE_ACCESS_TOKEN", "GOOGLE_ACCESS_TOKEN",
            "YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN",
            "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"]
    creds = {k: os.environ[k] for k in keys if os.environ.get(k)}
    if os.path.exists(DEFAULT_TOKENS_FILE):
        with open(DEFAULT_TOKENS_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                creds.setdefault(k.strip().upper(), v.strip().strip('"').strip("'"))
    return creds


def resolve_auth(creds):
    """Возвращает ('bearer', token) | ('key', api_key). OAuth от публикации тоже годится для чтения."""
    tok = creds.get("YOUTUBE_ACCESS_TOKEN") or creds.get("GOOGLE_ACCESS_TOKEN")
    if tok:
        return ("bearer", tok), "готовый access-token"
    cid = creds.get("YT_CLIENT_ID") or creds.get("GOOGLE_CLIENT_ID")
    csec = creds.get("YT_CLIENT_SECRET") or creds.get("GOOGLE_CLIENT_SECRET")
    rt = creds.get("YT_REFRESH_TOKEN") or creds.get("GOOGLE_REFRESH_TOKEN")
    if cid and csec and rt:
        r = requests.post("https://oauth2.googleapis.com/token",
                          data={"client_id": cid, "client_secret": csec,
                                "refresh_token": rt, "grant_type": "refresh_token"}, timeout=60)
        if not r.ok:
            sys.exit(f"OAuth refresh не удался: {r.status_code}: {r.text[:300]}")
        return ("bearer", r.json()["access_token"]), "обновлён через refresh_token"
    if creds.get("YOUTUBE_API_KEY"):
        return ("key", creds["YOUTUBE_API_KEY"]), "API-ключ"
    sys.exit("Нет кредов YouTube. Положи в "
             f"{DEFAULT_TOKENS_FILE} одно из:\n"
             "  YOUTUBE_API_KEY=...                (простой ключ для чтения), либо\n"
             "  YOUTUBE_ACCESS_TOKEN=...           (готовый OAuth access-token от публикации), либо\n"
             "  YT_CLIENT_ID=... / YT_CLIENT_SECRET=... / YT_REFRESH_TOKEN=...  (обновится сам)")


def api_get(path, params, auth):
    kind, val = auth
    headers = {}
    if kind == "bearer":
        headers["Authorization"] = f"Bearer {val}"
    else:
        params = {**params, "key": val}
    r = requests.get(f"{API}/{path}", params=params, headers=headers, timeout=60)
    if not r.ok:
        return None, f"{r.status_code}: {r.text[:300]}"
    return r.json(), None


def resolve_channel(ident, auth):
    """ident → (channelId, snippet, statistics)."""
    if re.fullmatch(r"UC[\w-]{22}", ident):
        data, err = api_get("channels", {"part": "snippet,statistics", "id": ident}, auth)
    elif ident.startswith("@"):
        data, err = api_get("channels", {"part": "snippet,statistics", "forHandle": ident}, auth)
    else:
        s, err = api_get("search", {"part": "snippet", "q": ident, "type": "channel", "maxResults": 1}, auth)
        if err:
            return None, err
        items = s.get("items", [])
        if not items:
            return None, "канал не найден по имени"
        cid = items[0]["snippet"]["channelId"]
        data, err = api_get("channels", {"part": "snippet,statistics", "id": cid}, auth)
    if err:
        return None, err
    items = data.get("items", [])
    if not items:
        return None, "канал не найден"
    return items[0], None


def iso_to_seconds(dur):
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", dur or "")
    if not m:
        return None
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def top_videos(channel_id, top, auth):
    """Топ-видео канала по просмотрам + их статистика."""
    s, err = api_get("search", {"part": "id", "channelId": channel_id, "order": "viewCount",
                                 "type": "video", "maxResults": min(50, max(top * 2, top))}, auth)
    if err:
        return None, err
    ids = [it["id"]["videoId"] for it in s.get("items", []) if it.get("id", {}).get("videoId")]
    if not ids:
        return [], None
    v, err = api_get("videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(ids[:50])}, auth)
    if err:
        return None, err
    out = []
    for it in v.get("items", []):
        st = it.get("statistics", {})
        secs = iso_to_seconds(it.get("contentDetails", {}).get("duration"))
        out.append({
            "videoId": it["id"],
            "title": it["snippet"]["title"],
            "publishedAt": it["snippet"]["publishedAt"][:10],
            "views": int(st.get("viewCount", 0)),
            "likes": int(st.get("likeCount", 0)) if "likeCount" in st else None,
            "comments": int(st.get("commentCount", 0)) if "commentCount" in st else None,
            "duration_sec": secs,
            "is_short": (secs is not None and secs <= 65),
            "url": f"https://youtu.be/{it['id']}",
        })
    out.sort(key=lambda x: x["views"], reverse=True)
    return out[:top], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("channels", nargs="*", default=None)
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    auth, src = resolve_auth(load_creds())
    print(f"  Авторизация: {src}")
    channels = args.channels if args.channels else DEFAULT_CHANNELS
    stamp = datetime.now(MOSCOW).strftime("%Y-%m-%d")
    results = {}

    print(f"\n{'='*70}\n  YOUTUBE КОНКУРЕНТ-РАЗВЕДКА — {stamp}\n{'='*70}")
    print("  YouTube отдаёт реальные просмотры — ранжируем по ним.\n")

    for ident in channels:
        print(f"  → {ident} …", end=" ")
        ch, err = resolve_channel(ident, auth)
        if err:
            print(f"ОШИБКА: {err}")
            results[ident] = {"error": err}
            continue
        cid = ch["id"]
        stats = ch.get("statistics", {})
        vids, err = top_videos(cid, args.top, auth)
        if err:
            print(f"ОШИБКА видео: {err}")
            results[ident] = {"error": err}
            continue
        title = ch["snippet"]["title"]
        subs = int(stats.get("subscriberCount", 0)) if "subscriberCount" in stats else None
        results[ident] = {"channel": title, "channelId": cid, "subscribers": subs,
                          "total_views": int(stats.get("viewCount", 0)) if "viewCount" in stats else None,
                          "video_count": int(stats.get("videoCount", 0)) if "videoCount" in stats else None,
                          "top_videos": vids}
        print(f"{title}: подписчиков {subs:,}, видео в топе: {len(vids)}" if subs else f"{title}: {len(vids)} видео")

    json_path = f"competitors-youtube-data-{stamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    md_path = f"competitors-youtube-data-{stamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Топ-видео конкурентов на YouTube — {stamp}\n\n")
        f.write("> Ранжирование по реальным просмотрам (YouTube Data API). "
                "S = Shorts (≤65 сек), V = длинное видео.\n\n")
        for ident, r in results.items():
            if r.get("error"):
                f.write(f"## {ident}\n\n⚠️ {r['error']}\n\n")
                continue
            subs = r.get("subscribers")
            f.write(f"## {r['channel']} — {subs:,} подписчиков\n\n" if subs else f"## {r['channel']}\n\n")
            f.write("| # | Тип | Просмотры | Лайки | Комм. | Дата | Заголовок | Ссылка |\n")
            f.write("|--:|:--:|--:|--:|--:|---|---|---|\n")
            for i, vd in enumerate(r["top_videos"], 1):
                t = "S" if vd["is_short"] else "V"
                lk = f"{vd['likes']:,}" if vd["likes"] is not None else "—"
                cm = f"{vd['comments']:,}" if vd["comments"] is not None else "—"
                title = vd["title"].replace("|", "/")
                f.write(f"| {i} | {t} | {vd['views']:,} | {lk} | {cm} | {vd['publishedAt']} | "
                        f"{title} | [▶]({vd['url']}) |\n")
            f.write("\n")

    print(f"\n  Сохранено: {json_path}  +  {md_path}\n{'='*70}\n")


if __name__ == "__main__":
    main()
