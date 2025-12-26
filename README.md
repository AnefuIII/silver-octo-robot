# Local Vendor Finder AI Assistant

An AI-powered assistant for finding local vendors on Instagram and Twitter, enriched with location data, WhatsApp numbers, and social media links.

## Features

- 🔍 Search vendors on Instagram and Twitter using Google/Bing Search APIs
- 📍 Enrich vendor data with Google Maps location information
- 📱 Extract WhatsApp numbers from vendor profiles
- 🔗 Extract Instagram bio links and profile URLs
- 💾 Export results to JSON format

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Edit the `.env` file and add your API keys:

```env
# Google Custom Search API
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id_here

# Bing Search API
BING_API_KEY=your_bing_api_key_here
BING_SEARCH_ENDPOINT=https://api.bing.microsoft.com/v7.0/search

# Google Maps API
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
```

### 3. Get API Keys

- **Google Custom Search API**: 
  - Go to [Google Cloud Console](https://console.cloud.google.com/)
  - Enable Custom Search API
  - Create credentials and get API key
  - Create a Custom Search Engine at [Google Programmable Search](https://programmablesearchengine.google.com/)

- **Bing Search API**:
  - Go to [Azure Portal](https://portal.azure.com/)
  - Create a Bing Search v7 resource
  - Get your subscription key

- **Google Maps API**:
  - Go to [Google Cloud Console](https://console.cloud.google.com/)
  - Enable Places API
  - Create credentials and get API key

## Usage

### Basic Usage

```python
from vendor_finder import VendorFinder

finder = VendorFinder()

# Search for cake vendors in Lagos on Instagram
vendors = finder.find_vendors('cake', 'Lagos', 'instagram', max_results=10)

# Display results
print(finder.format_output(vendors))

# Save to JSON
finder.save_to_json(vendors, 'vendors.json')
```

### Run Examples

```bash
python vendor_finder.py
```

This will run example searches for:
- Cake vendors in Lagos on Instagram
- Plumber vendors in Abuja on Twitter

## Project Structure

```
vendor-finder/
├── .env                      # Environment variables (API keys)
├── config.py                 # Configuration management
├── search_engine.py          # Google/Bing search implementation
├── vendor_extractor.py       # Vendor data extraction and enrichment
├── vendor_finder.py          # Main application
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## How It Works

1. **Search**: Uses Google Custom Search API and Bing Search API to find vendors on Instagram/Twitter
2. **Extract**: Parses search results and web pages to extract:
   - WhatsApp numbers (various formats)
   - Instagram profile links
   - Business information
3. **Enrich**: Uses Google Maps API to get location data for vendors
4. **Export**: Saves enriched vendor data to JSON files

## Notes

- Rate limiting is implemented to respect API quotas
- The application handles missing API keys gracefully
- Some features may be limited if certain APIs are not configured
- Results depend on what's publicly indexed by search engines

## License

MIT


