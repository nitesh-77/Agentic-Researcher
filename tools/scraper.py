import os
import requests
from typing import Optional
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class ScraperTool:
    """Browserless.io scraper tool for web content extraction"""

    def __init__(self):
        self.api_key = os.getenv("BROWSERLESS_API_KEY")
        if not self.api_key:
            print("⚠️ Warning: BROWSERLESS_API_KEY not found")

    def scrape(self, url: str, objective: str = "research") -> Optional[dict]:
        """
        Scrape website content using Browserless /content endpoint
        """
        print(f"Scraping website: {url}")

        if not self.api_key:
            return {
                "content": "Error: Missing API Key",
                "status": "error",
                "title": "Error",
                "scraped_at": datetime.now().isoformat()
            }

        post_url = f"https://chrome.browserless.io/content?token={self.api_key}"

        payload = {
            "url": url,
            "rejectRequestPattern": [
                ".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", 
                ".mp4", ".woff", ".woff2", ".ico", ".webp",
                "google-analytics", "doubleclick", "googletagmanager" # Added trackers
            ],
            "gotoOptions": {
                "timeout": 15000,  
                "waitUntil": "domcontentloaded" 
            }
        }

        try:
            response = requests.post(post_url, json=payload, timeout=45)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")

                # Extract title
                title_tag = soup.find('title')
                title_text = title_tag.get_text().strip() if title_tag else url

                # Remove non-content tags
                for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript", "svg"]):
                    element.extract()

                # Get clean text
                text = soup.get_text(separator=' ', strip=True)

                if len(text) < 200:
                    return {
                        "content": "Error: Content too short or blocked.",
                        "title": title_text,
                        "url": url,
                        "scraped_at": datetime.now().isoformat(),
                        "status": "minimal"
                    }

                return {
                    "content": text[:20000], 
                    "title": title_text,
                    "url": url,
                    "scraped_at": datetime.now().isoformat(),
                    "status": "success"
                }
            
            else:
                # Safe error printing
                error_msg = response.text[:100]
                print(f"❌ Browserless error: {response.status_code} - {error_msg}")
                return {
                    "content": f"Error: Scrape failed with status {response.status_code}",
                    "title": "Error",
                    "url": url,
                    "scraped_at": datetime.now().isoformat(),
                    "status": "error"
                }

        except Exception as e:
            # Sanitize error message to prevent API key leak
            error_str = str(e)
            if self.api_key and self.api_key in error_str:
                error_str = error_str.replace(self.api_key, "REDACTED_KEY")
                
            print(f"❌ Scrape exception: {error_str}")
            return {
                "content": f"Error: Technical issue scraping website.",
                "title": "Error",
                "url": url,
                "scraped_at": datetime.now().isoformat(),
                "status": "error"
            }