"""
Vendor extraction and enrichment module (Agent-ready version).

This module extracts vendor information from search results,
infers contacts and location, enriches with Google Maps where possible,
and produces confidence-scored vendor profiles.
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import googlemaps
from config import Config


JOB_KEYWORDS = [
    "hiring", "salary", "vacancy", "apply",
    "job", "career", "position",
    "recruiting", "opening", "employment"
]



class VendorExtractor:
    """Extracts, enriches, and scores vendor information."""

    def __init__(self):
        self.gmaps_client = None
        if Config.GOOGLE_MAPS_API_KEY and Config.GOOGLE_MAPS_API_KEY != "your_google_maps_api_key_here":
            try:
                self.gmaps_client = googlemaps.Client(key=Config.GOOGLE_MAPS_API_KEY)
            except Exception as e:
                print(f"Warning: Google Maps client not initialized: {e}")

    # ---------------------------------------------------------------------
    # CONTACT EXTRACTION
    # ---------------------------------------------------------------------

    def extract_whatsapp_numbers(self, text: str) -> List[str]:
        """Extract WhatsApp / phone numbers from text."""
        patterns = [
            r'wa\.me[/\+]?(\d+)',
            r'whatsapp[:\s]*([\+\d][\d\s\-]{9,})',
            r'(\+?234[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{4})',
            r'(\+?\d[\d\s\-]{9,})',
        ]

        numbers = set()
        for pattern in patterns:
            for match in re.findall(pattern, text, re.IGNORECASE):
                cleaned = re.sub(r"[^\d+]", "", match)
                if len(cleaned) >= 10:
                    numbers.add(cleaned)

        return list(numbers)

    def extract_instagram_links(self, text: str) -> List[str]:
        """Extract Instagram profile URLs or handles."""
        links = set()

        patterns = [
            r'https?://(www\.)?instagram\.com/[\w\.]+/?',
            r'instagram\.com/[\w\.]+/?',
            r'@[\w\.]{3,}',
        ]

        for pattern in patterns:
            for match in re.findall(pattern, text, re.IGNORECASE):
                if match.startswith("@"):
                    links.add(f"https://instagram.com/{match[1:]}")
                elif match.startswith("http"):
                    links.add(match)
                else:
                    links.add(f"https://{match}")

        return list(links)

    # ---------------------------------------------------------------------
    # LOCATION INFERENCE
    # ---------------------------------------------------------------------

    def infer_location_from_text(self, text: str, fallback_location: str) -> Optional[str]:
        """
        Infer location from free text (Instagram bio, snippet, etc.)
        """
        common_locations = [
            "lagos", "abuja", "ibadan", "port harcourt", "ph",
            "lekki", "ikeja", "ajah", "yaba", "surulere",
            "ikorodu", "benin", "asaba", "uyo", "owerri"
        ]

        lowered = text.lower()
        for loc in common_locations:
            if loc in lowered:
                return loc.title()

        return fallback_location if fallback_location else None

    def enrich_with_google_maps(self, business_name: str, location: str) -> Optional[Dict]:
        """Enrich vendor with Google Maps data."""
        if not self.gmaps_client or not business_name:
            return None

        try:
            query = f"{business_name} {location}"
            result = self.gmaps_client.places(query=query)

            if result.get("results"):
                place = result["results"][0]
                geo = place.get("geometry", {}).get("location", {})

                return {
                    "address": place.get("formatted_address"),
                    "latitude": geo.get("lat"),
                    "longitude": geo.get("lng"),
                    "rating": place.get("rating"),
                    "place_id": place.get("place_id"),
                    "source": "google_maps"
                }
        except Exception as e:
            print(f"Google Maps enrichment error: {e}")

        return None

    # ---------------------------------------------------------------------
    # PAGE FETCHING
    # ---------------------------------------------------------------------

    def fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch page HTML safely."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; VendorFinderBot/1.0)"
            }
            response = requests.get(url, headers=headers, timeout=8)
            response.raise_for_status()
            return response.text
        except Exception:
            return None

    # ---------------------------------------------------------------------
    # CONFIDENCE & SCORING
    # ---------------------------------------------------------------------

    def calculate_confidence_score(self, vendor: Dict) -> float:
        """
        Score vendor confidence based on data richness.
        """
        score = 0.0

        if vendor["contacts"]["whatsapp"]:
            score += 0.3

        if vendor["social"]["instagram"]:
            score += 0.2

        if vendor["location"].get("resolved"):
            score += 0.3

        if vendor["location"].get("google_maps"):
            score += 0.2

        return round(min(score, 1.0), 2)

    # ---------------------------------------------------------------------
    # MAIN EXTRACTION METHOD
    # ---------------------------------------------------------------------

    def extract_vendor_info(self, search_result: Dict, user_location: str) -> Dict:
        """
        Extract, enrich, and score a vendor from a search result.
        """

        combined_text = f"{search_result.get('title', '')} {search_result.get('snippet', '')}"

        if self.is_job_post(combined_text):
            return {
                "confidence_score": 0.0,
                "discarded": True,
                "reason": "job_post_detected"
            }


        # ---------------- HARD FILTER ----------------
        url = search_result.get("link", "")
        if not self.is_potential_vendor_url(url):
            return {
                "confidence_score": 0.0,
                "discarded": True
            }

        vendor = {
            "identity": {
                "name": search_result.get("title", ""),
                "source": search_result.get("source", ""),
                "url": url
            },
            "contacts": {
                "whatsapp": [],
            },
            "social": {
                "instagram": [],
            },
            "location": {
                "text": None,
                "resolved": None,
                "google_maps": None
            },
            "confidence_score": 0.0,
            "evidence": []
        }

        snippet = search_result.get("snippet", "")
        inferred_location = None

        # ---------------- SNIPPET EXTRACTION ----------------
        vendor["contacts"]["whatsapp"] += self.extract_whatsapp_numbers(snippet)
        vendor["social"]["instagram"] += self.extract_instagram_links(snippet)

        inferred_location = self.infer_location_from_text(snippet, user_location)
        vendor["location"]["text"] = inferred_location

        # ---------------- PAGE EXTRACTION ----------------
        html = self.fetch_page_content(url)
        page_text = ""

        if html:
            soup = BeautifulSoup(html, "html.parser")
            page_text = soup.get_text(separator=" ")

            vendor["contacts"]["whatsapp"] += self.extract_whatsapp_numbers(page_text)

            # Filter Instagram to profiles only
            ig_links = self.extract_instagram_links(page_text)
            vendor["social"]["instagram"] += [
                link for link in ig_links if "/p/" not in link
            ]

            title = soup.find("title")
            if title:
                vendor["identity"]["name"] = title.get_text(strip=True)

            inferred_location = self.infer_location_from_text(
                page_text,
                inferred_location or user_location
            )
            vendor["location"]["text"] = inferred_location

        # ---------------- GOOGLE MAPS ENRICHMENT ----------------
        if vendor["identity"]["name"] and inferred_location:
            maps_data = self.enrich_with_google_maps(
                vendor["identity"]["name"],
                inferred_location
            )

            # 🔑 Always normalize & resolve address if lat/lng exists
            if maps_data:
                maps_data = self.enrich_google_maps_location(maps_data)

            vendor["location"]["google_maps"] = maps_data
            vendor["location"]["resolved"] = inferred_location

        # ---------------- CLEANUP ----------------
        vendor["contacts"]["whatsapp"] = list(set(vendor["contacts"]["whatsapp"]))
        vendor["social"]["instagram"] = list(set(vendor["social"]["instagram"]))

        # ---------------- SOFT CONTACT SIGNAL ----------------
        combined_text = f"{snippet} {page_text}".lower()
        if self.detect_soft_contact_signals(combined_text):
            vendor["confidence_score"] += 0.1
            vendor["evidence"].append("soft_contact_signal")

        # ---------------- CONFIDENCE SCORE ----------------
        vendor["confidence_score"] += self.calculate_confidence_score(vendor)

        return vendor


    def is_potential_vendor_url(self, url: str) -> bool:
        """
        Fast heuristic to exclude obvious non-vendor URLs.
        """
        if not url:
            return False

        # Exclude Instagram post URLs
        if "instagram.com/p/" in url:
            return False

        # Exclude news / blog content
        bad_keywords = ["news", "press", "job", "vacancy", "salary"]
        if any(word in url.lower() for word in bad_keywords):
            return False

        return True


    def detect_soft_contact_signals(self, text: str) -> bool:
        """
        Detect soft signals that suggest the page represents a real vendor,
        even if direct contact info is missing.
        """

        if not text:
            return False

        text = text.lower()

        signals = [
            "order now",
            "call us",
            "dm us",
            "whatsapp",
            "delivery",
            "we offer",
            "our services",
            "bookings",
            "price",
            "pricing",
            "available",
            "located in",
            "based in",
            "lagos",
            "abuja",
        ]

        score = sum(1 for s in signals if s in text)

        # Threshold: at least 2 soft signals
        return score >= 2

    def is_job_post(self, text: str) -> bool:
        text = text.lower()
        return any(word in text for word in JOB_KEYWORDS)


    def enrich_google_maps_location(self, location: dict) -> dict:
        if not location:
            return location

        # If we already have a full address, do nothing
        if location.get("address"):
            return location

        lat = location.get("latitude")
        lng = location.get("longitude")

        if not lat or not lng:
            return location

        try:
            results = self.gmaps.reverse_geocode((lat, lng))
            if results:
                location["address"] = results[0].get("formatted_address")
                location["source"] = "google_maps"
        except Exception:
            pass

        return location




# """Vendor extraction and data enrichment module."""
# import re
# import requests
# from bs4 import BeautifulSoup
# from typing import Dict, List, Optional
# import phonenumbers
# from phonenumbers import geocoder, carrier
# import googlemaps
# from config import Config


# class VendorExtractor:
#     """Extracts and enriches vendor information from search results."""
    
#     def __init__(self):
#         self.gmaps_client = None
#         if Config.GOOGLE_MAPS_API_KEY and Config.GOOGLE_MAPS_API_KEY != 'your_google_maps_api_key_here':
#             try:
#                 self.gmaps_client = googlemaps.Client(key=Config.GOOGLE_MAPS_API_KEY)
#             except Exception as e:
#                 print(f"Warning: Could not initialize Google Maps client: {e}")
    
#     def extract_whatsapp_numbers(self, text: str) -> List[str]:
#         """
#         Extract WhatsApp numbers from text.
        
