import os
import json
import requests
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

class SearchTool:
    """Serper.dev search tool for web search operations"""

    def __init__(self):
        self.api_key = os.getenv("SERP_API_KEY")
        if not self.api_key:
            raise ValueError("SERP_API_KEY not found in environment variables")

    def search(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Search Google using Serper API
        Returns list of search results with title, link, snippet
        """
        url = "https://google.serper.dev/search"
        payload = json.dumps({
            "q": query,
            "num": num_results
        })
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()

            data = response.json()

            # Extract organic search results
            results = []
            if 'organic' in data:
                for result in data['organic']:
                    results.append({
                        'title': result.get('title', ''),
                        'link': result.get('link', ''),
                        'snippet': result.get('snippet', ''),
                        'position': result.get('position', 0)
                    })

            return results

        except Exception as e:
            print(f"Error in search: {e}")
            return []

    def filter_quality_urls(self, results: List[Dict]) -> List[Dict]:
        """
        Filter out low-quality or blacklisted URLs
        Blacklist: youtube, pinterest, social media, etc.
        """
        blacklist_domains = [
            'youtube.com', 'youtu.be', 'pinterest.com', 'instagram.com',
            'facebook.com', 'twitter.com', 'tiktok.com', 'reddit.com'
        ]

        filtered = []
        for result in results:
            url = result.get('link', '').lower()

            # Skip if domain is blacklisted
            if any(domain in url for domain in blacklist_domains):
                continue

            # Skip if no meaningful content
            if not result.get('title') or not result.get('snippet'):
                continue

            filtered.append(result)

        return filtered