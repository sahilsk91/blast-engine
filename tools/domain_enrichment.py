import os
import requests
from urllib.parse import urlparse

# Optional B2B Database Enrichment (V7 Fallback)
# If a company's website physically hides their emails, we can query massive databases.

def lookup_domain_emails(url: str, limit: int = 3) -> list[dict]:
    """
    Takes a URL, extracts the domain, and searches Hunter.io or Snov.io.
    If no API key is present, it uses 100% Free OSINT Search Engine Dorking 
    to extract emails by searching the entire web for "@{domain}".
    """
    try:
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
    except:
        return []

    hunter_key = os.getenv("HUNTER_API_KEY")
    
    if hunter_key:
        try:
            print(f"  -> [V7 B2B Enrichment] Hitting Hunter.io for {domain}...")
            endpoint = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={hunter_key}&limit={limit}&type=personal"
            resp = requests.get(endpoint, timeout=15)
            
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                emails = data.get("emails", [])
                
                enrichments = []
                for e in emails:
                    val = e.get("value")
                    position = e.get("position") or "Employee"
                    if val:
                        enrichments.append({"email": val, "position": position})
                
                if enrichments:
                    print(f"  -> [V7 SUCCESS] Hunter.io returned {len(enrichments)} hidden human emails for {domain}!")
                    return enrichments
        except Exception as e:
            print(f"  -> [V7 B2B Enrichment] Hunter failed: {e}")

    # 100% FREE OSINT FALLBACK ENGINE (No API Key Required)
    print(f"  -> [V7 Free OSINT] Commencing Deep Dork Search for @{domain}...")
    try:
        from duckduckgo_search import DDGS
        import re
        
        dork_query = f'"@{domain}"'
        results_text = ""
        
        with DDGS() as ddgs:
            for r in ddgs.text(dork_query, max_results=20):
                results_text += r.get("body", "") + " " + r.get("title", "") + " "
                
        # Scrape precisely for the domain
        found_emails = list(set(re.findall(f'[a-zA-Z0-9_.+-]+@{domain}', results_text.lower())))
        
        enrichments = []
        for e in found_emails:
            # To simulate B2B databases, we aggressively seek *personal* names, skipping generic info@
            generic = ["info@", "sales@", "contact@", "hello@", "support@", "admin@", "billing@", "jobs@"]
            if not any(g in e for g in generic):
                enrichments.append({"email": e, "position": "Found via V7 Free OSINT Dorking"})
                
        if enrichments:
            print(f"  -> [V7 OSINT SUCCESS] Bypassed API! Extracted {len(enrichments)} deeply hidden human emails from public footprints!")
            
        return enrichments
        
    except Exception as e:
        print(f"  -> [V7 Free OSINT] Search Engine Error: {e}")
        return []

if __name__ == "__main__":
    # Test script locally
    # export HUNTER_API_KEY="your_key"
    print(lookup_domain_emails("https://stripe.com"))
