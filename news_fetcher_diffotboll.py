import requests
import json
import os
import time
import feedparser
from dotenv import load_dotenv
from post_to_bluesky_diffotboll import authenticate, post_to_bluesky

# Load environment variables
load_dotenv()

# API URL for DIF Hockey news
DIF_FOTBOLL_API_URL = "https://www.dif.se/api/news-feed?includeVideosHiddenInListings=true&plain=true&orderBy=DateDesc&offset=0&limit=25"

# RSS-feed URL
SVENSKAFANS_RSS_FEED_URL = "https://www.svenskafans.com/rss/team/46"

# File to track posted news
POSTED_NEWS_FILE = "posted_news_football.json"

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


def fetch_dif_fotboll_news():
    print("Fetching DIF Fotboll news...")
    try:
        response = requests.get(DIF_FOTBOLL_API_URL)
        print(f"Response: {response.status_code}")
        response.raise_for_status()
        
        data = response.json()
        articles = []
        
        if "pages" in data and data["pages"]:
            for article_item in data["pages"][:3]:
                # Get article URL (need to add base domain)
                article_url = article_item.get("url", "")
                full_link = f"https://www.dif.se{article_url}"
                
                # Extract timestamp from ISO format date
                timestamp = time.time()  # Default to current time
                if "date" in article_item:
                    try:
                        date_str = article_item["date"]
                        # Parse ISO 8601 date format
                        timestamp = time.mktime(time.strptime(date_str.split('.')[0], "%Y-%m-%dT%H:%M:%S"))
                        print(f"DIF Fotboll article timestamp: {time.ctime(timestamp)}")
                    except (ValueError, IndexError) as e:
                        print(f"⚠️ Error parsing timestamp: {e}, using current time")
                
                # Get image URL if available
                image_url = None
                if "image" in article_item and article_item["image"] and "src" in article_item["image"]:
                    image_url = article_item["image"]["src"]
                
                # For video items, use thumbnail if available
                if not image_url and "thumbnailUrl" in article_item:
                    image_url = article_item.get("thumbnailUrl")
                
                # Get title (heading or name for videos)
                title = article_item.get("heading", article_item.get("name", ""))
                
                # Get description (preamble or description for videos)
                description = article_item.get("preamble", article_item.get("description", ""))
                
                articles.append({
                    "url": full_link,
                    "timestamp": timestamp,
                    "source": "DIF Fotboll",
                    "image_url": image_url,
                    "title": title,
                    "description": description
                })
            
            return articles
    except Exception as e:
        print(f"⚠️ Error fetching DIF Fotboll news: {e}")
    return []


def fetch_svenskafans_rss_news():
    print("Fetching SvenskaFans DIF Fotboll RSS news...")
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
    all_articles = fetch_dif_fotboll_news() + fetch_svenskafans_rss_news()
    
    # Print timestamps before sorting
    print("\nArticles before sorting:")
    for article in all_articles:
        date_string = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(article["timestamp"]))
        print(f"- {article['source']}: {date_string} - {article['title']}")
    
    # Sort by timestamp (oldest first)
    all_articles.sort(key=lambda x: x["timestamp"])
    
    # Print timestamps after sorting
    print("\nArticles after sorting (oldest first):")
    for article in all_articles:
        date_string = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(article["timestamp"]))
        print(f"- {article['source']}: {date_string} - {article['title']}")
    
    print(f"\nProcessing {len(all_articles)} articles in chronological order (oldest first)")
    
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
# The news_fetcher.py script fetches the latest news from two sources: