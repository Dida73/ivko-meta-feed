#!/usr/bin/env python3
"""Само четене: гледа публичния код на страници от сайта и показва откъде идва кодът за Meta."""
import re, urllib.request, json
UA = "Mozilla/5.0 (compatible; IvkoScan/1.0)"
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60).read().decode("utf-8", "replace")
home = get("https://mebeliivko.bg/")
prods = json.loads(get("https://mebeliivko.bg/wp-json/wc/store/v1/products?per_page=1"))
pages = {"начална": home, "продукт": get(prods[0]["permalink"])}
for name, h in pages.items():
    print("=====", name, len(h), "байта")
    print("fbq( извиквания:", len(re.findall(r"fbq\(", h)))
    print("fbevents.js:", re.findall(r"[^\"'\s]*fbevents[^\"'\s]*", h)[:5])
    print("pixel id-та:", sorted(set(re.findall(r"\b(\d{15,16})\b", " ".join(re.findall(r"fbq\('init'[^)]*\)|fbq\(\"init\"[^)]*\)|facebook\.com/tr\?id=\d+", h))))))
    print("fbq init редове:", re.findall(r"fbq\(['\"]init['\"][^;]{0,120}", h)[:5])
    print("приставки, зареждащи се (wp-content/plugins):")
    for p in sorted(set(re.findall(r"wp-content/plugins/([a-z0-9\-_]+)/", h))):
        print("  ", p)
    for m in re.finditer(r"(?i)(facebook|fbq|meta-pixel|capi|conversions)", h):
        pass
    ctx = [h[max(0, m.start()-80):m.end()+80].replace("\n", " ") for m in re.finditer(r"fbq\(['\"]track['\"]", h)]
    print("track извиквания:", ctx[:6])
