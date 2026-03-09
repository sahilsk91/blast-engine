"""
B.L.A.S.T V12 — Extraction Engine (Insane Mode)
=================================================
8-layer waterfall per URL, all free, all Python, no APIs:

  L1 — Homepage HTML (regex + mailto: links)
  L2 — JSON-LD / schema.org structured data (Google indexes this)
  L3 — Obfuscated email decoding ([at], (dot), HTML entity, Unicode)
  L4 — Navbar contact page discovery (crawls the nav, finds /contact links)
  L5 — Sitemap.xml / robots.txt crawl to find all internal pages
  L6 — Static subpage brute-force (/contact, /about, /team, /staff ...)
  L7 — OSINT DuckDuckGo Domain Dork ("@domain.com")
  L8 — WHOIS DNS fallback

Thread-pooled for parallel execution. Session reuse for speed.
"""

import re
import json
import time
import html
import random
import urllib3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, unquote
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Disable SSL warnings for small business sites with expired certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Config ─────────────────────────────────────────────────────────────────
MAX_WORKERS   = 25
TIMEOUT       = 10
MAX_SUBPAGES  = 12   # Max pages to crawl per site

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# ── Lead Schema ─────────────────────────────────────────────────────────────
class LeadSchema(BaseModel):
    name:        Optional[str] = None
    website:     str
    description: Optional[str] = None
    source_url:  str
    emails:      List[str] = []
    phones:      List[str] = []
    socials:     List[str] = []
    model_config = ConfigDict(extra="ignore")


# ── Email Quality Gate ───────────────────────────────────────────────────────
_SPAM = [
    "sentry.", "w3.org", "example.", ".png", ".jpg", ".gif", ".svg", ".webp",
    "no-reply", "noreply", "mailer-daemon", "postmaster@", "hostmaster@",
    "webmaster@", "abuse@", "compliance@", "privacy@", "dkim@", "bounce@",
    "godaddy", "namecheap", "cloudflare", "networksolutions", "hostgator",
    "register.com", "tucows", "enom", "markmonitor", "porkbun",
    "bluehost", "siteground", "dreamhost", "hostinger",
    "amazon.com", "amazonaws", "registrar", "yellowpages", "wixpress",
    "squarespace.com", "shopify.com", "wordpress.com", "schema.org",
]

_EMAIL_RE   = re.compile(r"[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}")
_PHONE_RE   = re.compile(r"(?:\+?1[\.\-\s]?)?\(?\d{3}\)?[\.\-\s]?\d{3}[\.\-\s]?\d{4}")
_SOCIAL_RE  = re.compile(r"https?://(?:www\.)?(?:facebook|twitter|instagram|linkedin|yelp)\.com/[^\s\"'<>]+")

def _ok_email(e: str) -> bool:
    e = e.lower()
    if not re.match(r"^[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z]{2,63}$", e):
        return False
    return not any(s in e for s in _SPAM)


# ── HTTP helpers ─────────────────────────────────────────────────────────────
def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent":      random.choice(USER_AGENTS),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "DNT":             "1",
        "Connection":      "keep-alive",
    })
    s.max_redirects = 5
    return s

def _get(sess: requests.Session, url: str) -> str:
    try:
        r = sess.get(url, timeout=TIMEOUT, verify=False, allow_redirects=True)
        if r.status_code == 200 and ("text" in r.headers.get("Content-Type","") or "html" in r.headers.get("Content-Type","")):
            return r.text
    except Exception:
        pass
    return ""


# ── Layer helpers ─────────────────────────────────────────────────────────────

