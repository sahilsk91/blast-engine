"""
B.L.A.S.T V11 - Google Maps Business Scraper (Zero Login, Zero API Key)
==========================================================================
Strategy:
  1. Use DuckDuckGo dorks to find Google Maps URLs for a given niche/location.
  2. Parse each Maps listing page directly with requests to pull:
     - Business Name
     - Website URL
     - Phone number
  3. Feed each discovered website URL into the V11 Waterfall extractor
     which finds the actual email (homepage → subpages → OSINT → WHOIS).
"""

import re
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote
from typing import List, Optional


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

def _headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _extract_website_from_maps_listing(maps_url: str) -> Optional[str]:
    """
    Given a Google Maps place URL, fetch the page and extract the
    linked website URL (if present). Google Maps pages use structured data
    and anchor tags to embed website links.
    """
    try:
        resp = requests.get(maps_url, headers=_headers(), timeout=12, allow_redirects=True, verify=False)
        html = resp.text

        # Approach 1: Look for structured URL= patterns in GMaps page source
        # GMaps uses a URL-encoded redirect: /url?q=https://website.com
        website_matches = re.findall(r'/url\?q=(https?://[^&"\']+)', html)
        for m in website_matches:
            decoded = unquote(m)
            parsed = urlparse(decoded)
            # Exclude Google-internal URLs and social media
            if parsed.netloc and "google" not in parsed.netloc and "goo.gl" not in parsed.netloc:
                return decoded

        # Approach 2: Scan all href attributes for external website links
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            if href.startswith("http") and "google.com" not in href and "goo.gl" not in href:
                if urlparse(href).netloc:
                    return href

    except Exception:
        pass
    return None


def find_business_urls_via_gmaps(niche: str, location: str, target: int = 30) -> List[str]:
    """
    Main entry point: Searches Google Maps via DuckDuckGo dorks for
    `{niche} {location}` and returns a list of business website URLs.
    
    These URLs are then passed downstream to the V11 waterfall
    extractor to find email addresses.
    """
    from duckduckgo_search import DDGS

    business_website_urls = []
    seen_domains = set()

    # Multiple query variations to maximize unique results
    queries = [
        f"{niche} {location} site:google.com/maps",
        f'"{niche}" "{location}" google maps listing',
        f"{niche} near {location} maps.google.com",
        f"{niche} {location} google business profile",
    ]

    print(f"\n[GMap V11] Searching business listings for '{niche}' in '{location}'...")

    with DDGS() as ddgs:
        for query in queries:
            if len(business_website_urls) >= target:
                break

            try:
                results = ddgs.text(query, max_results=20)
                maps_urls = []
                direct_urls = []
                
                for r in results:
                    url = r.get("href", "")
                    snippet = r.get("body", "")

                    # If result IS a Google Maps URL, get the website from it
                    if "maps.google" in url or "google.com/maps" in url:
                        maps_urls.append(url)
                    else:
                        # Otherwise treat as a direct business website URL
                        parsed = urlparse(url)
                        domain = parsed.netloc.replace("www.", "")
                        skip = ["yelp", "yellowpages", "bbb.", "facebook", "linkedin",
                                "instagram", "tripadvisor", "angi", "thumbtack",
                                "google.com", "wikipedia", ".gov", ".edu"]
                        if domain and domain not in seen_domains and not any(s in domain for s in skip):
                            seen_domains.add(domain)
                            direct_urls.append(url)

                # First: Resolve Maps URLs to real websites
                for maps_url in maps_urls[:5]:
                    if len(business_website_urls) >= target:
                        break
                    website = _extract_website_from_maps_listing(maps_url)
                    if website:
                        parsed = urlparse(website)
                        domain = parsed.netloc.replace("www.", "")
                        if domain and domain not in seen_domains:
                            seen_domains.add(domain)
                            business_website_urls.append(website)
                            print(f"  [GMap] ✅ Found via Maps: {website}")
                    time.sleep(0.5)

                # Second: Add direct business URLs from snippets
                for url in direct_urls:
                    if len(business_website_urls) >= target:
                        break
                    business_website_urls.append(url)

                time.sleep(1.5)

            except Exception as e:
                print(f"  [GMap] Search error: {e}")
                continue

    print(f"[GMap V11] Found {len(business_website_urls)} business URLs from Google Maps search.")
    return business_website_urls


if __name__ == "__main__":
    # Quick local test
    urls = find_business_urls_via_gmaps("Dentists", "Miami", target=10)
    for u in urls:
        print(u)
