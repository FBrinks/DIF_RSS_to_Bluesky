import requests
import json
import os
import time
import feedparser
from dotenv import load_dotenv
from post_to_bluesky import authenticate, post_to_bluesky

# Load environment variables
load_dotenv()

# API URL for DIF Hockey news
DIF_HOCKEY_API_URL = "https://www.difhockey.se/api/articles/site-news/list?page=0&pagesize=5&orderByDate=desc"

# RSS-feed URL
SVENSKAFANS_RSS_FEED_URL = "https://www.svenskafans.com/rss/team/251"

# File to track posted news
POSTED_NEWS_FILE = "posted_news.json"

def load_posted_news():
    try:
        if os.path.exists(POSTED_NEWS_FILE):
            with open(POSTED_NEWS_FILE, "r") as file:
                return json.load(file)
    except (json.JSONDecodeError, IOError):
        print("⚠️ Failed to load `posted_news.json`, resetting file.")
    return []


def save_posted_news(posted_news):
    try:
        with open(POSTED_NEWS_FILE, "w") as file:
            json.dump(posted_news[-100:], file)  # Keep only the last 100 posts
    except IOError as e:
        print(f"⚠️ Failed to save `posted_news.json`: {e}")


def fetch_dif_hockey_news():
    print("Fetching DIF Hockey news...")
    try:
        response = requests.get(DIF_HOCKEY_API_URL)
        print(f"Response: {response.status_code}")
        response.raise_for_status()
        
        data = response.json()
        articles = []
        
        if "data" in data and "articleItems" in data["data"] and data["data"]["articleItems"]:
            for article_item in data["data"]["articleItems"][:3]:
                article_id = article_item.get("id", "")
                full_link = article_item.get("permalink", f"https://www.difhockey.se/article/{article_id}/view").strip()
                
                if not full_link.endswith("/view"):
                    full_link += "/view"
                
                # Extract timestamp and other available metadata directly from API
                timestamp = time.time()  # Default to current time
                if "publishedDate" in article_item:
                    try:
                        publish_date = article_item["publishedDate"].split("T")[0]
                        timestamp = time.mktime(time.strptime(publish_date, "%Y-%m-%d"))
                    except (ValueError, IndexError):
                        pass
                
                # Get any available image from the API response
                image_url = None
                if "imageUrl" in article_item:
                    image_url = article_item["imageUrl"]
                
                articles.append({
                    "url": full_link,
                    "timestamp": timestamp,
                    "source": "DIF Hockey",
                    "image_url": image_url,
                    "title": article_item.get("title", ""),
                    "description": article_item.get("preamble", "")
                })
            
            return articles
    except Exception as e:
        print(f"⚠️ Error fetching DIF Hockey news: {e}")
    return []


def fetch_svenskafans_rss_news():
    print("Fetching SvenskaFans RSS news...")
    try:
        browser_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Referer": "https://www.svenskafans.com/",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        response = requests.get(SVENSKAFANS_RSS_FEED_URL, headers=browser_headers, timeout=10)
        response.raise_for_status()
        
        feed = feedparser.parse(response.text)
        if not feed.entries:
            print("🚨 No RSS news found!")
            return []
        
        articles = []
        for entry in feed.entries[:3]:
            # Extract timestamp
            timestamp = time.time()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                timestamp = time.mktime(entry.published_parsed)
            
            url = entry.link
            title = entry.title if hasattr(entry, 'title') else ""
            
            # Instead of parsing RSS, visit the actual article page to extract image
            try:
                print(f"Fetching full article from {url}")
                article_response = requests.get(url, headers=browser_headers, timeout=10)
                article_response.raise_for_status()
                
                from bs4 import BeautifulSoup
                article_soup = BeautifulSoup(article_response.text, 'html.parser')
                
                # Look for OpenGraph image meta tag (most reliable)
                image_url = None
                og_image = article_soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    image_url = og_image.get('content')
                    print(f"Found OpenGraph image: {image_url}")
                
                # Fallback: Look for article-image class
                if not image_url:
                    article_img = article_soup.find('img', class_='article-image')
                    if article_img and article_img.get('src'):
                        image_url = article_img.get('src')
                        print(f"Found article image: {image_url}")
                
                # Fallback: Look for first image in article container
                if not image_url:
                    article_container = article_soup.find('div', class_='article-container')
                    if article_container:
                        img = article_container.find('img')
                        if img and img.get('src'):
                            image_url = img.get('src')
                            print(f"Found container image: {image_url}")
                
                # Extract description from meta description
                description = ""
                meta_desc = article_soup.find('meta', {'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    description = meta_desc.get('content')
                else:
                    # Fallback: Get first paragraph
                    first_p = article_soup.find('p')
                    if first_p:
                        description = first_p.text[:200]  # Limit to 200 chars
            
            except Exception as e:
                print(f"⚠️ Error fetching article page: {e}")
                description = ""
                # Continue with the URL but without image
            
            articles.append({
                "url": url,
                "timestamp": timestamp,
                "source": "SvenskaFans",
                "title": title,
                "description": description,
                "image_url": image_url
            })
        
        print(f"✅ Successfully fetched {len(articles)} RSS entries from SvenskaFans")
        return articles
    except Exception as e:
        print(f"⚠️ Failed to fetch RSS feed: {e}")
        return []


def process_all_news(access_token):
    posted_news = load_posted_news()
    
    # Fetch all news
    all_articles = fetch_dif_hockey_news() + fetch_svenskafans_rss_news()
    
    # Sort by timestamp (oldest first)
    all_articles.sort(key=lambda x: x["timestamp"])
    
    print(f"Processing {len(all_articles)} articles in chronological order")
    
    # Post each article
    for article in all_articles:
        url = article["url"]
        source = article["source"]
        
        if url not in posted_news:
            print(f"Posting {source} article: {url}")
            
            # We can directly pass the metadata to post_to_bluesky if needed
            success = post_to_bluesky(
                access_token, 
                url,
                title=article.get("title"),
                description=article.get("description"),
                image_url=article.get("image_url")
            )
            
            if success:
                posted_news.append(url)
                print(f"✅ Successfully posted {source} article")
            
            # Add delay between posts
            time.sleep(5)
    
    # Save updated list of posted news
    save_posted_news(posted_news)


def main():
    access_token = authenticate()
    process_all_news(access_token)

if __name__ == "__main__":
    main()
# The news_fetcher.py script fetches the latest news from two sources: the DIF Hockey website and the SvenskaFans RSS feed.