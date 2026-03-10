import time
from googlesearch import search
from duckduckgo_search import DDGS
from urllib.parse import urlparse
import warnings

warnings.filterwarnings("ignore", message=".*renamed.*")

# Global exclusion list - aggregators, social media, big corps
EXCLUDE_DOMAINS = [
    "yelp.com", "bbb.org", "yellowpages.com", "angi.com", "thumbtack.com",
    "homeadvisor.com", "houzz.com", "porch.com", "expertise.com",
    "forbes.com", "facebook.com", "instagram.com", "twitter.com",
    "linkedin.com", "mapquest.com", "superpages.com", "dexknows.com",
    "yellowbook.com", "manta.com", "local.yahoo.com", "bing.com",
    "google.com", "apple.com", "zillow.com", "realtor.com", "cnet.com",
    "wikipedia.org", "amazon.com", "ebay.com", "walmart.com", "target.com",
    "nextdoor.com", "chamberofcommerce.com", "alignable.com",
    "merchantcircle.com", "citysearch.com", "tripadvisor.com",
    "bestprosintown.com", "rankmetop.net", "bark.com", "trustpilot.com",
    "glassdoor.com", "indeed.com", "reddit.com", "quora.com",
    "youtube.com", "tiktok.com", "pinterest.com",
]

def _is_valid_business_url(url: str) -> bool:
    try:
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        for excluded in EXCLUDE_DOMAINS:
            if excluded in domain:
                return False

        # Also exclude .gov, .edu, and generic info sites
        if domain.endswith(".gov") or domain.endswith(".edu"):
            return False

        return True
    except:
        return False

# V6 God-Tier: True Stealth & Header Spoofing
from fake_useragent import UserAgent
import os

ua = UserAgent(os="windows", browsers=["chrome", "edge", "firefox"])

# Define V6 Proxy String here (User can inject BrightData/SmartProxy string when ready)
V6_PROXY = os.getenv("RESIDENTIAL_PROXY_URL", None)

def get_spoofed_headers():
    return {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/"
    }

def _build_exclusion_string() -> str:
    """Build a -site: exclusion string for the top aggregators."""
    top_excludes = [
        "yelp.com", "yellowpages.com", "angi.com", "thumbtack.com",
        "homeadvisor.com", "bbb.org", "houzz.com", "porch.com",
        "expertise.com", "mapquest.com", "facebook.com", "linkedin.com",
        "nextdoor.com", "reddit.com",
    ]
    return " ".join(f"-site:{d}" for d in top_excludes)


def generate_smart_queries(base_query: str) -> list[str]:
    """
    V9 Smart Query Generator:
    Instead of dorking INTO aggregator directories (self-defeating),
    we generate queries designed to find ACTUAL BUSINESS WEBSITES
    by using negative site operators and contact-page-specific terms.
    """
    excludes = _build_exclusion_string()

    # Strategy 1: Direct business website queries with aggregator exclusions
    direct_queries = [
        f"{base_query} {excludes}",
        f"{base_query} official website {excludes}",
        f"{base_query} contact us {excludes}",
        f'"{base_query}" "call us" OR "email us" {excludes}',
    ]

    # Strategy 2: Location-aware business queries
    # Try to detect if query already has a location
    parts = base_query.lower().split(" in ")
    if len(parts) == 2:
        niche = parts[0].strip()
        location = parts[1].strip()
        direct_queries.extend([
            f"{niche} {location} official site {excludes}",
            f"{niche} company {location} {excludes}",
            f"{niche} services {location} contact {excludes}",
            f"{niche} near {location} website {excludes}",
            f'"{niche}" "{location}" "phone" OR "email" {excludes}',
        ])
    else:
        # No location detected, use generic expansions
        prefixes = ["best", "top", "local", "professional", "licensed"]
        for p in prefixes[:3]:
            direct_queries.append(f"{p} {base_query} {excludes}")

    return list(dict.fromkeys(direct_queries))  # De-dup while preserving order


