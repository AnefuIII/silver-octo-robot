"""
Main vendor finder application (Agent-ready orchestrator).

Responsible for:
- Coordinating search + extraction
- Ranking vendors intelligently
- Explaining results
- Producing clean, user-facing output
"""

import json
from typing import List, Dict
from search_engine import SearchEngine
from vendor_extractor import VendorExtractor
from config import Config
from llm_reasoner import LLMReasoner


TRADE_SERVICES = [
    "plumber", "electrician", "mechanic", "technician",
    "carpenter", "welder", "installer", "repair",
    "cleaner", "handyman", "maintenance"
]

VISUAL_SERVICES = [
    "cake", "bakery", "makeup", "photography",
    "fashion", "decor", "event", "catering", "florist"
]


def classify_service(service: str) -> str:
    service = service.lower()
    if any(word in service for word in TRADE_SERVICES):
        return "trade"
    if any(word in service for word in VISUAL_SERVICES):
        return "visual"
    return "general"



class VendorFinder:
    """Agent-style orchestrator for vendor discovery."""

    def __init__(self):
        self.search_engine = SearchEngine()
        self.extractor = VendorExtractor()
        self.reasoner = LLMReasoner()

    # ------------------------------------------------------------------
    # CORE AGENT FLOW
    # ---------------------------------------------------------------
    def find_vendors(
        self,
        service: str,
        location: str,
        platform: str = "instagram",
        max_results: int = 10,
        min_confidence: float = 0.3
    ) -> Dict:
        """
        Autonomous vendor discovery agent with:
        1. Vendor intent filtering
        2. LLM vendor validation
        3. Contact enrichment
        4. Platform-aware ranking
        """
        service_type = classify_service(service)

        if service_type == "trade":
            effective_min_confidence = 0.2
        elif service_type == "visual":
            effective_min_confidence = min_confidence
        else:
            effective_min_confidence = min_confidence


        attempt = 0
        max_attempts = 2  # HARD SAFETY LIMIT

        current_platform = platform
        current_location = location
        current_min_confidence = min_confidence

        final_reasoning = []
        ranked_vendors: List[Dict] = []

        while attempt < max_attempts:
            attempt += 1
            print(f"\n🔎 Attempt {attempt}: '{service}' in '{current_location}' on {current_platform}")
            
            # ---------------- PLATFORM OVERRIDE ----------------
            if service_type == "visual":
                current_platform = "instagram"

            # ---------------- SEARCH ----------------
            search_results = self.search_engine.search_vendors(
                service=service,
                location=current_location,
                platform=current_platform
            )

            if not search_results:
                break

            enriched_vendors: List[Dict] = []

            # ---------------- EXTRACTION ----------------
            for result in search_results[: max_results * 3]:
                vendor = self.extractor.extract_vendor_info(result, current_location)

                # Improvement #1: Hard discard non-vendors
                if vendor.get("discarded"):
                    continue

                # Confidence gate
                if vendor["confidence_score"] < effective_min_confidence:
                    continue

                # Improvement #2: LLM vendor intent validation
                if not self.reasoner.is_actual_vendor(service, vendor):
                    continue

                enriched_vendors.append(vendor)

                if len(enriched_vendors) >= max_results:
                    break

            if not enriched_vendors:
                break

            # ---------------- DETERMINISTIC RANKING ----------------
            ranked_vendors = self.rank_vendors(enriched_vendors)

            # ---------------- LLM RE-RANK ----------------
            if len(ranked_vendors) > 1:
                rerank = self.reasoner.rerank_vendors(service, ranked_vendors)

                valid_ids = [
                    i for i in rerank.get("ordered_vendor_ids", [])
                    if 0 <= i < len(ranked_vendors)
                ]

                if valid_ids:
                    ranked_vendors = [ranked_vendors[i] for i in valid_ids]

                if rerank.get("reasoning"):
                    final_reasoning.append(rerank["reasoning"])

            # ---------------- LLM ANALYSIS ----------------
            analysis = self.reasoner.analyze_results(
                service,
                current_location,
                ranked_vendors
            )

            # ---------------- LLM AUTONOMY ----------------
            decision = self.reasoner.decide_next_search(
                service,
                current_location,
                current_platform,
                ranked_vendors
            )

            if decision.get("action") == "STOP":
                return {
                    "vendors": ranked_vendors,
                    "analysis": analysis,
                    "agent_reasoning": final_reasoning
                }

            # ---------------- APPLY DECISION ----------------
            if decision["action"] == "EXPAND_LOCATION":
                current_location = f"{current_location} nearby"
                final_reasoning.append("Expanded search location.")

            elif decision["action"] == "TRY_ANOTHER_PLATFORM":
                if service_type == "visual":
                    current_platform = "instagram"
                else:
                    current_platform = "twitter" if current_platform == "instagram" else "instagram"

                final_reasoning.append(f"Switched platform to {current_platform}.")

            elif decision["action"] == "RELAX_CONFIDENCE":
                current_min_confidence = max(0.1, current_min_confidence - 0.1)
                final_reasoning.append("Relaxed confidence threshold.")

        # ---------------- FALLBACK ----------------
        return {
            "vendors": ranked_vendors,
            "analysis": {
                "explanation": "Search completed but results were limited or low confidence.",
                "result_quality": "weak",
                "clarifying_question": "Would you like to broaden the location or try another service?"
            },
            "agent_reasoning": final_reasoning
        }


    # ------------------------------------------------------------------
    # RANKING LOGIC
    # ------------------------------------------------------------------

    def rank_vendors(self, vendors: List[Dict]) -> List[Dict]:
        """
        Rank vendors based on confidence, contact richness, and location strength.
        """

        def ranking_key(vendor: Dict):
            contact_score = 1 if vendor["contacts"]["whatsapp"] else 0
            social_score = 1 if vendor["social"]["instagram"] else 0
            location_score = 1 if vendor["location"].get("google_maps") else 0

            return (
                vendor["confidence_score"],
                contact_score,
                social_score,
                location_score,
            )

        vendors.sort(key=ranking_key, reverse=True)
        return vendors

    # ------------------------------------------------------------------
    # OUTPUT FORMATTING (USER-FACING)
    # ------------------------------------------------------------------

    def format_output(self, vendors: List[Dict]) -> str:
        """Human-readable output (CLI / logs)."""

        if not vendors:
            return "\nNo qualified vendors found.\n"

        lines = []
        lines.append("=" * 90)
        lines.append(f"✅ FOUND {len(vendors)} QUALIFIED VENDORS")
        lines.append("=" * 90)

        for idx, vendor in enumerate(vendors, 1):
            identity = vendor["identity"]
            contacts = vendor["contacts"]
            social = vendor["social"]
            location = vendor["location"]

            lines.append(f"\nVendor #{idx}")
            lines.append("-" * 40)
            lines.append(f"Name: {identity.get('name', 'N/A')}")
            lines.append(f"Source: {identity.get('source')}")
            lines.append(f"URL: {identity.get('url')}")
            lines.append(f"Confidence Score: {vendor['confidence_score']}")

            if contacts["whatsapp"]:
                lines.append(f"WhatsApp: {', '.join(contacts['whatsapp'])}")
            else:
                lines.append("WhatsApp: Not found")

            if social["instagram"]:
                lines.append(f"Instagram: {', '.join(social['instagram'])}")
            else:
                lines.append("Instagram: Not found")

            if location.get("resolved"):
                lines.append(f"Location: {location['resolved']}")
            if location.get("google_maps"):
                gm = location["google_maps"]
                lines.append(f"Address: {gm.get('address')}")
                if gm.get("rating"):
                    lines.append(f"Rating: {gm.get('rating')}")

        lines.append("\n")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # DATA EXPORT
    # ------------------------------------------------------------------

    def save_to_json(self, vendors: List[Dict], filename: str):
        """Persist vendor results to JSON."""

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(vendors, f, indent=2, ensure_ascii=False)

        print(f"💾 Results saved to {filename}")


