#!/usr/bin/env python3
# yoola_reviews_rss.py
import requests, json, os, re
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from dateutil import parser as dateparser
from datetime import datetime, timezone

SHOP = "Yoola"
SHOP_URL = f"https://www.etsy.com/shop/{SHOP}/reviews"
OUTPUT_PATH = "docs/yoola_reviews.xml"

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; YoolaReviewsBot/1.0; +https://yooladesign.com)"
}

def parse_jsonld(soup):
    reviews = []
    for script in soup.find_all("script", type="application/ld+json"):
        txt = script.string
        if not txt:
            continue
        try:
            data = json.loads(txt)
        except Exception:
            continue
        def walk(obj):
            if isinstance(obj, dict):
                if obj.get("@type") == "Review":
                    reviews.append(obj)
                if "review" in obj and isinstance(obj["review"], list):
                    for r in obj["review"]:
                        if isinstance(r, dict) and r.get("@type") == "Review":
                            reviews.append(r)
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)
        walk(data)
    return reviews

def parse_fallback(soup):
    reviews = []
    # try elements with data-review-id
    for elem in soup.select("[data-review-id]"):
        try:
            rid = elem.get("data-review-id")
            # try to extract visible review text
            text = " ".join(elem.stripped_strings)
            # try to find a date
            date = None
            t = elem.find("time")
            if t and t.has_attr("datetime"):
                date = t["datetime"]
            # try reviewer name attribute (if present)
            reviewer = elem.get("data-reviewer-name") or ""
            reviews.append({
                "@type": "Review",
                "reviewBody": text,
                "datePublished": date,
                "author": {"name": reviewer},
                "id": rid
            })
        except Exception:
            continue
    if reviews:
        return reviews
    # final fallback: find any block whose class name contains "review"
    for elem in soup.find_all(class_=re.compile("review", re.I)):
        text = " ".join(elem.stripped_strings)
        reviews.append({"@type": "Review", "reviewBody": text})
    return reviews

def normalize_review(r):
    body = r.get("reviewBody") or r.get("description") or ""
    author = r.get("author")
    if isinstance(author, dict):
        author_name = author.get("name", "")
    else:
        author_name = author or ""
    date = r.get("datePublished") or r.get("date") or None
    try:
        dt = dateparser.parse(date) if date else None
    except Exception:
        dt = None
    item = r.get("itemReviewed", {})
    link = None
    if isinstance(item, dict):
        link = item.get("url") or item.get("sameAs")
    return {"author": author_name, "body": body, "date": dt, "link": link}

def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    resp = requests.get(SHOP_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    reviews_raw = parse_jsonld(soup)
    if not reviews_raw:
        reviews_raw = parse_fallback(soup)

    reviews = [normalize_review(r) for r in reviews_raw]

    fg = FeedGenerator()
    fg.title(f"{SHOP} Etsy Shop Reviews")
    fg.link(href=f"https://www.etsy.com/shop/{SHOP}", rel="alternate")
    fg.description(f"Latest reviews from the {SHOP} Etsy shop")

    for i, r in enumerate(reviews[:100]):
        fe = fg.add_entry()
        title = (r["author"] or "Customer") + " — " + (r["body"][:60].strip() if r["body"] else "Review")
        fe.id(f"{SHOP}-review-{i}-{r['date'].isoformat() if r['date'] else i}")
        fe.title(title)
        if r["link"]:
            fe.link(href=r["link"])
        fe.description(r["body"])
        if r["date"]:
            fe.pubDate(r["date"])
        else:
            fe.pubDate(datetime.now(timezone.utc))

    fg.rss_file(OUTPUT_PATH)
    print(f"Saved {len(reviews)} reviews to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
