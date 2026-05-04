"""
Fetches Instagram insights for all published carousels and prints a report.

Usage:
  set INSTAGRAM_ACCESS_TOKEN=<your_token>
  python fetch_analytics.py
"""

import json
import os
import sys
import io
import requests
from datetime import datetime, timezone, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
if not ACCESS_TOKEN:
    sys.exit("Set INSTAGRAM_ACCESS_TOKEN environment variable first.")

GRAPH_BASE = "https://graph.facebook.com/v21.0"
MOSCOW = timezone(timedelta(hours=3))

METRICS = ["likes", "comments", "shares", "saved", "reach", "impressions", "total_interactions"]


def get_insights(media_id):
    r = requests.get(
        f"{GRAPH_BASE}/{media_id}/insights",
        params={"metric": ",".join(METRICS), "access_token": ACCESS_TOKEN},
        timeout=30,
    )
    if not r.ok:
        return None, r.text
    data = {item["name"]: item["values"][0]["value"] for item in r.json().get("data", [])}
    return data, None


def get_media_info(media_id):
    r = requests.get(
        f"{GRAPH_BASE}/{media_id}",
        params={"fields": "like_count,comments_count,timestamp", "access_token": ACCESS_TOKEN},
        timeout=30,
    )
    if not r.ok:
        return None
    return r.json()


with open("schedule.json", encoding="utf-8") as f:
    schedule = json.load(f)

published = [e for e in schedule if e.get("status") == "published" and e.get("media_id")]

print(f"\n{'='*70}")
print(f"  АНАЛИТИКА INSTAGRAM — {datetime.now(MOSCOW).strftime('%d.%m.%Y %H:%M')} МСК")
print(f"{'='*70}")
print(f"  Опубликовано каруселей: {len(published)}\n")

totals = {m: 0 for m in METRICS}
rows = []

for entry in published:
    media_id = entry["media_id"]
    pub_at = entry.get("published_at", "")
    if pub_at:
        dt = datetime.fromisoformat(pub_at)
        pub_str = dt.strftime("%d.%m %H:%M")
    else:
        pub_str = entry["date"]

    insights, err = get_insights(media_id)
    if err:
        print(f"  WARN id={entry['id']} media_id={media_id}: {err[:120]}")
        continue

    rows.append((entry, pub_str, insights))
    for m in METRICS:
        totals[m] += insights.get(m, 0)

# Print table
header = f"{'#':>3}  {'Дата':^11}  {'Слайды':^6}  {'Тема (серия)':^22}  {'Охват':>7}  {'Показы':>7}  {'Сохр.':>6}  {'Лайки':>6}  {'Ком.':>5}  {'Репост':>6}"
print(header)
print("-" * len(header))

for entry, pub_str, ins in rows:
    topic = entry["folder"].replace("series-", "").replace("-", " ").strip()[:22]
    print(
        f"{entry['id']:>3}  {pub_str:^11}  {entry['slides_count']:^6}  {topic:<22}  "
        f"{ins.get('reach', 0):>7,}  {ins.get('impressions', 0):>7,}  "
        f"{ins.get('saved', 0):>6,}  {ins.get('likes', 0):>6,}  "
        f"{ins.get('comments', 0):>5,}  {ins.get('shares', 0):>6,}"
    )

if rows:
    print("-" * len(header))
    print(
        f"{'ИТОГО':>3}  {'':^11}  {'':^6}  {'':^22}  "
        f"{totals['reach']:>7,}  {totals['impressions']:>7,}  "
        f"{totals['saved']:>6,}  {totals['likes']:>6,}  "
        f"{totals['comments']:>5,}  {totals['shares']:>6,}"
    )

    print(f"\n  Engagement rate (лайки+сохр.+ком. / охват): ", end="")
    eng = totals["likes"] + totals["saved"] + totals["comments"]
    rate = eng / totals["reach"] * 100 if totals["reach"] else 0
    print(f"{rate:.2f}%")

    # Best carousel by saves
    best_saves = max(rows, key=lambda x: x[2].get("saved", 0))
    print(f"  Лучшая по сохранениям: id={best_saves[0]['id']} ({best_saves[1]}) — {best_saves[2].get('saved', 0)} сохр.")

    best_reach = max(rows, key=lambda x: x[2].get("reach", 0))
    print(f"  Лучшая по охвату:      id={best_reach[0]['id']} ({best_reach[1]}) — {best_reach[2].get('reach', 0):,} чел.")

print(f"\n{'='*70}\n")