def get_search_results(query: str, target_count: int = 50) -> list[str]:
    """
    V9 Engine: Smart Query Generation + Aggregator Exclusion
    Now with Phase 3: Infinite Dorks via Gemini AI.
    """
    urls_found = set()
    valid_urls = []

    # Phase 3 AI Integration
    import os
    from dork_generator import generate_dorks
    from dotenv import load_dotenv
    load_dotenv()
    
    parts = query.lower().split(" in ")
    niche = parts[0].strip() if len(parts) > 1 else query
    location = parts[1].strip() if len(parts) > 1 else ""
    
    # Generate 10-50 highly specific queries based on target
    ai_dorks = generate_dorks(niche, location, max(10, min(50, target_count)))
    
    if ai_dorks:
        print(f"\n[Search Engine Phase 3] Successfully generated {len(ai_dorks)} AI-driven micro-queries.")
        excludes = _build_exclusion_string()
        queries = [f"{q} {excludes}" for q in ai_dorks]
    else:
        # Fallback to hardcoded queries if API fails or key is missing
        print("\n[Search Engine V9] AI Query Generation failed or missing key. Falling back to static V9 Generator.")
        queries = generate_smart_queries(query)
        
    print(f"\n[Search Engine V9] Firing {len(queries)} total queries.")
    
    if V6_PROXY:
        print("[Search Engine V9] -> Residential Proxy Pool Engaged.")
    else:
        print("[Search Engine V9] -> WARNING: Running on Local IP. Add RESIDENTIAL_PROXY_URL to .env for infinite scale.")

    # ---- NEW Primary: Official Google Custom Search API (Zero Ban) ----
    # If the user provides a Google API key, use the official API for perfect, unblockable results.
    google_api_key = os.getenv("GOOGLE_API_KEY")
    google_cx = os.getenv("GOOGLE_CX")
    
    if google_api_key and google_cx:
        import requests
        print(f"\n[Search Engine V9] Engaging Official Google Custom Search API (Zero-Ban Mode)...")
        for i, q in enumerate(queries):
            if len(valid_urls) >= target_count:
                break
                
            print(f"  [{i+1}/{len(queries)}] Google API: '{q[:50]}...'")
            try:
                # The API allows pagination (start=1, 11, etc) to get up to 100 results per query
                url = f"https://customsearch.googleapis.com/customsearch/v1?key={google_api_key}&cx={google_cx}&q={requests.utils.quote(q)}"
                r = requests.get(url, timeout=10)
                
                if r.status_code == 200:
                    data = r.json()
                    for item in data.get("items", []):
                        h = item.get("link", "")
                        if h.startswith("http") and _is_valid_business_url(h) and h not in urls_found:
                            urls_found.add(h)
                            valid_urls.append(h)
                            if len(valid_urls) >= target_count:
                                break
                else:
                    print(f"  -> Google API Error {r.status_code}: {r.text}")
                    if r.status_code == 429:
                        print("  -> Google API Rate Limit Reached (Free Tier). Down-shifting to DDG Web Scraper...")
                        break # Stop using API if quota is exhausted
                time.sleep(1) # Be entirely polite to the official API
            except Exception as e:
                print(f"  -> Google API Request Failed: {e}")
                continue
                
    if len(valid_urls) >= target_count:
        print(f"\n[Search Engine V9] Extracted {len(valid_urls)} unique business URLs.")
        return valid_urls

    # ---- Secondary: DuckDuckGo ----
    try:
        with DDGS(proxy=V6_PROXY, timeout=10) as ddgs:
            for i, q in enumerate(queries):
                if len(valid_urls) >= target_count:
                    break

                # Rotate UA for every query
                if hasattr(ddgs, 'headers'):
                    ddgs.headers.update(get_spoofed_headers())

                print(f"  [{i+1}/{len(queries)}] DDGS: '{q[:70]}...'")
                try:
                    # Capture stdout to suppress the annoying browser error if it happens
                    import sys, os
                    old_stdout = sys.stdout
                    sys.stdout = open(os.devnull, 'w')
                    try:
                        results = ddgs.text(q, max_results=25)
                    finally:
                        sys.stdout.close()
                        sys.stdout = old_stdout
                        
                    hits = 0
                    for r in results:
                        url = r.get("href")
                        if url and _is_valid_business_url(url) and url not in urls_found:
                            urls_found.add(url)
                            valid_urls.append(url)
                            hits += 1
                            if len(valid_urls) >= target_count:
                                break
                    if hits == 0:
                        raise Exception("0 Results - IP Banned")
                    time.sleep(1.5)
                except Exception as e:
                    print(f"  -> DDGS IP blocked or rate-limited.")
                    # DDG is IP blocking us, break out immediately to hit Brave
                    break
    except Exception as e:
        print(f"[Search Engine V9] DDG Global Error: {e}")

    # ---- Secondary: SearxNG Metasearch Fallback (Zero Blocking) ----
    if len(valid_urls) < target_count:
        print(f"\n[Search Engine V9] Valid URLs: {len(valid_urls)}/{target_count}. Engaging SearxNG (Meta-Search) Fallback...")
        import searxng_metasearch

        for i, q in enumerate(queries):
            if len(valid_urls) >= target_count:
                break
            
            print(f"  [{i+1}/{len(queries)}] SearxNG: '{q[:50]}...'")
            try:
                # We ask Searx to grab 20 results per query from Google/Bing
                searx_urls = searxng_metasearch.searx_search(q, 20)
                
                hits = 0
                for h in searx_urls:
                    if _is_valid_business_url(h) and h not in urls_found:
                        urls_found.add(h)
                        valid_urls.append(h)
                        hits += 1
                        if len(valid_urls) >= target_count:
                            break
                            
                time.sleep(1) # Be polite to public nodes
            except Exception as e:
                print(f"  -> SearxNG error: {e}.")
                continue

    # ---- Tertiary: Google Fallback ----
    if len(valid_urls) < target_count:
        print(f"\n[Search Engine V9] Valid URLs: {len(valid_urls)}/{target_count}. Engaging Google Fallback...")
        # For Google, use simpler queries (it handles complex operators worse via the library)
        google_queries = [
            query,
            f"{query} contact",
            f"{query} official website",
        ]
        for i, q in enumerate(google_queries):
            if len(valid_urls) >= target_count:
                break

            print(f"  [{i+1}/{len(google_queries)}] Google: '{q[:70]}...'")
            try:
                results = search(q, num_results=20, lang="en")
                for url in results:
                    if _is_valid_business_url(url) and url not in urls_found:
                        urls_found.add(url)
                        valid_urls.append(url)
                        if len(valid_urls) >= target_count:
                            break
                time.sleep(2)
            except Exception as e:
                print(f"  -> Google error: {e}.")
                break

    print(f"\n[Search Engine V9] Extracted {len(valid_urls)} unique business URLs.")
    return valid_urls

if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "plumbers in new york"
    print(get_search_results(query, 5))
