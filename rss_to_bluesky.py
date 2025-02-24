import feedparser
import requests
import os
import json
from atproto import Client
from dotenv import load_dotenv

# Ladda miljövariabler från .env
load_dotenv()

RSS_FEED_URL = "DIN_NYA_SVENSKAFANS_RSS_URL"

USERNAME = os.getenv("BLUESKY_USERNAME")
APP_PASSWORD = os.getenv("BLUESKY_APP_PASSWORD")
POSTED_FILE = "posted_news.json"

# Hämta RSS-flödet
response = requests.get(RSS_FEED_URL)
raw_data = response.text
feed = feedparser.parse(raw_data)

if not feed.entries:
    print("🚨 Inga nyheter hittades! Kolla om RSS-länken är rätt.")
    exit()

latest_entry = feed.entries[0]
title = latest_entry.title
link = latest_entry.link
news_id = latest_entry.id

# Skapa en facet för att markera länken
facets = [{
    "index": {
        "byteStart": len(title) + 2,  # Positionen där länken börjar i texten
        "byteEnd": len(title) + 2 + len(link)  # Positionen där länken slutar
    },
    "features": [{
        "$type": "app.bsky.richtext.facet#link",
        "uri": link
    }]
}]

# Kolla om vi redan har postat nyheten
if os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, "r") as f:
        posted_news = json.load(f)
else:
    posted_news = []

if news_id in posted_news:
    print("Ingen ny nyhet att posta.")
else:
    # Formatera inlägget och använd facets för att tvinga en klickbar länk
    content = f"{title}\n\n{link}\n\n#DIFhockey"

    # Logga in och posta på Bluesky med facets
    client = Client()
    client.login(USERNAME, APP_PASSWORD)
    client.post(content, facets=facets)

    print("✅ Postat på Bluesky:", content)

    # Spara postad nyhet
    posted_news.append(news_id)
    with open(POSTED_FILE, "w") as f:
        json.dump(posted_news, f)
