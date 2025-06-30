# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import feedparser
from datetime import datetime
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

# Liste des flux RSS à agréger
RSS_FEEDS = [
    "https://rss.lemonde.fr/c/205/f/3050/index.rss",
    "https://www.france24.com/fr/rss",
    "https://www.rfi.fr/fr/rss",
]

# Fonction pour récupérer l’image associée à un article
def extract_image(entry):
    # 1. media:content
    if "media_content" in entry:
        for media in entry.media_content:
            if "url" in media:
                return media["url"]

    # 2. media:thumbnail
    if "media_thumbnail" in entry:
        for thumb in entry.media_thumbnail:
            if "url" in thumb:
                return thumb["url"]

    # 3. image.href
    if hasattr(entry, "image") and hasattr(entry.image, "href"):
        return entry.image.href

    # 4. liens avec type image
    if "links" in entry:
        for link in entry.links:
            if link.get("type", "").startswith("image") and "href" in link:
                return link["href"]

    # 5. fallback : chercher une image dans le résumé HTML
    if hasattr(entry, "summary"):
        img_match = re.search(r'<img[^>]+src="([^">]+)"', entry.summary)
        if img_match:
            return img_match.group(1)

    return None

# Traitement des flux RSS
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
        iso_date = pub_date.isoformat() if pub_date else None
        image_url = extract_image(entry)

        articles.append({
            "title": title,
            "link": link,
            "published": iso_date,
            "summary": summary,
            "image": image_url,
        })

    return articles

# Endpoint principal
@app.get("/news")
def get_news():
    all_articles = []
    for url in RSS_FEEDS:
        all_articles.extend(parse_feed(url))

    articles_with_date = [a for a in all_articles if a["published"]]
    articles_sorted = sorted(
        articles_with_date,
        key=lambda x: datetime.fromisoformat(x["published"]),
        reverse=True,
    )

    return JSONResponse(
        content={"status": "ok", "articles": articles_sorted},
        media_type="application/json; charset=utf-8"
    )

# Pour exécuter localement
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