# L1 + L3: Standard HTML parse + obfuscation decode
def _emails_from_html(html_src: str) -> list[str]:
    emails = []

    # A. Raw regex on full HTML
    emails += _EMAIL_RE.findall(html_src)

    # B. Explicit mailto: hrefs
    soup = BeautifulSoup(html_src, "html.parser")
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if h.lower().startswith("mailto:"):
            e = unquote(h[7:]).split("?")[0].strip()
            emails.append(e)

    # C. Obfuscation decoding — catches [at], (dot), HTML entities, Unicode escapes
    decoded = html.unescape(html_src)
    # [at] / [dot] style
    obf = re.sub(r'\s*\[at\]\s*', '@', decoded, flags=re.IGNORECASE)
    obf = re.sub(r'\s*\(at\)\s*', '@', obf, flags=re.IGNORECASE)
    obf = re.sub(r'\s*@\(\)\s*', '@', obf)
    obf = re.sub(r'\s*\[dot\]\s*', '.', obf, flags=re.IGNORECASE)
    obf = re.sub(r'\s*\(dot\)\s*', '.', obf, flags=re.IGNORECASE)
    emails += _EMAIL_RE.findall(obf)

    # D. Plain-text visible in the page (catches CSS-hidden text tricks)
    try:
        text = soup.get_text(separator=" ")
        emails += _EMAIL_RE.findall(text)
    except Exception:
        pass

    return list(set(e.lower() for e in emails if _ok_email(e)))


# L2: JSON-LD / schema.org structured data
def _emails_from_jsonld(html_src: str) -> list[str]:
    emails = []
    try:
        soup = BeautifulSoup(html_src, "html.parser")
        for tag in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(tag.string or "{}")
                blob = json.dumps(data)  # Flatten to string for regex
                emails += _EMAIL_RE.findall(blob)
            except Exception:
                pass
    except Exception:
        pass
    return [e for e in set(e.lower() for e in emails) if _ok_email(e)]


