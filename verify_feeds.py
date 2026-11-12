#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""境外中继：从我们站点拉 feed 清单 → 并发体检 → 写 results.json。"""
import concurrent.futures as cf
import json
import os
import time
import urllib.request
import xml.etree.ElementTree as ET

FEEDS_URL = os.environ.get(
    "FEEDS_URL", "https://huanjing-intel.com/relay/a85dbd8e68a23ad21e139bf1.json")
OUT = "results.json"
UA = "Mozilla/5.0 (compatible; HuanjingIntelRelay/1.0; +https://huanjing-intel.com)"


def check(item):
    url = item.get("url")
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.4"})
        with urllib.request.urlopen(req, timeout=12) as r:
            raw = r.read(600_000)
        root = ET.fromstring(raw)
        items = []
        for el in root.iter():
            if el.tag.split("}")[-1].lower() not in ("item", "entry"):
                continue
            t = l = p = ""
            for ch in el:
                ct = ch.tag.split("}")[-1].lower()
                v = (ch.text or "").strip()
                if ct == "title" and not t:
                    t = v[:200]
                elif ct == "link" and not l:
                    l = (v or ch.attrib.get("href", ""))[:500]
                elif ct in ("pubdate", "published", "updated") and not p:
                    p = v
            if t and l:
                items.append({"title": t, "link": l, "published": p})
        if not items:
            return {"id": item.get("id"), "url": url, "status": "empty"}
        return {"id": item.get("id"), "url": url, "status": "ok",
                "count": len(items), "sample": items[:5]}
    except Exception as e:
        return {"id": item.get("id"), "url": url, "status": "error",
                "err": type(e).__name__}


def main():
    with urllib.request.urlopen(urllib.request.Request(FEEDS_URL, headers={"User-Agent": UA}),
                                timeout=60) as r:
        feeds = json.loads(r.read().decode("utf-8"))
    print("feeds:", len(feeds))
    out = []
    with cf.ThreadPoolExecutor(max_workers=32) as ex:
        for i, res in enumerate(ex.map(check, feeds), 1):
            out.append(res)
            if i % 100 == 0:
                print("  %d/%d ok=%d" % (i, len(feeds), sum(1 for x in out if x["status"] == "ok")))
    ok = sum(1 for x in out if x["status"] == "ok")
    json.dump({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "total": len(feeds), "ok": ok, "results": out},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print("done ok=%d/%d" % (ok, len(feeds)))


if __name__ == "__main__":
    main()
