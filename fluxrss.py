from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import feedparser
from datetime import datetime, timedelta
from typing import List, Optional
import uvicorn
import html
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Dictionnaire : nom source -> url du flux RSS
RSS_FEEDS = {
    "lequipe": "https://www.lequipe.fr/rss/actu_rss.xml",
    "humanite": "https://www.humanite.fr/rss.xml",
    "liberation": "https://www.liberation.fr/arc/outboundfeeds/rss-all/?outputType=xml",
    "lexpress": "https://www.lexpress.fr/feeds/rss/",
    "leparisien": "https://feeds.leparisien.fr/leparisien/rss",
    "lefigaro": "https://www.lefigaro.fr/rss/figaro_actualites.xml",
    "lacroix": "https://www.la-croix.com/rss",
    "marianne": "https://www.marianne.net/rss.xml",
    "franceinfo": "https://www.franceinfo.fr/titres.rss",
    "lepoint": "https://www.lepoint.fr/rss.xml",
    "mediapart": "https://www.mediapart.fr/fr/journal/mot-cle/flux-rss",
    "20minutes": "https://www.20minutes.fr/rss/",
    "courrierinternational": "https://www.courrierinternational.com/feed",
    "nouvelobs": "https://www.nouvelobs.com/rss.xml",
    "lesechos": "https://www.lesechos.fr/rss/rss_general.xml",
    "bfmtv": "https://www.bfmtv.com/rss/news-24-7/",
    "lci": "https://www.lci.fr/rss/",
}

def extract_image(entry):
    # (même code que avant, inchangé)
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

def parse_feed(source_name: str, url: str) -> List[dict]:
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
            "source": source_name,
        })
    return articles

@app.get("/news")
def get_news(
    skip: int = Query(0), 
    limit: int = Query(200),
    sources: Optional[List[str]] = Query(None, description="Liste des sources à inclure")
):
    all_articles = []
    
    # Si sources est vide ou None, on prend tout
    if sources:
        # Normaliser les noms en minuscules
        sources = [s.lower() for s in sources]
        filtered_feeds = {k: v for k, v in RSS_FEEDS.items() if k in sources}
    else:
        filtered_feeds = RSS_FEEDS
    
    for source_name, url in filtered_feeds.items():
        all_articles.extend(parse_feed(source_name, url))

    articles_with_date = [a for a in all_articles if a["published"]]
    articles_sorted = sorted(
        articles_with_date,
        key=lambda x: datetime.fromisoformat(x["published"]),
        reverse=True,
    )

    limited_articles = articles_sorted[skip:skip+limit]

    return JSONResponse(
        content={"status": "ok", "articles": limited_articles},
        media_type="application/json; charset=utf-8"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
