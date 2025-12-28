# test_cx.py
import requests
from config import Config

query = "site:instagram.com cake vendor"
url = "https://www.googleapis.com/customsearch/v1"
params = {
    "key": Config.GOOGLE_API_KEY,
    "cx": Config.GOOGLE_SEARCH_ENGINE_ID,  # This uses your 17-char ID
    "q": query,
    "num": 3
}

try:
    response = requests.get(url, params=params)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    if "items" in data:
        print(f"Success! Found {len(data['items'])} results.")
        for item in data["items"]:
            print(f"  - {item['title']}")
    else:
        print("No results found. Response:", data.get('error', {}).get('message', data))
except Exception as e:
    print(f"An error occurred: {e}")