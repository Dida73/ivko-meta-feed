#!/usr/bin/env python3
"""Сглобява чист списък с продукти за Meta каталога от ПУБЛИЧНИЯ API на mebeliivko.bg.

Само четене. Не пише нищо към сайта. Не използва пароли.
Изход: feed.csv (за Meta) и report.json (кратка справка какво е влязло и какво е отпаднало).
"""
import csv
import html
import json
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

SITE = "https://mebeliivko.bg"
API = SITE + "/wp-json/wc/store/v1/products"
BRAND = "Мебели Ивко"
OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
UA = "Mozilla/5.0 (compatible; IvkoFeedBot/1.0; +https://github.com/Dida73/ivko-meta-feed)"

COLUMNS = [
    "id", "title", "description", "availability", "condition", "price",
    "sale_price", "link", "image_link", "additional_image_link", "brand",
    "item_group_id", "product_type",
]


def get_json(url, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                total_pages = int(r.headers.get("X-WP-TotalPages", "1") or 1)
                return json.loads(r.read().decode("utf-8")), total_pages
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Неуспешно четене на {url}: {last}")


def fetch_all(extra=""):
    items, page, total = [], 1, 1
    while page <= total:
        data, total = get_json(f"{API}?per_page=100&page={page}{extra}")
        items.extend(data)
        page += 1
    return items


def clean_text(s, limit=5000):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def money(prices, key):
    raw = prices.get(key)
    if raw in (None, "", "0"):
        return None
    minor = int(prices.get("currency_minor_unit", 2))
    cur = prices.get("currency_code", "EUR")
    val = int(raw) / (10 ** minor)
    return val, cur


def build_rows(products, variations):
    skipped = Counter()
    rows = []

    by_parent = {}
    for v in variations:
        by_parent.setdefault(v.get("parent"), []).append(v)

    def make_row(p, parent=None):
        prices = p.get("prices") or {}
        reg = money(prices, "regular_price") or money(prices, "price")
        cur_price = money(prices, "price")
        if not reg or reg[0] <= 0:
            skipped["цена 0 или липсва"] += 1
            return None
        if not p.get("is_in_stock", False):
            skipped["не е в наличност"] += 1
            return None
        images = p.get("images") or (parent or {}).get("images") or []
        if not images:
            skipped["без снимка"] += 1
            return None
        title = clean_text((parent or p).get("name"), 150)
        if parent and p.get("attributes"):
            attrs = ", ".join(a.get("value") or a.get("name", "") for a in p["attributes"])
            if attrs:
                title = f"{title} - {attrs}"[:150]
        desc = clean_text((parent or p).get("description") or (parent or p).get("short_description")) or title
        cats = (parent or p).get("categories") or []
        row = {
            "id": str(p["id"]),
            "title": title,
            "description": desc,
            "availability": "in stock",
            "condition": "new",
            "price": f"{reg[0]:.2f} {reg[1]}",
            "sale_price": f"{cur_price[0]:.2f} {cur_price[1]}" if cur_price and cur_price[0] < reg[0] else "",
            "link": p.get("permalink") or (parent or {}).get("permalink", ""),
            "image_link": images[0]["src"],
            "additional_image_link": ",".join(i["src"] for i in images[1:10]),
            "brand": BRAND,
            "item_group_id": str(parent["id"]) if parent else "",
            "product_type": " > ".join(c["name"] for c in cats),
        }
        return row

    for p in products:
        ptype = p.get("type")
        if ptype == "variable":
            vs = by_parent.get(p["id"], [])
            if not vs:
                # няма отделни варианти в API – ползваме най-ниската цена на основния продукт
                r = make_row(p)
                if r:
                    rows.append(r)
                continue
            for v in vs:
                r = make_row(v, parent=p)
                if r:
                    rows.append(r)
        elif ptype in ("simple", "external", "grouped"):
            r = make_row(p)
            if r:
                rows.append(r)
        else:
            skipped[f"тип {ptype}"] += 1
    return rows, skipped


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    products = fetch_all()
    try:
        variations = fetch_all("&type=variation")
    except Exception as e:  # noqa: BLE001
        print("Предупреждение: не успях да чета вариантите:", e)
        variations = []
    rows, skipped = build_rows(products, variations)
    if len(rows) < 50:
        # предпазител: не презаписваме добър списък с почти празен
        raise SystemExit(f"Спрях: в списъка влязоха само {len(rows)} реда. Не пиша файла.")

    with open(OUT_DIR / "feed.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    report = {
        "products_read": len(products),
        "variations_read": len(variations),
        "rows_in_feed": len(rows),
        "rows_with_price_zero": sum(1 for r in rows if float(r["price"].split()[0]) <= 0),
        "rows_without_image": sum(1 for r in rows if not r["image_link"]),
        "skipped": dict(skipped),
    }
    (OUT_DIR / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
