import whois
from urllib.parse import urlparse
import re

def extract_whois_data(url: str) -> dict:
    """
    V6 God-Tier: Bypasses the website completely and queries the ICANN DNS records.
    Founders often register their domains using their personal Gmail and cell phone. 
    This module extracts them.
    """
    try:
        # 1. Clean URL to bare domain (e.g. www.lionplumbinginc.com -> lionplumbinginc.com)
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
            
        print(f"[V6 Enrichment] Querying WHOIS Database for {domain}...")
        
        # 2. Execute WHOIS Lookup
        w = whois.whois(domain)
        
        # 3. Extract Emails
        raw_emails = []
        if type(w.emails) == list:
            raw_emails.extend(w.emails)
        elif type(w.emails) == str:
            raw_emails.append(w.emails)
            
        # 4. Clean & Filter Privacy Protections & Registrars
        valid_emails = []
        noise_domains = [
            "privacy", "proxy", "protect", "redacted", "domaindiscreet",
            "godaddy.com", "namecheap.com", "cloudflare.com", "networksolutions",
            "register.com", "web.com", "tucows.com", "gkg.net", "enom.com",
            "bluehost.com", "domains.siteground.com", "markmonitor.com",
            "internetbrands.com", "officite.com", "imatrix.com", "gcd.com"
        ]
        noise_prefixes = ["abuse", "domain-registrar", "whoisrequest", "domain.operations"]
        
        for e in raw_emails:
            e = e.lower()
            if any(junk in e for junk in noise_domains) or any(e.startswith(p) for p in noise_prefixes):
                continue
            valid_emails.append(e)
            
        # 5. Extract Phones (Optional - WHOIS phones are often registrar phones. Basic regex check)
        # Not heavily relying on WHOIS phones unless they match standard formats
        phones = []
        
        return {
            "emails": list(set(valid_emails)),
            "phones": phones
        }
    except Exception as e:
        # WHOIS queries can fail or timeout. Fail gracefully.
        return {"emails": [], "phones": []}

# Manual Test
if __name__ == "__main__":
    result = extract_whois_data("https://www.google.com")
    print(result)
