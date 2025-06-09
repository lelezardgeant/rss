from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import feedparser
from datetime import datetime
from typing import List
import uvicorn

app = FastAPI()

# Autoriser les requêtes depuis FlutterFlow (cors)
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

def parse_feed(url: str) -> List[dict]:
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        # La date peut être sous plusieurs formats, on essaye de la normaliser
        pub_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            pub_date = datetime(*entry.updated_parsed[:6])

        articles.append({
            "title": entry.title,
            "link": entry.link,
            "published": pub_date.isoformat() if pub_date else None,
            "summary": entry.summary if hasattr(entry, "summary") else "",
        })
    return articles

@app.get("/news")
def get_news():
    all_articles = []
    for url in RSS_FEEDS:
        all_articles.extend(parse_feed(url))

    # Supprimer les articles sans date et trier par date décroissante
    articles_with_date = [a for a in all_articles if a["published"]]
    articles_sorted = sorted(
        articles_with_date,
        key=lambda x: x["published"],
        reverse=True,
    )
    return {"status": "ok", "articles": articles_sorted}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
