import requests
import json
import os
import time
import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BLUESKY_USERNAME = os.getenv("BLUESKY_USERNAME")
BLUESKY_APP_PASSWORD = os.getenv("BLUESKY_APP_PASSWORD")

# Authenticate with Bluesky API
def authenticate():
    auth_url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    auth_payload = {"identifier": BLUESKY_USERNAME, "password": BLUESKY_APP_PASSWORD}
    
    for attempt in range(3):
        try:
            auth_response = requests.post(auth_url, json=auth_payload, timeout=10)
            auth_response.raise_for_status()
            return auth_response.json()["accessJwt"]
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Authentication failed (attempt {attempt + 1}/3): {e}")
            time.sleep(5)
    
    print("🚨 Authentication failed after 3 attempts. Exiting.")
    exit()

# Fetch OpenGraph metadata
def fetch_opengraph_metadata(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        
        title = og_title["content"] if og_title else soup.title.string if soup.title else "No Title"
        description = og_desc["content"] if og_desc else "No description available."
        image_url = og_image["content"] if og_image else None
        
        return title, description, image_url
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Failed to fetch metadata: {e}")
        return None, None, None

# Upload image to Bluesky
def upload_image(access_token, image_url):
    try:
        # Special handling for SvenskaFans images
        browser_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        # Add specific referer for svenskafans images
        if "svenskafans.com" in image_url:
            print("Detected SvenskaFans image, using special headers...")
            browser_headers["Referer"] = "https://www.svenskafans.com/"
            browser_headers["Origin"] = "https://www.svenskafans.com"
            browser_headers["sec-ch-ua"] = '"Chromium";v="122", "Google Chrome";v="122", "Not:A-Brand";v="99"'
            browser_headers["sec-ch-ua-mobile"] = "?0"
            browser_headers["sec-ch-ua-platform"] = '"macOS"'
            browser_headers["Sec-Fetch-Dest"] = "image"
            browser_headers["Sec-Fetch-Mode"] = "no-cors" 
            browser_headers["Sec-Fetch-Site"] = "same-site"
        
        img_response = requests.get(image_url, headers=browser_headers, timeout=10)
        img_response.raise_for_status()
        
        mime_type = img_response.headers['Content-Type']
        print(f"Image MIME type: {mime_type}")
        if not mime_type.startswith('image/'):
            print(f"⚠️ Invalid MIME type: {mime_type}")
            return None
        
        upload_url = "https://bsky.social/xrpc/com.atproto.repo.uploadBlob"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": mime_type
        }
        
        upload_response = requests.post(upload_url, headers=headers, data=img_response.content)
        upload_response.raise_for_status()
        return upload_response.json()["blob"]
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Failed to upload image: {e}")
        # Continue without image
        return None

# Post to Bluesky with link preview
def post_to_bluesky(access_token, article_url, title=None, description=None, image_url=None):
    try:
        # If metadata isn't provided, fetch it from the URL
        if not (title and description):
            title, description, fetched_image_url = fetch_opengraph_metadata(article_url)
            # Use the fetched image if none was provided
            if not image_url and fetched_image_url:
                image_url = fetched_image_url
        
        post_url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        
        embed = {"$type": "app.bsky.embed.external", "external": {"uri": article_url, "title": title, "description": description}}
        
        if image_url:
            blob = upload_image(access_token, image_url)
            if blob:
                embed["external"]["thumb"] = blob
        
        post_text = f"{title}\nDjurgården Hockey\n{article_url}"
        post_payload = {
            "repo": BLUESKY_USERNAME,
            "collection": "app.bsky.feed.post",
            "record": {
                "text": post_text,
                "embed": embed,
                "facets": [{
                    "$type": "app.bsky.richtext.facet",
                    "index": {
                        "start": post_text.find(article_url),
                        "end": post_text.find(article_url) + len(article_url),
                        "byteStart": post_text.encode().find(article_url.encode()),
                        "byteEnd": post_text.encode().find(article_url.encode()) + len(article_url.encode())
                    },
                    "features": [{"$type": "app.bsky.richtext.facet.link", "uri": article_url}]
                }],
                "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
            }
        }
        
        try:
            post_response = requests.post(post_url, headers=headers, json=post_payload, timeout=10)
            post_response.raise_for_status()
            print(f"✅ Successfully posted: {title}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Failed to post: {e}")
            if e.response is not None:
                print(f"Response content: {e.response.content}")
            return False
    except Exception as e:
        print(f"⚠️ Failed to post: {e}")
        return False