# L4: Nav contact page discovery
def _find_contact_links(base_url: str, html_src: str) -> list[str]:
    """Scan the HTML nav bars and anchor tags for contact/about/team pages."""
    contact_keywords = ["contact", "about", "team", "staff", "reach", "connect",
                        "get-in-touch", "people", "our-team", "office", "location"]
    found = []
    try:
        soup = BeautifulSoup(html_src, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            label = a.get_text(separator=" ").lower()
            if any(k in href or k in label for k in contact_keywords):
                full = urljoin(base_url, a["href"])
                if urlparse(full).netloc == urlparse(base_url).netloc:
                    found.append(full)
    except Exception:
        pass
    return list(dict.fromkeys(found))[:8]  # Deduplicate, cap at 8


# L5: Sitemap.xml / robots.txt intelligence
def _sitemap_urls(sess: requests.Session, base_url: str) -> list[str]:
    """Parse robots.txt to find sitemap, then scan sitemap for contact pages."""
    contact_urls = []
    contact_kw = re.compile(r"contact|about|team|staff|people|office", re.I)

    # 1. Try robots.txt first
    robots = _get(sess, f"{base_url}/robots.txt")
    sitemap_locs = re.findall(r"Sitemap:\s*(https?://\S+)", robots, re.I)
    if not sitemap_locs:
        sitemap_locs = [f"{base_url}/sitemap.xml", f"{base_url}/sitemap_index.xml"]

    for sitemap_url in sitemap_locs[:2]:
        xml = _get(sess, sitemap_url)
        if not xml:
            continue
        # Extract all <loc> URLs
        locs = re.findall(r"<loc>(.*?)</loc>", xml, re.I | re.S)
        for loc in locs:
            loc = loc.strip()
            if contact_kw.search(loc) and urlparse(loc).netloc == urlparse(base_url).netloc:
                contact_urls.append(loc)

    return list(dict.fromkeys(contact_urls))[:6]


# ── Core Extraction Per URL ───────────────────────────────────────────────────
def extract_lead(url: str) -> Optional[LeadSchema]:
    """
    Runs the full 8-layer extraction waterfall for a single URL.
    Returns a LeadSchema or None if no contact info found.
    """
    try:
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        domain = parsed.netloc.lower().replace("www.", "")

        print(f"[V12] → {domain}")

        sess = _session()
        all_emails: list[str] = []
        all_phones: list[str] = []
        all_socials: list[str] = []
        pages_crawled = set()

        def _process_page(page_url: str):
            if page_url in pages_crawled or len(pages_crawled) >= MAX_SUBPAGES:
                return
            pages_crawled.add(page_url)
            src = _get(sess, page_url)
            if not src:
                return
            # L1 + L3: HTML + obfuscation
            all_emails.extend(_emails_from_html(src))
            # L2: JSON-LD
            all_emails.extend(_emails_from_jsonld(src))
            # Phones + Socials
            try:
                all_phones.extend(_PHONE_RE.findall(BeautifulSoup(src, "html.parser").get_text()))
                all_socials.extend(_SOCIAL_RE.findall(src))
            except Exception:
                pass
            return src

        # === L1/L2/L3: Homepage ===
        homepage_src = _process_page(url)

        # === L4: Nav-discovered contact pages ===
        if homepage_src and not all_emails:
            nav_pages = _find_contact_links(base_url, homepage_src)
            for p in nav_pages[:4]:
                _process_page(p)
                if all_emails:
                    break

        # === L5: Sitemap / robots.txt ===
        if not all_emails:
            sitemap_pages = _sitemap_urls(sess, base_url)
            for p in sitemap_pages:
                _process_page(p)
                if all_emails:
                    break

        # === L6: Static subpage brute-force ===
        if not all_emails:
            static_pages = [
                f"{base_url}/contact",      f"{base_url}/contact-us",
                f"{base_url}/about",        f"{base_url}/about-us",
                f"{base_url}/team",         f"{base_url}/our-team",
                f"{base_url}/staff",        f"{base_url}/reach-us",
                f"{base_url}/get-in-touch", f"{base_url}/connect",
                f"{base_url}/office",       f"{base_url}/locations",
            ]
            for p in static_pages:
                if all_emails:
                    break
                _process_page(p)

        # === L7: OSINT Domain Dork ===
        if not all_emails:
            try:
                from domain_enrichment import lookup_domain_emails
                hits = lookup_domain_emails(url)
                for h in hits:
                    e = h.get("email", "")
                    if e and _ok_email(e):
                        all_emails.append(e)
            except Exception:
                pass

        # === L8: WHOIS DNS fallback ===
        if not all_emails:
            try:
                from enrichment import extract_whois_data
                w = extract_whois_data(url)
                all_emails.extend([e for e in w.get("emails", []) if _ok_email(e)])
            except Exception:
                pass

        # ── De-duplicate ──────────────────────────────────────────────────
        all_emails  = list(dict.fromkeys(all_emails))
        all_phones  = list(dict.fromkeys(p.strip() for p in all_phones))[:5]
        all_socials = list(dict.fromkeys(all_socials))[:5]

        if not all_emails and not all_phones:
            return None

        # ── Business name from <title> ──────────────────────────────────
        name = domain
        if homepage_src:
            try:
                t = BeautifulSoup(homepage_src, "html.parser").find("title")
                if t and t.get_text(strip=True):
                    name = t.get_text(strip=True)[:80]
            except Exception:
                pass

        source = "V12 Waterfall"
        if len(pages_crawled) > 1:
            source = f"V12 ({len(pages_crawled)} pages crawled)"

        return LeadSchema(
            name=name,
            website=url,
            description=source,
            source_url=url,
            emails=all_emails,
            phones=all_phones,
            socials=all_socials,
        )

    except Exception as e:
        print(f"[V12] ✗ {url} → {e}")
        return None


# ── Parallel Batch Extractor ──────────────────────────────────────────────────
def extract_all_leads(urls: List[str]) -> List[LeadSchema]:
    """
    Runs all URLs in a parallel thread pool.
    Returns all successfully extracted LeadSchema objects.
    """
    if not urls:
        return []

    leads = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(extract_lead, u): u for u in urls}
        for f in as_completed(futures):
            r = f.result()
            if r:
                leads.append(r)
                print(f"  ✅ {r.name} | {len(r.emails)} email(s)")

    return leads
