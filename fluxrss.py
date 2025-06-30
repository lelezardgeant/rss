# -*- coding: utf-8 -*-
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import feedparser
from datetime import datetime, timedelta
from typing import List
import uvicorn
import html
import re

app = FastAPI()

# Autoriser les requêtes depuis FlutterFlow (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

RSS_FEEDS = [
    "https://rss.lemonde.fr/c/205/f/3050/index.rss",
    "https://www.france24.com/fr/rss",
    "https://www.rfi.fr/fr/rss",
]

def extract_image(entry):
    if "media_content" in entry:
        for media in entry.media_content:
            if "url" in media:
                return media["url"]
    if "media_thumbnail" in entry:
        for thumb in entry.media_thumbnail:
            if "url" in thumb:
                return thumb["url"]
    if hasattr(entry, "image") and hasattr(entry.image, "href"):
        return entry.image.href
    if "links" in entry:
        for link in entry.links:
            if link.get("type", "").startswith("image") and "href" in link:
                return link["href"]
    if hasattr(entry, "summary"):
        img_match = re.search(r'<img[^>]+src="([^">]+)"', entry.summary)
        if img_match:
            return img_match.group(1)
    return None

def human_readable_date(pub_date: datetime) -> str:
    now = datetime.now()
    diff = now - pub_date
    if diff < timedelta(minutes=60):
        minutes = int(diff.total_seconds() // 60)
        return f"Il y a {minutes} minute{'s' if minutes > 1 else ''}"
    elif diff < timedelta(hours=24):
        hours = int(diff.total_seconds() // 3600)
        return f"Il y a {hours} heure{'s' if hours > 1 else ''}"
    elif diff < timedelta(hours=48):
        return "Hier"
    else:
        return pub_date.strftime("%d/%m/%Y")

def parse_feed(url: str) -> List[dict]:
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        pub_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            pub_date = datetime(*entry.updated_parsed[:6])

        title = html.unescape(entry.title).strip()
        summary = html.unescape(entry.summary).strip() if hasattr(entry, "summary") else ""
        link = entry.link
        image_url = extract_image(entry)

        display_date = human_readable_date(pub_date) if pub_date else ""

        articles.append({
            "title": title,
            "link": link,
            "published": pub_date.isoformat() if pub_date else None,
            "summary": summary,
            "image": image_url,
            "display_date": display_date,
        })
    return articles

@app.get("/news")
def get_news(skip: int = Query(0, ge=0), limit: int = Query(10, gt=0)):
    all_articles = []
    for url in RSS_FEEDS:
        all_articles.extend(parse_feed(url))

    articles_with_date = [a for a in all_articles if a["published"]]
    articles_sorted = sorted(
        articles_with_date,
        key=lambda x: datetime.fromisoformat(x["published"]),
        reverse=True,
    )

    paged_articles = articles_sorted[skip:skip + limit]

    return JSONResponse(
        content={
            "status": "ok",
            "articles": paged_articles,
            "total": len(articles_sorted),
            "skip": skip,
            "limit": limit
        },
        media_type="application/json; charset=utf-8"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
