#!/usr/bin/env python3
"""Само четене: търси в публичния код на сайта следи от Conversions API Gateway (openbridge/capig/AWS) и чужди домейни."""
import re, urllib.request, json
UA = "Mozilla/5.0 (compatible; IvkoScan/1.0)"
def get(u):
    r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60)
    return r.read().decode("utf-8", "replace"), dict(r.headers)
prods = json.loads(get("https://mebeliivko.bg/wp-json/wc/store/v1/products?per_page=1")[0])
pages = {"начална": "https://mebeliivko.bg/", "продукт": prods[0]["permalink"], "количка": "https://mebeliivko.bg/kolichka/"}
for name, u in pages.items():
    try:
        h, hd = get(u)
    except Exception as e:
        print("=====", name, "грешка", e); continue
    print("=====", name, u, len(h), "байта")
    for k in ("openbridge", "capig", "capi-gateway", "amazonaws", "cloudfront", "conversions-api-gateway", "fb_conv_service", "signalsgateway", "pixel_server"):
        print(f"  '{k}':", len(re.findall(k, h, re.I)))
    for m in re.finditer(r"(?i)openbridge|capig|amazonaws|cloudfront", h):
        print("   ...", h[max(0, m.start()-120):m.end()+160].replace("\n", " "))
        break
    hosts = sorted(set(re.findall(r"(?:src|href)=[\"']https?://([^/\"']+)", h)))
    print("  външни домейни:", [x for x in hosts if "mebeliivko.bg" not in x])
    print("  fbq('set' извиквания:", re.findall(r"fbq\(\s*['\"]set['\"][^;]{0,160}", h)[:6])
    print("  fbq('init' извиквания:", re.findall(r"fbq\(\s*['\"]init['\"][^;]{0,160}", h)[:4])
    print("  заглавия:", {k: v for k, v in hd.items() if k.lower() in ("x-cache", "cf-cache-status", "server", "x-powered-by", "cache-control", "via", "x-litespeed-cache")})
