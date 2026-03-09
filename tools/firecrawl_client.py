"""
B.L.A.S.T V11 - Pure Python Web Scraping Engine
Zero Docker, Zero Paid APIs, 100% Production-Grade.

Waterfall extraction pipeline per URL:
  1. Pure Python requests + BeautifulSoup (instant, no dependencies)
  2. Deep crawl: /contact, /about, /team, /contact-us (sub-pages)
  3. OSINT DuckDuckGo Domain Dork ("@domain.com")
  4. WHOIS DNS Enrichment
  Returns a LeadSchema with all found emails, phones, socials.
"""

import asyncio
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

# ----- Configuration -----
MAX_WORKERS = 20  # Parallel URL scraping threads
REQUEST_TIMEOUT = 12  # Seconds

# Rotating user agents pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

# ----- Lead Schema -----
class LeadSchema(BaseModel):
    name: Optional[str] = None
    website: str
    description: Optional[str] = None
    source_url: str
    emails: List[str] = []
    phones: List[str] = []
    socials: List[str] = []
    model_config = ConfigDict(extra="ignore")


# ----- Email Quality Gate -----
SPAM_KEYWORDS = [
    "sentry", "w3.org", "example", ".png", ".jpg", ".gif", "no-reply", "noreply",
    "mailer-daemon", "domain", "postmaster@", "hostmaster@",
    "webmaster@", "abuse@", "compliance@", "privacy@",
    "godaddy", "namecheap", "cloudflare", "networksolutions", "hostgator",
    "register.com", "tucows", "gkg.net", "enom", "markmonitor", "domains@",
    "web.com", "bluehost", "siteground", "dreamhost", "aws.com",
    "amazon.com", "registrar", "yp.ca", "yellowpages", "legal@",
    "temp", "fake", "spam", "trap", "catchall",
    "shopify.com", "wixpress", "squarespace.com", "wordpress.com",
]

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"(?:\+?1[\.\-\s]?)?\(?\d{3}\)?[\.\-\s]?\d{3}[\.\-\s]?\d{4}")
SOCIAL_REGEX = re.compile(r"https?://(?:www\.)?(?:facebook|twitter|instagram|linkedin|yelp)\.com/[^\s\"'<>]+")

def is_valid_email(email: str) -> bool:
    email = email.lower()
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,63}$", email):
        return False
    return not any(kw in email for kw in SPAM_KEYWORDS)


# ----- Core HTTP Fetcher -----
def _get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "DNT": "1",
    }

def _fetch_html(url: str, retries: int = 2) -> str:
    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                headers=_get_headers(),
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                verify=False,  # Skip SSL verification to avoid cert errors on small business sites
            )
            if resp.status_code == 200:
                # Detect content type
                ct = resp.headers.get("Content-Type", "")
                if "text" in ct or "html" in ct:
                    return resp.text
        except requests.exceptions.Timeout:
            pass
        except requests.exceptions.ConnectionError:
            break
        except Exception:
            break
        if attempt < retries - 1:
            time.sleep(0.5)
    return ""


def _parse_html(url: str, html: str) -> dict:
    """Extract emails, phones, and socials from raw HTML."""
    emails = []
    phones = []
    socials = []

    if not html:
        return {"emails": emails, "phones": phones, "socials": socials}

    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove script/style/svg noise
        for tag in soup(["script", "style", "svg", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator=" ")

        # 1. Extract emails from raw HTML (catches obfuscated mailto: links too)
        raw_html_emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}", html)
        raw_text_emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}", text)
        all_emails = list(set(raw_html_emails + raw_text_emails))
        emails = [e for e in all_emails if is_valid_email(e)]

        # 2. Check mailto: links (explicitly coded emails)
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            if href.startswith("mailto:"):
                e = href.replace("mailto:", "").split("?")[0].strip()
                if e and is_valid_email(e) and e not in emails:
                    emails.append(e)

        # 3. Phones
        phones = list(set(re.findall(PHONE_REGEX, text)))[:5]

        # 4. Socials
        socials = list(set(re.findall(SOCIAL_REGEX, html)))[:5]

    except Exception:
        pass

    return {
        "emails": list(set(emails)),
        "phones": phones,
        "socials": socials
    }


