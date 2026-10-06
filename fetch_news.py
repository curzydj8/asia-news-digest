#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
亚洲新闻中文速览 - 每日抓取脚本
抓取 13 家国际媒体 RSS -> 过滤亚洲新闻 -> 翻译成中文 -> 生成 data/YYYY-MM-DD.json
纯标准库，无第三方依赖，适合 cron 每日运行。
"""
import urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as ET
import json, re, os, sys, time, hashlib, html
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
CACHE_FILE = os.path.join(DATA_DIR, ".translate_cache.json")
TZ_SH = timezone(timedelta(hours=8))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

SOURCES = [
    ("CNN", "CNN", "http://rss.cnn.com/rss/edition.rss"),
    ("The New York Times", "纽约时报", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
    ("The Washington Post", "华盛顿邮报", "https://feeds.washingtonpost.com/rss/world"),
    ("The Wall Street Journal", "华尔街日报", "https://feeds.a.dj.com/rss/RSSWorldNews.xml"),
    ("Fox News", "福克斯新闻", "https://moxie.foxnews.com/google-publisher/world.xml"),
    ("NBC News", "NBC新闻", "https://feeds.nbcnews.com/nbcnews/public/world"),
    ("ABC News", "ABC新闻", "https://abcnews.com/abcnews/internationalheadlines"),
    ("CBS News", "CBS新闻", "https://www.cbsnews.com/latest/rss/world"),
    ("NPR", "NPR", "https://feeds.npr.org/1004/rss.xml"),
    ("BBC News", "BBC", "https://feeds.bbci.co.uk/news/world/asia/rss.xml"),
    ("The Guardian", "卫报", "https://www.theguardian.com/world/rss"),
    ("Financial Times", "金融时报", "https://www.ft.com/rss/world"),
    ("Euronews", "欧洲新闻", "https://www.euronews.com/rss?level=theme&name=news"),
]

# 亚洲关键词（标题+摘要命中其一即收录）
ASIA_KW = [
    "china", "chinese", "beijing", "shanghai", "shenzhen", "guangzhou", "wuhan",
    "taiwan", "taipei", "hong kong", "macau", "xinjiang", "tibet", "xi jinping",
    "japan", "japanese", "tokyo", "osaka", "kyoto",
    "korea", "seoul", "pyongyang", "busan", "kim jong",
    "india", "indian", "delhi", "mumbai", "modi", "kolkata", "bangalore",
    "pakistan", "islamabad", "karachi", "bangladesh", "dhaka",
    "vietnam", "hanoi", "ho chi minh", "thailand", "bangkok",
    "philippines", "manila", "indonesia", "jakarta", "bali",
    "malaysia", "kuala lumpur", "singapore", "myanmar", "burma", "yangon",
    "cambodia", "phnom penh", "laos", "mongolia", "ulaanbaatar",
    "nepal", "kathmandu", "sri lanka", "colombo", "bhutan", "maldives",
    "kazakhstan", "uzbekistan", "central asia",
    "asia", "asian", "asean", "apec", "indo-pacific", "pacific",
    "south china sea", "east china sea", "taiwan strait",
    "everest", "himalaya",
]

VIDEO_HINTS = ["/video", "/videos/", "watch:", "| video", "(video)", "video:"]


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def is_video(title, desc, link):
    blob = f"{title} {desc} {link}".lower()
    return any(h in blob for h in VIDEO_HINTS)


def is_asia(title, desc):
    blob = f"{title} {desc}".lower()
    return any(k in blob for k in ASIA_KW)


def find_image(item):
    """按优先级提取图片 URL"""
    ns = {"media": "http://search.yahoo.com/mrss/"}
    for mc in item.findall("media:content", ns):
        t = (mc.get("type") or "") + (mc.get("medium") or "")
        if "video" in t:
            continue
        u = mc.get("url")
        if u:
            return u
    for mt in item.findall("media:thumbnail", ns):
        u = mt.get("url")
        if u:
            return u
    for enc in item.findall("enclosure"):
        t = enc.get("type") or ""
        u = enc.get("url") or ""
        if t.startswith("image") or re.search(r"\.(jpe?g|png|webp)(\?|$)", u, re.I):
            return u
    return ""


def parse_pubdate(s):
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s.strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s.strip()[:25], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def parse_feed(xml_bytes, src_en, src_zh):
    """解析 RSS2.0 / Atom，返回条目列表"""
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        print(f"  [parse fail] {src_en}: {e}", flush=True)
        return items
    tag = root.tag.lower()
    if tag.endswith("rss") or root.find("channel") is not None:
        for it in root.findall("./channel/item"):
            title = strip_html(it.findtext("title") or "")
            desc = strip_html(it.findtext("description") or "")
            link = (it.findtext("link") or "").strip()
            pub = parse_pubdate(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date") or "")
            items.append((title, desc, link, pub, find_image(it)))
    elif tag.endswith("feed"):  # Atom
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for e in root.findall("a:entry", ns):
            title = strip_html(e.findtext("a:title", "", ns))
            desc = strip_html(e.findtext("a:summary", "", ns) or e.findtext("a:content", "", ns))
            link = ""
            for l in e.findall("a:link", ns):
                if l.get("rel", "alternate") == "alternate":
                    link = l.get("href") or ""
                    break
            pub = parse_pubdate(e.findtext("a:updated", "", ns) or e.findtext("a:published", "", ns))
            img = ""
            for l in e.findall("a:link", ns):
                if (l.get("rel") == "enclosure") and (l.get("type") or "").startswith("image"):
                    img = l.get("href") or ""
            items.append((title, desc, link, pub, img))
    out = []
    for title, desc, link, pub, img in items:
        if not title or not link:
            continue
        if is_video(title, desc, link):
            continue
        if not is_asia(title, desc):
            continue
        out.append({
            "id": hashlib.md5(link.encode()).hexdigest()[:12],
            "source_en": src_en, "source_zh": src_zh,
            "title_en": title, "summary_en": desc[:600],
            "url": link, "image": img,
            "published": (pub or datetime.now(timezone.utc)).isoformat(),
        })
    return out


# ---------- 翻译 ----------
def load_cache():
    try:
        return json.load(open(CACHE_FILE, encoding="utf-8"))
    except Exception:
        return {}


def save_cache(c):
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(c, open(CACHE_FILE, "w", encoding="utf-8"), ensure_ascii=False)


def translate_batch(texts):
    """Google 非官方接口批量翻译 en->zh-CN，带缓存"""
    cache = load_cache()
    results, todo, todo_idx = {}, [], []
    for i, t in enumerate(texts):
        if not t.strip():
            results[i] = ""
            continue
        key = hashlib.md5(("en|zh|" + t).encode()).hexdigest()
        if key in cache:
            results[i] = cache[key]
        else:
            todo.append(t)
            todo_idx.append((i, key))
    # 分批请求，每批最多 8 条
    for b in range(0, len(todo), 8):
        chunk = todo[b:b + 8]
        params = [("client", "gtx"), ("sl", "en"), ("tl", "zh-CN"), ("dt", "t")]
        qs = urllib.parse.urlencode(params) + "".join("&" + urllib.parse.urlencode({"q": t}) for t in chunk)
        url = "https://translate.googleapis.com/translate_a/single?" + qs
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers=UA)
                d = json.load(urllib.request.urlopen(req, timeout=20))
                # d[0] 是句子列表，按 q 顺序
                sents = ["".join(x[0] for x in s) for s in d[0]]
                # d[0] 结构是 [[ [译文,原文,...], ... ], ...] 每条q对应一段；简单起见按段切分
                # 实际返回：d[0] 为 list of segments，每个 segment 是 list of [trans, orig]
                # 多 q 时 google 会合并，稳妥做法：逐条单独请求回退
                if len(sents) == len(chunk):
                    trans_list = sents
                else:
                    raise ValueError("segment mismatch")
                for (i, key), tr in zip(todo_idx[b:b + 8], trans_list):
                    results[i] = tr
                    cache[key] = tr
                break
            except Exception as e:
                if attempt == 2:
                    # 回退：逐条请求
                    for (i, key), t in zip(todo_idx[b:b + 8], chunk):
                        try:
                            q2 = urllib.parse.urlencode({"q": t})
                            url2 = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&{q2}"
                            req2 = urllib.request.Request(url2, headers=UA)
                            d2 = json.load(urllib.request.urlopen(req2, timeout=20))
                            tr = "".join(x[0] for x in d2[0])
                            results[i] = tr
                            cache[key] = tr
                            time.sleep(0.4)
                        except Exception:
                            results[i] = texts[i]
                        time.sleep(0.3)
                else:
                    time.sleep(2)
        time.sleep(1)
    save_cache(cache)
    return [results.get(i, texts[i]) for i in range(len(texts))]


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    today = datetime.now(TZ_SH).strftime("%Y-%m-%d")
    day_file = os.path.join(DATA_DIR, f"{today}.json")

    # 读入今日已有（多次运行累积去重）
    existing = {}
    if os.path.exists(day_file):
        try:
            for a in json.load(open(day_file, encoding="utf-8")):
                existing[a["id"]] = a
        except Exception:
            pass

    all_new = []
    for src_en, src_zh, url in SOURCES:
        print(f"fetch {src_en} ...", flush=True)
        try:
            xml = fetch(url)
            items = parse_feed(xml, src_en, src_zh)
            print(f"  -> {len(items)} asia items", flush=True)
            all_new.extend(items)
        except Exception as e:
            print(f"  [fetch fail] {src_en}: {e}", flush=True)
        time.sleep(1)

    # 去重
    fresh = [a for a in all_new if a["id"] not in existing]
    print(f"total new: {len(fresh)} (existing {len(existing)})", flush=True)

    # 翻译标题+摘要
    if fresh:
        texts = []
        for a in fresh:
            texts.append(a["title_en"])
            texts.append(a["summary_en"])
        print(f"translating {len(texts)} texts ...", flush=True)
        tr = translate_batch(texts)
        for a, t_zh, s_zh in zip(fresh, tr[0::2], tr[1::2]):
            a["title_zh"] = t_zh
            a["summary_zh"] = s_zh
            existing[a["id"]] = a

    articles = sorted(existing.values(), key=lambda x: x["published"], reverse=True)
    json.dump(articles, open(day_file, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 更新日期索引（新日期在前）
    idx_file = os.path.join(DATA_DIR, "index.json")
    idx = []
    if os.path.exists(idx_file):
        try:
            idx = json.load(open(idx_file, encoding="utf-8"))
        except Exception:
            pass
    dates = {d["date"]: d for d in idx}
    dates[today] = {"date": today, "count": len(articles)}
    idx = sorted(dates.values(), key=lambda d: d["date"], reverse=True)
    json.dump(idx, open(idx_file, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"done: {today} 共 {len(articles)} 条", flush=True)


if __name__ == "__main__":
    main()
