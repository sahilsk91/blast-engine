import re
import time
import random
from googlesearch import search
from duckduckgo_search import DDGS
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import warnings

warnings.filterwarnings("ignore", message=".*renamed.*")

# ---- Niche Synonym Expansion ----
# When the user searches for "Lawyer", we also search "Attorney", "Law Firm", etc.
# This breaks through the DDG snippet cache ceiling by querying fundamentally different terms.
NICHE_SYNONYMS = {
    "lawyer":      ["attorney", "law firm", "legal counsel", "paralegal", "solicitor", "barrister", "legal advisor"],
    "attorney":    ["lawyer", "law firm", "legal counsel", "paralegal", "solicitor", "legal advisor"],
    "plumber":     ["plumbing company", "plumbing contractor", "plumbing services", "drain specialist", "pipe fitter"],
    "electrician": ["electrical contractor", "electrical services", "wiring specialist", "electrical company"],
    "dentist":     ["dental clinic", "dental practice", "orthodontist", "dental surgeon", "dental office"],
    "doctor":      ["physician", "medical practice", "clinic", "healthcare provider", "medical doctor"],
    "accountant":  ["CPA", "tax advisor", "bookkeeper", "accounting firm", "tax preparer"],
    "realtor":     ["real estate agent", "real estate broker", "property agent", "real estate company"],
    "contractor":  ["construction company", "general contractor", "building contractor", "renovation company"],
    "therapist":   ["counselor", "psychologist", "mental health", "psychotherapist", "life coach"],
    "ceo":         ["founder", "owner", "managing director", "president", "chief executive"],
    "cfo":         ["finance director", "VP finance", "financial controller", "head of finance"],
    "cto":         ["VP engineering", "head of technology", "technical director", "chief architect"],
    "marketing director": ["VP marketing", "head of marketing", "CMO", "marketing manager", "brand director"],
}


def _get_synonyms(niche: str) -> list[str]:
    """Get synonym variations for a niche term. Returns [original, syn1, syn2, ...]"""
    key = niche.lower().strip()
    synonyms = [niche]  # Always include the original

    for base, syns in NICHE_SYNONYMS.items():
        if base in key or key in base:
            synonyms.extend(syns)
            break

    return list(dict.fromkeys(synonyms))  # De-dup preserving order


class OmniLead(BaseModel):
    entity_type: str = "Person"  # or Company
    name: str = "Unknown"
    title_or_description: str = ""
    website_or_social: str = ""
    source_url: str = ""
    emails: List[str] = []
    phones: List[str] = []

    model_config = ConfigDict(extra="ignore")


from verify_email import verify_email

def extract_contacts_from_text(text: str):
    # Strict email regex: TLD must be 2-10 alpha chars, optional second-level TLD
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,6}(?:\.[a-zA-Z]{2,4})?'
    phone_pattern = r'(?:\+?1[-.\s]?)?\(?[2-9][0-8][0-9]\)?[-.\s]?[2-9][0-9]{2}[-.\s]?[0-9]{4}'

    emails = list(set(re.findall(email_pattern, text)))
    phones = list(set(re.findall(phone_pattern, text)))

    # Filter noise via regex
    noise = ["sentry", "w3.org", "example", ".png", ".jpg", ".svg", ".gif",
             "noreply", "no-reply", "mailer-daemon", "wixpress", "sentry.io",
             "wordpress", "schema.org", "cloudflare"]
    raw_emails = [e for e in emails if not any(x in e.lower() for x in noise)]
    if not raw_emails:
        raw_emails = [e for e in emails if "@" in e][:3]

    # V11 Infinite Quality: SMTP/DNS Validation
    clean_emails = []
    for email in raw_emails:
        if verify_email(email)["valid"]:
            clean_emails.append(email)

    return clean_emails, phones


