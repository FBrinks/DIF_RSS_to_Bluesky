import requests
import json
import os
from dotenv import load_dotenv
import feedparser
import datetime
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

BLUESKY_USERNAME = os.getenv("BLUESKY_USERNAME")
BLUESKY_APP_PASSWORD = os.getenv("BLUESKY_APP_PASSWORD")

# Authenticate with Bluesky API
def authenticate():
    auth_url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    auth_payload = {"identifier": BLUESKY_USERNAME, "password": BLUESKY_APP_PASSWORD}
    auth_response = requests.post(auth_url, json=auth_payload)
    
    if auth_response.status_code == 200:
        return auth_response.json()["accessJwt"]
    else:
        print(f"⚠️ Authentication failed: {auth_response.text}")
        exit()

# Fetch RSS Feed
RSS_FEED_URL = "https://www.svenskafans.com/rss/team/251"
feed = feedparser.parse(requests.get(RSS_FEED_URL).text)

if not feed.entries:
    print("🚨 No news found! Exiting.")
    exit()

latest_entry = feed.entries[0]
title = latest_entry.title
link = latest_entry.link

# Fetch embed URL card
def fetch_embed_url_card(access_token: str, url: str) -> dict:
    card = {
        "uri": url,
        "title": "",
        "description": "",
    }

    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    title_tag = soup.find("meta", property="og:title")
    if title_tag:
        card["title"] = title_tag["content"]
    description_tag = soup.find("meta", property="og:description")
    if description_tag:
        card["description"] = description_tag["content"]

    image_tag = soup.find("meta", property="og:image")
    if image_tag:
        img_url = image_tag["content"]
        if "://" not in img_url:
            img_url = url + img_url
        try:
            resp = requests.get(img_url)
            resp.raise_for_status()

            blob_resp = requests.post(
                "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
                headers={
                    "Content-Type": "image/png",
                    "Authorization": "Bearer " + access_token,
                },
                data=resp.content,
            )
            blob_resp.raise_for_status()
            card["thumb"] = blob_resp.json()["blob"]
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Failed to fetch or upload image: {e}")

    return {
        "$type": "app.bsky.embed.external",
        "external": card,
    }

# Create a Bluesky post with a clickable hyperlink and website card embed
def post_to_bluesky(access_token, title, link):
    post_url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    
    post_text = f"{title}\n\n{link}\n\n#DIFhockey"
    
    facets = [{
        "index": {
            "byteStart": len(title) + 2,
            "byteEnd": len(title) + 2 + len(link)
        },
        "features": [{
            "$type": "app.bsky.richtext.facet#link",
            "uri": link
        }]
    }]
    
    embed = fetch_embed_url_card(access_token, link)
    
    post_payload = {
        "repo": BLUESKY_USERNAME,
        "collection": "app.bsky.feed.post",
        "record": {
            "text": post_text,
            "facets": facets,
            "createdAt": datetime.datetime.utcnow().isoformat() + "Z",
            "embed": embed
        }
    }
    
    post_response = requests.post(post_url, headers=headers, json=post_payload)
    
    if post_response.status_code == 200:
        print("✅ Successfully posted to Bluesky with a clickable hyperlink and website card embed!")
    else:
        print(f"⚠️ Failed to post: {post_response.text}")

# Execute
access_token = authenticate()
post_to_bluesky(access_token, title, link)
