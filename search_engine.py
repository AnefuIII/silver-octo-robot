"""
Search engine module for Google and Bing APIs (Agent-ready version).

Responsible for:
- Generating intelligent search queries
- Executing multi-engine searches
- Deduplicating and tagging results
- Preparing search evidence for downstream AI reasoning
"""

import requests
import time
from typing import List, Dict
from config import Config


class SearchEngine:
    """Handles intelligent search operations using Google and Bing APIs."""

    def __init__(self):
        self.google_api_key = Config.GOOGLE_API_KEY
        self.google_engine_id = Config.GOOGLE_SEARCH_ENGINE_ID
        self.bing_api_key = Config.BING_API_KEY
        self.bing_endpoint = Config.BING_SEARCH_ENDPOINT

        self.last_request_time = 0
        self.min_request_interval = 60 / max(Config.MAX_REQUESTS_PER_MINUTE, 1)

    # ------------------------------------------------------------------
    # RATE LIMITING
    # ------------------------------------------------------------------

    def _rate_limit(self):
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    # ------------------------------------------------------------------
    # QUERY GENERATION (INTELLIGENCE LAYER)
    # ------------------------------------------------------------------

    def build_queries(self, service: str, location: str, platform: str) -> List[str]:
        """
        Build multiple query variants to improve recall.
        """
        site_map = {
            "instagram": "site:instagram.com",
            "twitter": "site:twitter.com",
            "x": "site:twitter.com",
            "facebook": "site:facebook.com",
            "tiktok": "site:tiktok.com",
        }

        site = site_map.get(platform.lower(), "")

        base_queries = [
            f'{site} "{service} vendor {location}"',
            f'{site} "{service} in {location}"',
            f'{site} "{service}" "{location}"',
            f'{site} "{service}" whatsapp "{location}"',
        ]

        # Remove empty site searches
        return [q.strip() for q in base_queries if q.strip()]

    # ------------------------------------------------------------------
    # GOOGLE SEARCH
    # ------------------------------------------------------------------

    def search_google(self, query: str, num_results: int = 10) -> List[Dict]:
        if not self.google_api_key or not self.google_engine_id:
            return []

        self._rate_limit()

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.google_engine_id,
            "q": query,
            "num": min(num_results, 10),
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("items", []):
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "google",
                    "query_used": query
                })

            return results

        except requests.exceptions.RequestException:
            return []

    # ------------------------------------------------------------------
    # BING SEARCH
    # ------------------------------------------------------------------

    def search_bing(self, query: str, num_results: int = 10) -> List[Dict]:
        if not self.bing_api_key:
            return []

        self._rate_limit()

        headers = {
            "Ocp-Apim-Subscription-Key": self.bing_api_key
        }
        params = {
            "q": query,
            "count": min(num_results, 50),
            "textFormat": "Raw",
        }

        try:
            response = requests.get(
                self.bing_endpoint,
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("webPages", {}).get("value", []):
                results.append({
                    "title": item.get("name", ""),
                    "link": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "bing",
                    "query_used": query
                })

            return results

        except requests.exceptions.RequestException:
            return []

    # ------------------------------------------------------------------
    # MAIN SEARCH ORCHESTRATION
    # ------------------------------------------------------------------

    def search_vendors(self, service: str, location: str, platform: str) -> List[Dict]:
        """
        Perform intelligent multi-query search for vendors.
        """
        queries = self.build_queries(service, location, platform)

        raw_results: List[Dict] = []

        for query in queries:
            raw_results.extend(self.search_google(query))
            raw_results.extend(self.search_bing(query))

        # ------------------------------------------------------------------
        # DEDUPLICATION & BASIC SCORING
        # ------------------------------------------------------------------

        seen_urls = set()
        unique_results = []

        for result in raw_results:
            url = result.get("link")
            if not url or url in seen_urls:
                continue

            seen_urls.add(url)

            # Lightweight relevance signal
            relevance_score = 0.0
            title = result.get("title", "").lower()
            snippet = result.get("snippet", "").lower()

            if service.lower() in title:
                relevance_score += 0.3
            if location.lower() in snippet:
                relevance_score += 0.3
            if "whatsapp" in snippet or "wa.me" in snippet:
                relevance_score += 0.2
            if platform.lower() in result.get("query_used", "").lower():
                relevance_score += 0.2

            result["relevance_score"] = round(min(relevance_score, 1.0), 2)
            unique_results.append(result)

        # Sort by relevance score (descending)
        unique_results.sort(key=lambda r: r["relevance_score"], reverse=True)

        return unique_results


# """Search engine module for Google and Bing APIs."""
# import requests
# import time
# from typing import List, Dict, Optional
# from config import Config


# class SearchEngine:
#     """Handles search operations using Google and Bing APIs."""
    
#     def __init__(self):
#         self.google_api_key = Config.GOOGLE_API_KEY
#         self.google_engine_id = Config.GOOGLE_SEARCH_ENGINE_ID
#         self.bing_api_key = Config.BING_API_KEY
#         self.bing_endpoint = Config.BING_SEARCH_ENDPOINT
#         self.last_request_time = 0
#         self.min_request_interval = 60 / Config.MAX_REQUESTS_PER_MINUTE
    
#     def _rate_limit(self):
#         """Implement rate limiting between requests."""
#         current_time = time.time()
#         time_since_last_request = current_time - self.last_request_time
        
#         if time_since_last_request < self.min_request_interval:
#             sleep_time = self.min_request_interval - time_since_last_request
#             time.sleep(sleep_time)
        
#         self.last_request_time = time.time()
    
#     def search_google(self, query: str, num_results: int = 10) -> List[Dict]:
#         """
#         Search using Google Custom Search API.
        
#         Args:
#             query: Search query string
#             num_results: Number of results to return (max 10 per request)
        
#         Returns:
#             List of search result dictionaries
#         """
#         if not self.google_api_key or not self.google_engine_id:
#             print("Warning: Google API credentials not configured")
#             return []
        
#         self._rate_limit()
        
#         url = "https://www.googleapis.com/customsearch/v1"
#         params = {
#             'key': self.google_api_key,
#             'cx': self.google_engine_id,
#             'q': query,
#             'num': min(num_results, 10)
#         }
        
#         try:
#             response = requests.get(url, params=params, timeout=10)
#             response.raise_for_status()
#             data = response.json()
            
#             results = []
#             if 'items' in data:
#                 for item in data['items']:
#                     results.append({
#                         'title': item.get('title', ''),
#                         'link': item.get('link', ''),
#                         'snippet': item.get('snippet', ''),
#                         'source': 'google'
#                     })
            
#             return results
#         except requests.exceptions.RequestException as e:
#             print(f"Error searching Google: {e}")
#             return []
    
#     def search_bing(self, query: str, num_results: int = 10) -> List[Dict]:
#         """
#         Search using Bing Search API.
        
#         Args:
#             query: Search query string
#             num_results: Number of results to return
        
#         Returns:
#             List of search result dictionaries
#         """
#         if not self.bing_api_key:
#             print("Warning: Bing API credentials not configured")
#             return []
        
#         self._rate_limit()
        
#         headers = {
#             'Ocp-Apim-Subscription-Key': self.bing_api_key
#         }
#         params = {
#             'q': query,
#             'count': min(num_results, 50),
#             'textDecorations': True,
#             'textFormat': 'HTML'
#         }
        
#         try:
#             response = requests.get(self.bing_endpoint, headers=headers, params=params, timeout=10)
#             response.raise_for_status()
#             data = response.json()
            
#             results = []
#             if 'webPages' in data and 'value' in data['webPages']:
#                 for item in data['webPages']['value']:
#                     results.append({
#                         'title': item.get('name', ''),
#                         'link': item.get('url', ''),
#                         'snippet': item.get('snippet', ''),
#                         'source': 'bing'
#                     })
            
#             return results
#         except requests.exceptions.RequestException as e:
#             print(f"Error searching Bing: {e}")
#             return []
    
#     def search_vendors(self, service: str, location: str, platform: str = 'instagram') -> List[Dict]:
#         """
#         Search for vendors on specific platforms.
        
#         Args:
#             service: Service/product name (e.g., 'cake', 'plumber')
#             location: Location (e.g., 'Lagos', 'Abuja')
#             platform: Platform to search ('instagram' or 'twitter')
        
#         Returns:
#             List of search results
#         """
#         if platform.lower() == 'instagram':
#             site = 'site:instagram.com'
#         elif platform.lower() == 'twitter':
#             site = 'site:twitter.com'
#         else:
#             site = ''
        
#         query = f'{site} "{service} in {location}"'
        
#         # Try both search engines
#         results = []
        
#         # Search Google
#         google_results = self.search_google(query, num_results=10)
#         results.extend(google_results)
        
#         # Search Bing
#         bing_results = self.search_bing(query, num_results=10)
#         results.extend(bing_results)
        
#         # Remove duplicates based on URL
#         seen_urls = set()
#         unique_results = []
#         for result in results:
#             if result['link'] not in seen_urls:
#                 seen_urls.add(result['link'])
#                 unique_results.append(result)
        
#         return unique_results


