# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import feedparser
from datetime import datetime
from typing import List
import html

app = FastAPI()

# CORS pour autoriser les requêtes de FlutterFlow
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

def parse_feed(url: str) -> List[dict]:
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        pub_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            pub_date = datetime(*entry.updated_parsed[:6])
        title = html.unescape(entry.title)
        summary = html.unescape(entry.summary) if hasattr(entry, "summary") else ""
        link = entry.link
        articles.append({
            "title": title,
            "link": link,
            "published": pub_date.isoformat() if pub_date else None,
            "summary": summary,
        })
    return articles

@app.get("/news")
def get_news():
    all_articles = []
    for url in RSS_FEEDS:
        all_articles.extend(parse_feed(url))
    articles_with_date = [a for a in all_articles if a["published"]]
    articles_sorted = sorted(articles_with_date, key=lambda x: x["published"], reverse=True)
    return {"status": "ok", "articles": articles_sorted}