#         Args:
#             text: Text to search for phone numbers
        
#         Returns:
#             List of phone numbers found
#         """
#         # Common WhatsApp number patterns
#         patterns = [
#             r'\+?\d{1,4}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # General phone pattern
#             r'wa\.me[/\+]?(\d+)',  # wa.me links
#             r'whatsapp[:\s]+(\+?\d+)',  # "whatsapp: +234..."
#             r'(\+?234[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{4})',  # Nigerian format
#         ]
        
#         numbers = set()
#         for pattern in patterns:
#             matches = re.findall(pattern, text, re.IGNORECASE)
#             for match in matches:
#                 if isinstance(match, tuple):
#                     match = match[0] if match[0] else match[1] if len(match) > 1 else ''
#                 if match:
#                     # Clean and validate
#                     cleaned = re.sub(r'[^\d+]', '', match)
#                     if len(cleaned) >= 10:  # Minimum phone number length
#                         numbers.add(cleaned)
        
#         return list(numbers)
    
#     def extract_instagram_links(self, text: str, base_url: str = '') -> List[str]:
#         """
#         Extract Instagram profile links from text.
        
#         Args:
#             text: Text to search
#             base_url: Base URL of the page (for relative links)
        
#         Returns:
#             List of Instagram URLs
#         """
#         instagram_links = set()
        
