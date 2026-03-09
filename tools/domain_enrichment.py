import os
import requests
from urllib.parse import urlparse

# Optional B2B Database Enrichment (V7 Fallback)
# If a company's website physically hides their emails, we can query massive databases.

def lookup_domain_emails(url: str, limit: int = 3) -> list[dict]:
    """
    Takes a URL, extracts the domain, and searches Hunter.io or Snov.io 
    to find highly verified employee/founder emails that are not listed on the website.
    """
    hunter_key = os.getenv("HUNTER_API_KEY")
    
    if not hunter_key:
        return []
        
    try:
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
            
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
        else:
            print(f"  -> [V7 Error] Hunter API returned {resp.status_code}")
            return []
            
    except Exception as e:
        print(f"  -> [V7 Error] Domain Enrichment failed: {e}")
        return []

if __name__ == "__main__":
    # Test script locally
    # export HUNTER_API_KEY="your_key"
    print(lookup_domain_emails("https://stripe.com"))
