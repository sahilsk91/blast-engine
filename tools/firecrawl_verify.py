import requests
import sys

print("Testing Firecrawl Local Instance...")
url = "http://localhost:3002/v1/scrape"

# We just do a basic test to see if the endpoint is up and can scrape a simple page
payload = {
    "url": "https://example.com",
    "formats": ["markdown"]
}

try:
    response = requests.post(url, json=payload, timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"Firecrawl scrape success! Extracted {len(data.get('data', {}).get('markdown', ''))} chars of markdown.")
    else:
        print(f"Firecrawl returned status code: {response.status_code}")
        print(response.text)
        sys.exit(1)
except Exception as e:
    print(f"Firecrawl connection failed: {e}")
    sys.exit(1)

print("\nLink Phase Firecrawl Verification Complete.")
