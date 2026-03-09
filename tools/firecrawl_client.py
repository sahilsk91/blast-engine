import asyncio
import aiohttp
import re
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from urllib.parse import urlparse
from enrichment import extract_whois_data
from ocr_vision import extract_emails_from_images

FIRECRAWL_URL = "http://localhost:3002/v1/scrape"
MAX_CONCURRENT_EXTRACTIONS = 20 # Upgraded for V5 Omni-Scale Engine

class LeadSchema(BaseModel):
    name: Optional[str] = None
    website: str
    description: Optional[str] = None
    source_url: str
    emails: List[str] = []
    phones: List[str] = []
    socials: List[str] = []

    model_config = ConfigDict(extra="ignore")

def is_valid_email(email: str) -> bool:
    email = email.lower()
    
    # 1. TLD & Format Enforcement
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        return False
        
    # 2. Aggressive Anti-Spam / Anti-Registrar Filter
    noise = [
        "sentry", "w3.org", "example", ".png", ".jpg", ".gif", "no-reply", "noreply", 
        "mailer-daemon", "test", "domain", "admin@", "postmaster@", "hostmaster@",
        "webmaster@", "abuse@", "support@", "billing@", "compliance@", "privacy@",
        "godaddy", "namecheap", "cloudflare", "networksolutions", "hostgator",
        "register.com", "tucows", "gkg.net", "enom", "markmonitor", "domains@",
        "web.com", "bluehost", "siteground", "dreamhost", "aws.com",
        "amazon.com", "registrar", "yp.ca", "yellowpages", "legal@", 
        "123", "temp", "fake", "spam", "trap", "catchall",
        "shopify", "wix", "squarespace", "wordpress", ".gov", ".edu",
        "wixpress", "customer"
    ]
    if any(n in email for n in noise):
        return False
        
    return True

def parse_markdown_to_lead(url: str, md: str) -> LeadSchema:
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    phone_pattern = r'(?:\+?1[-.\s]?)?\(?[2-9][0-8][0-9]\)?[-.\s]?[2-9][0-9]{2}[-.\s]?[0-9]{4}'
    social_pattern = r'https?://(?:www\.)?(?:facebook|twitter|instagram|linkedin|yelp)\.com/[^\s"]+'
    
    emails = list(set(re.findall(email_pattern, md)))
    phones = list(set(re.findall(phone_pattern, md)))
    socials = list(set(re.findall(social_pattern, md)))
    
    raw_emails = [e for e in emails if is_valid_email(e)]
    
    from verify_email import verify_email
    clean_emails = [e for e in raw_emails if verify_email(e)["valid"]]
    
    domain = urlparse(url).netloc
        
    return LeadSchema(
        name=domain,
        website=url,
        description="Scraped via V4 Deep Firecrawl",
        source_url=url,
        emails=clean_emails,
        phones=phones,
        socials=socials
    )

async def _fetch_markdown(url: str, session: aiohttp.ClientSession) -> str:
    payload = {"url": url, "formats": ["markdown"]}
    try:
        async with session.post(FIRECRAWL_URL, json=payload, timeout=25) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data", {}).get("markdown", "")
    except Exception:
        pass
    return ""

async def extract_lead(url: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> Optional[LeadSchema]:
    async with semaphore:
        print(f"[Firecrawl V4] Deep Extracting {url}...")
        
        # Base url parsing
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # 1. Fetch Homepage
        md_content = await _fetch_markdown(url, session)
        
        # 2. Extract
        lead = parse_markdown_to_lead(url, md_content)
        
        # 3. If no highly-validated emails found, DEEP CRAWL /contact and /about
        if not lead.emails:
            print(f"  -> No emails on homepage. Deep crawling subpages for {base_url}...")
            subpages = [f"{base_url}/contact", f"{base_url}/about", f"{base_url}/contact-us"]
            
            for sub_url in subpages:
                sub_md = await _fetch_markdown(sub_url, session)
                if sub_md:
                    sub_lead = parse_markdown_to_lead(sub_url, sub_md)
                    # Merge findings
                    lead.emails.extend(sub_lead.emails)
                    lead.phones.extend(sub_lead.phones)
                    lead.socials.extend(sub_lead.socials)
                
                # De-duplicate after merge
                lead.emails = list(set(lead.emails))
                lead.phones = list(set(lead.phones))
                lead.socials = list(set(lead.socials))
                
                if lead.emails: # Stop crawling subpages if we found an email
                    print(f"  -> Found {lead.emails} on {sub_url}!")
                    break

        if not lead.emails:
            domain = parsed.netloc
            # V6 GOD-TIER: AI Vision OCR Extraction Fallback
            print(f"  -> Searching for obfuscated images. Initiating V6 AI Vision OCR...")
            ocr_emails = await extract_emails_from_images(md_content, session)
            if ocr_emails:
                print(f"  -> [V6 SUCCESS] Bypassed Obfuscation! Extracted hidden emails from images: {ocr_emails}")
                lead.emails.extend(ocr_emails)
                lead.description = "Scraped via V6 Priority Image OCR"

        if not lead.emails:
            # V6 GOD-TIER: WHOIS DNS Extraction Fallback
            print(f"  -> Absolute missing context. Initiating V6 WHOIS DNS Enrichment for {domain}...")
            whois_data = extract_whois_data(url)
            if whois_data["emails"]:
                print(f"  -> [V6 SUCCESS] Bypassed Firewall! Extracted hidden founder emails from DNS: {whois_data['emails']}")
                lead.emails.extend(whois_data["emails"])
                lead.description = "Scraped via V6 Priority WHOIS Verification"

        if lead.emails or lead.phones:
            return lead
        else:
            print(f"[Firecrawl V6] Dropped {url} due to absolute missing contact info.")
            return None

async def extract_all_leads(urls: List[str]) -> List[LeadSchema]:
    print(f"[Firecrawl] Schedulling extraction for {len(urls)} URLs...")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXTRACTIONS)
    async with aiohttp.ClientSession() as session:
        tasks = [extract_lead(url, session, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)
        
    valid_leads = [r for r in results if r is not None]
    print(f"[Firecrawl] Successfully extracted {len(valid_leads)} valid leads out of {len(urls)}.")
    return valid_leads