# ----------------------------------------------------------------------
# CLI ENTRY POINT
# ----------------------------------------------------------------------

def main():
    """CLI entry point."""

    missing_keys = Config.validate_config()
    if missing_keys:
        print("⚠️ Missing API keys:")
        for key in missing_keys:
            print(f"   - {key}")
        print("The app will run with limited functionality.\n")

    finder = VendorFinder()

    print("\n🤖 Local Vendor Finder AI Assistant")
    print("=" * 90)

    result1 = finder.find_vendors(
        service="cake",
        location="Lagos",
        platform="instagram",
        max_results=5
    )

    vendors1 = result1["vendors"]

    print(finder.format_output(vendors1))
    finder.save_to_json(vendors1, "cake_lagos_vendors.json")


    result2 = finder.find_vendors(
        service="plumber",
        location="Abuja",
        platform="twitter",
        max_results=5
    )

    vendors2 = result2["vendors"]

    print(finder.format_output(vendors2))
    finder.save_to_json(vendors2, "plumber_abuja_vendors.json")



if __name__ == "__main__":
    main()


# """Main vendor finder application."""
# import json
# from typing import List, Dict
# from search_engine import SearchEngine
# from vendor_extractor import VendorExtractor
# from config import Config


# class VendorFinder:
#     """Main class for finding and enriching vendor information."""
    
#     def __init__(self):
#         self.search_engine = SearchEngine()
#         self.extractor = VendorExtractor()
    