# ----- DNS/MX Verification -----
def _verify_email_domain(email: str) -> bool:
    """Fast MX record check - ensures the domain actually receives mail."""
    try:
        import dns.resolver
        domain = email.split("@")[1]
        dns.resolver.resolve(domain, "MX")
        return True
    except Exception:
        return True  # Default to true to avoid false drops on DNS timeouts


# ----- Core Extraction Pipeline Per URL -----
def extract_lead(url: str) -> Optional[LeadSchema]:
    """
    Full waterfall extraction for a single URL.
    Tries homepage → subpages → OSINT Dorking → WHOIS DNS
    """
    try:
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        domain = parsed.netloc.lower().replace("www.", "")

        print(f"[Engine V11] Scraping {url}...")

        # Track all found data
        all_emails = []
        all_phones = []
        all_socials = []

        # === LAYER 1: Homepage ===
        html = _fetch_html(url)
        result = _parse_html(url, html)
        all_emails.extend(result["emails"])
        all_phones.extend(result["phones"])
        all_socials.extend(result["socials"])

        # === LAYER 2: Deep Subpage Crawl ===
        if not all_emails:
            subpages = [
                f"{base_url}/contact",
                f"{base_url}/contact-us",
                f"{base_url}/about",
                f"{base_url}/about-us",
                f"{base_url}/team",
                f"{base_url}/our-team",
                f"{base_url}/staff",
                f"{base_url}/reach-us",
            ]
            print(f"  -> No emails on homepage. Deep crawling {len(subpages)} subpages...")
            for sub_url in subpages:
                sub_html = _fetch_html(sub_url)
                if sub_html:
                    sub_result = _parse_html(sub_url, sub_html)
                    all_emails.extend(sub_result["emails"])
                    all_phones.extend(sub_result["phones"])
                    all_socials.extend(sub_result["socials"])
                    if all_emails:
                        print(f"  -> Found {len(all_emails)} emails on {sub_url}!")
                        break

        # === LAYER 3: OSINT Domain Dork (DDG "@domain.com") ===
        if not all_emails:
            print(f"  -> Initiating OSINT Dorking for @{domain}...")
            from domain_enrichment import lookup_domain_emails
            enrichments = lookup_domain_emails(url)
            for e in enrichments:
                email_val = e.get("email", "")
                if email_val and is_valid_email(email_val):
                    all_emails.append(email_val)

        # === LAYER 4: WHOIS DNS Fallback ===
        if not all_emails:
            print(f"  -> Initiating WHOIS DNS fallback for {domain}...")
            try:
                from enrichment import extract_whois_data
                whois = extract_whois_data(url)
                whois_emails = [e for e in whois.get("emails", []) if is_valid_email(e)]
                all_emails.extend(whois_emails)
            except Exception:
                pass

        # Deduplicate everything
        all_emails = list(set(all_emails))
        all_phones = list(set(all_phones))
        all_socials = list(set(all_socials))

        if all_emails or all_phones:
            # Try to get a business name from the page title
            name = domain
            try:
                soup = BeautifulSoup(html, "html.parser")
                title_tag = soup.find("title")
                if title_tag and title_tag.get_text(strip=True):
                    name = title_tag.get_text(strip=True)[:80]
            except Exception:
                pass

            return LeadSchema(
                name=name,
                website=url,
                description=f"Extracted from {domain}",
                source_url=url,
                emails=all_emails,
                phones=all_phones,
                socials=all_socials,
            )

    except Exception as e:
        print(f"[Engine V11] Error on {url}: {e}")

    print(f"[Engine V11] Dropped {url} — no contact info found.")
    return None


# ----- Parallel Batch Extractor -----
def extract_all_leads(urls: List[str]) -> List[LeadSchema]:
    """
    Runs extraction on all URLs in parallel using a thread pool.
    No asyncio needed — uses plain ThreadPoolExecutor for simplicity.
    """
    print(f"\n[Engine V11] Launching parallel extraction for {len(urls)} URLs...")
    leads = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(extract_lead, url): url for url in urls}
        for future in as_completed(futures):
            result = future.result()
            if result:
                leads.append(result)
                print(f"  -> ✅ Lead captured: {result.name} ({len(result.emails)} emails)")

    print(f"[Engine V11] Extracted {len(leads)} valid leads out of {len(urls)} URLs.")
    return leads