def build_xray_dorks(niche: str, location: str) -> list[str]:
    """
    V10: Generates EXPANDED dorks using niche synonyms to break through
    the DDG snippet cache ceiling. More terms = more unique cached pages.
    """
    synonyms = _get_synonyms(niche)
    email_domains = ["@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com"]
    dorks = []

    for term in synonyms:
        # Strategy 1: LinkedIn X-Ray with each email domain
        for domain in email_domains:
            dorks.append(f'site:linkedin.com/in "{term}" "{location}" "{domain}"')

        # Strategy 2: LinkedIn with generic contact keywords
        dorks.append(f'site:linkedin.com/in "{term}" "{location}" email')
        dorks.append(f'site:linkedin.com/in "{term}" "{location}" contact')

        # Strategy 3: Broader web search for emails
        dorks.append(f'"{term}" "{location}" "@gmail.com" OR "@yahoo.com" -site:linkedin.com')

    return dorks


# Keep the old function signature for backward compatibility
def build_xray_dork(niche: str, location: str) -> str:
    """Legacy wrapper — returns the first dork for backward compat."""
    return build_xray_dorks(niche, location)[0]


def _stealth_delay():
    """Random delay between 8-15 seconds to avoid rate limits on local IP."""
    delay = random.uniform(8, 15)
    print(f"      [Stealth] Cooling down {delay:.1f}s...")
    time.sleep(delay)