#         # Pattern for Instagram URLs
#         patterns = [
#             r'https?://(www\.)?instagram\.com/[\w.]+/?',
#             r'instagram\.com/[\w.]+/?',
#             r'@[\w.]+',  # Instagram handles
#         ]
        
#         for pattern in patterns:
#             matches = re.findall(pattern, text, re.IGNORECASE)
#             for match in matches:
#                 if isinstance(match, tuple):
#                     match = match[0] if match else ''
                
#                 if match.startswith('@'):
#                     instagram_links.add(f'https://instagram.com/{match[1:]}')
#                 elif match.startswith('http'):
#                     instagram_links.add(match)
#                 elif 'instagram.com' in match:
#                     instagram_links.add(f'https://{match}')
        
#         return list(instagram_links)
    
#     def get_location_from_maps(self, business_name: str, location: str) -> Optional[Dict]:
#         """
#         Get location information from Google Maps.
        
#         Args:
#             business_name: Name of the business
#             location: Location string (e.g., 'Lagos', 'Abuja')
        
#         Returns:
#             Dictionary with location information or None
#         """
#         if not self.gmaps_client:
#             return None
        
#         try:
#             query = f"{business_name} {location}"
#             places = self.gmaps_client.places(query=query)
            
#             if places.get('results') and len(places['results']) > 0:
#                 place = places['results'][0]
#                 geometry = place.get('geometry', {})
#                 location_data = geometry.get('location', {})
                