#     def find_vendors(self, service: str, location: str, platform: str = 'instagram', max_results: int = 10) -> List[Dict]:
#         """
#         Find vendors for a given service and location.
        
#         Args:
#             service: Service/product name (e.g., 'cake', 'plumber')
#             location: Location (e.g., 'Lagos', 'Abuja')
#             platform: Platform to search ('instagram' or 'twitter')
#             max_results: Maximum number of results to return
        
#         Returns:
#             List of enriched vendor information dictionaries
#         """
#         print(f"Searching for '{service}' vendors in '{location}' on {platform}...")
        
#         # Search for vendors
#         search_results = self.search_engine.search_vendors(service, location, platform)
        
#         if not search_results:
#             print("No search results found.")
#             return []
        
#         print(f"Found {len(search_results)} search results. Extracting vendor information...")
        
#         # Extract and enrich vendor information
#         vendors = []
#         for i, result in enumerate(search_results[:max_results], 1):
#             print(f"Processing result {i}/{min(len(search_results), max_results)}...")
#             vendor_info = self.extractor.extract_vendor_info(result, location)
#             vendors.append(vendor_info)
        
#         return vendors
    
#     def format_output(self, vendors: List[Dict]) -> str:
#         """
#         Format vendor information for display.
        
#         Args:
#             vendors: List of vendor information dictionaries
        
#         Returns:
#             Formatted string
#         """
#         output = []
#         output.append(f"\n{'='*80}")
#         output.append(f"Found {len(vendors)} vendors")
#         output.append(f"{'='*80}\n")
        
#         for i, vendor in enumerate(vendors, 1):
#             output.append(f"\nVendor {i}:")
#             output.append(f"  Title: {vendor.get('title', 'N/A')}")
#             output.append(f"  URL: {vendor.get('url', 'N/A')}")
#             output.append(f"  Source: {vendor.get('source', 'N/A')}")
            
#             if vendor.get('whatsapp_numbers'):
#                 output.append(f"  WhatsApp Numbers: {', '.join(vendor['whatsapp_numbers'])}")
#             else:
#                 output.append(f"  WhatsApp Numbers: None found")
            
#             if vendor.get('instagram_links'):
#                 output.append(f"  Instagram Links: {', '.join(vendor['instagram_links'])}")
#             else:
#                 output.append(f"  Instagram Links: None found")
            
#             if vendor.get('location'):
#                 loc = vendor['location']
#                 output.append(f"  Location: {loc.get('name', 'N/A')}")
#                 output.append(f"  Address: {loc.get('address', 'N/A')}")
#                 if loc.get('rating'):
#                     output.append(f"  Rating: {loc['rating']}")
#             else:
#                 output.append(f"  Location: Not found")
            
#             output.append("")
        
#         return "\n".join(output)
    
#     def save_to_json(self, vendors: List[Dict], filename: str = 'vendors.json'):
#         """
#         Save vendor information to JSON file.
        
#         Args:
#             vendors: List of vendor information dictionaries
#             filename: Output filename
#         """
#         # Remove raw_content for cleaner JSON
#         clean_vendors = []
#         for vendor in vendors:
#             clean_vendor = {k: v for k, v in vendor.items() if k != 'raw_content'}
#             clean_vendors.append(clean_vendor)
        
#         with open(filename, 'w', encoding='utf-8') as f:
#             json.dump(clean_vendors, f, indent=2, ensure_ascii=False)
        
#         print(f"\nVendor information saved to {filename}")


# def main():
#     """Main entry point for the application."""
#     # Validate configuration
#     missing_keys = Config.validate_config()
#     if missing_keys:
#         print("Warning: The following API keys are not configured:")
#         for key in missing_keys:
#             print(f"  - {key}")
#         print("\nPlease update your .env file with valid API keys.")
#         print("The application will continue but may have limited functionality.\n")
    
#     # Initialize vendor finder
#     finder = VendorFinder()
    
#     # Example usage
#     print("Local Vendor Finder AI Assistant")
#     print("=" * 80)
    
#     # Example 1: Search for cake vendors in Lagos on Instagram
#     print("\nExample 1: Searching for cake vendors in Lagos on Instagram")
#     vendors1 = finder.find_vendors('cake', 'Lagos', 'instagram', max_results=5)
#     print(finder.format_output(vendors1))
#     finder.save_to_json(vendors1, 'cake_lagos_vendors.json')
    
#     # Example 2: Search for plumber vendors in Abuja on Twitter
#     print("\n\nExample 2: Searching for plumber vendors in Abuja on Twitter")
#     vendors2 = finder.find_vendors('plumber', 'Abuja', 'twitter', max_results=5)
#     print(finder.format_output(vendors2))
#     finder.save_to_json(vendors2, 'plumber_abuja_vendors.json')


# if __name__ == '__main__':
#     main()