def run_xray_search(query: str, target_count: int = 20, niche: str = "", location: str = "") -> List[OmniLead]:
    """
    V10 X-Ray Engine: Multi-synonym dork expansion with stealth delays.
    Uses DDG → Bing → Brave → Google fallback chain.
    """
    if niche and location:
        queries = build_xray_dorks(niche, location)
    else:
        queries = [query]

    print(f"\n[X-Ray Engine V10] Initiating stealth search with {len(queries)} dork(s)")
    print(f"[X-Ray Engine V10] Target: {target_count} leads | Stealth delays: ON")

    leads = []
    seen_names = set()

    def _process_result(title: str, snippet: str, url: str, source: str):
        """Process a single search result and add to leads if valid."""
        full_text = f"{title} {snippet}"
        emails, phones = extract_contacts_from_text(full_text)

        if emails or phones:
            name = title.split("-")[0].strip() if "-" in title else title.split("|")[0].strip()
            # Clean name
            name = name.strip()
            if not name or name in seen_names or len(name) > 60 or len(name) < 3:
                return False
            # Skip generic names
            if any(x in name.lower() for x in ["linkedin", "search", "results", "page", "contact"]):
                return False

            seen_names.add(name)
            lead = OmniLead(
                entity_type="Person" if "linkedin.com/in" in url else "Company",
                name=name,
                title_or_description=snippet[:120] + "..." if len(snippet) > 120 else snippet,
                website_or_social=url,
                source_url=f"{source} Snippet",
                emails=emails,
                phones=phones
            )
            leads.append(lead)
            print(f"      [Hit #{len(leads)}] {name} -> {emails[:2]}")
            return True
        return False

    # ---- Engine 1: DuckDuckGo (primary) ----
    print(f"\n  [Engine 1/3] DuckDuckGo ({len(queries)} queries)...")
    try:
        ddg = DDGS()
        for qi, q in enumerate(queries):
            if len(leads) >= target_count:
                break
            print(f"    [{qi+1}/{len(queries)}] '{q[:65]}...'")
            try:
                results = ddg.text(q, max_results=30)
                hits_this_query = 0
                for r in results:
                    if _process_result(r.get("title", ""), r.get("body", ""), r.get("href", ""), "DDG"):
                        hits_this_query += 1
                    if len(leads) >= target_count:
                        break
                if hits_this_query > 0:
                    _stealth_delay()
                else:
                    time.sleep(random.uniform(3, 5))  # Shorter delay if no results
            except Exception as e:
                print(f"    -> DDG error: {e}")
                time.sleep(random.uniform(5, 10))
                continue
    except Exception as e:
        print(f"  [Engine 1] DDG Global Error: {e}")

    # ---- Engine 2: Bing (via scraping) ----
    if len(leads) < target_count:
        print(f"\n  [Engine 2/3] Bing Search ({len(leads)}/{target_count} so far)...")
        try:
            import requests
            from bs4 import BeautifulSoup
            from fake_useragent import UserAgent
            ua = UserAgent()

            # Use a subset of dorks for Bing (it handles site: differently)
            bing_queries = [q for q in queries if "site:" not in q][:10]
            # Also add some Bing-specific queries
            synonyms = _get_synonyms(niche) if niche else [query]
            for term in synonyms[:4]:
                bing_queries.append(f'{term} {location} email contact')

            for qi, q in enumerate(bing_queries):
                if len(leads) >= target_count:
                    break
                print(f"    [{qi+1}/{len(bing_queries)}] Bing: '{q[:60]}...'")
                try:
                    headers = {"User-Agent": ua.random, "Accept-Language": "en-US,en;q=0.9"}
                    params = {"q": q, "count": "20"}
                    resp = requests.get("https://www.bing.com/search", params=params, headers=headers, timeout=15)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        for li in soup.select("li.b_algo"):
                            a = li.select_one("h2 a")
                            p = li.select_one(".b_caption p")
                            if a and p:
                                _process_result(a.get_text(), p.get_text(), a.get("href", ""), "Bing")
                            if len(leads) >= target_count:
                                break
                    _stealth_delay()
                except Exception as e:
                    print(f"    -> Bing error: {e}")
                    time.sleep(5)
                    continue
        except ImportError:
            print("  [Engine 2] Skipping Bing (requests/bs4 not installed)")

    # ---- Engine 3: Brave Search (via scraping) ----
    if len(leads) < target_count:
        print(f"\n  [Engine 3/3] Brave Search ({len(leads)}/{target_count} so far)...")
        try:
            import requests
            from bs4 import BeautifulSoup
            from fake_useragent import UserAgent
            ua = UserAgent()

            brave_queries = [q for q in queries if "site:" not in q][:8]
            for qi, q in enumerate(brave_queries):
                if len(leads) >= target_count:
                    break
                print(f"    [{qi+1}/{len(brave_queries)}] Brave: '{q[:60]}...'")
                try:
                    headers = {
                        "User-Agent": ua.random,
                        "Accept": "text/html,application/xhtml+xml",
                        "Accept-Language": "en-US,en;q=0.9",
                    }
                    params = {"q": q}
                    resp = requests.get("https://search.brave.com/search", params=params, headers=headers, timeout=15)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        for item in soup.select(".snippet"):
                            title_el = item.select_one(".snippet-title")
                            desc_el = item.select_one(".snippet-description")
                            link_el = item.select_one("a")
                            if title_el and desc_el and link_el:
                                _process_result(
                                    title_el.get_text(),
                                    desc_el.get_text(),
                                    link_el.get("href", ""),
                                    "Brave"
                                )
                            if len(leads) >= target_count:
                                break
                    _stealth_delay()
                except Exception as e:
                    print(f"    -> Brave error: {e}")
                    time.sleep(5)
                    continue
        except ImportError:
            print("  [Engine 3] Skipping Brave (requests/bs4 not installed)")

    # ---- Final: Google (last resort, likely to 429) ----
    if len(leads) < target_count:
        print(f"\n  [Engine 4/4] Google Fallback ({len(leads)}/{target_count} so far)...")
        google_queries = [q for q in queries if "site:" not in q][:5]
        for qi, q in enumerate(google_queries):
            if len(leads) >= target_count:
                break
            print(f"    [{qi+1}/{len(google_queries)}] Google: '{q[:60]}...'")
            try:
                results = search(q, num_results=20, lang="en", advanced=True)
                for r in results:
                    _process_result(r.title or "", r.description or "", r.url, "Google")
                    if len(leads) >= target_count:
                        break
                _stealth_delay()
            except Exception as e:
                print(f"    -> Google error: {e}")
                break

    print(f"\n[X-Ray Engine V10] Complete. Extracted {len(leads)} leads across all engines.")
    return leads

if __name__ == "__main__":
    leads = run_xray_search("", 10, niche="Marketing Director", location="London")
    for l in leads:
        print(l.model_dump())