#                 return {
#                     'name': place.get('name', ''),
#                     'address': place.get('formatted_address', ''),
#                     'latitude': location_data.get('lat'),
#                     'longitude': location_data.get('lng'),
#                     'place_id': place.get('place_id', ''),
#                     'rating': place.get('rating'),
#                     'types': place.get('types', [])
#                 }
#         except Exception as e:
#             print(f"Error getting location from Google Maps: {e}")
        
#         return None
    
#     def fetch_page_content(self, url: str) -> Optional[str]:
#         """
#         Fetch and parse content from a URL.
        
#         Args:
#             url: URL to fetch
        
#         Returns:
#             Page content as string or None
#         """
#         try:
#             headers = {
#                 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
#             }
#             response = requests.get(url, headers=headers, timeout=10)
#             response.raise_for_status()
#             return response.text
#         except Exception as e:
#             print(f"Error fetching {url}: {e}")
#             return None
    
#     def extract_vendor_info(self, search_result: Dict, location: str) -> Dict:
#         """
#         Extract and enrich vendor information from a search result.
        
#         Args:
#             search_result: Search result dictionary
#             location: Location string for enrichment
        
#         Returns:
#             Enriched vendor information dictionary
#         """
#         vendor_info = {
#             'title': search_result.get('title', ''),
#             'url': search_result.get('link', ''),
#             'snippet': search_result.get('snippet', ''),
#             'source': search_result.get('source', ''),
#             'whatsapp_numbers': [],
#             'instagram_links': [],
#             'location': None,
#             'raw_content': ''
#         }
        
#         # Extract from snippet
#         snippet = search_result.get('snippet', '')
#         vendor_info['whatsapp_numbers'].extend(self.extract_whatsapp_numbers(snippet))
#         vendor_info['instagram_links'].extend(self.extract_instagram_links(snippet, vendor_info['url']))
        
#         # Try to fetch full page content
#         page_content = self.fetch_page_content(vendor_info['url'])
#         if page_content:
#             vendor_info['raw_content'] = page_content
            
#             # Extract from full content
#             vendor_info['whatsapp_numbers'].extend(self.extract_whatsapp_numbers(page_content))
#             vendor_info['instagram_links'].extend(self.extract_instagram_links(page_content, vendor_info['url']))
            
#             # Try to extract business name from page
#             try:
#                 soup = BeautifulSoup(page_content, 'html.parser')
#                 # Try to get title or h1
#                 title_tag = soup.find('title') or soup.find('h1')
#                 if title_tag:
#                     business_name = title_tag.get_text().strip()
#                     if business_name:
#                         vendor_info['location'] = self.get_location_from_maps(business_name, location)
#             except Exception as e:
#                 print(f"Error parsing HTML: {e}")
        
#         # Remove duplicates
#         vendor_info['whatsapp_numbers'] = list(set(vendor_info['whatsapp_numbers']))
#         vendor_info['instagram_links'] = list(set(vendor_info['instagram_links']))
        
#         return vendor_info


