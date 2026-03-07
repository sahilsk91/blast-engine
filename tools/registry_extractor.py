import re
from ddgs import DDGS
from googlesearch import search
import time
from search_engine import get_spoofed_headers, V6_PROXY
import warnings

warnings.filterwarnings("ignore", message=".*renamed.*")


def hunt_company_officers(company_name: str) -> list[dict]:
    """
    V9 Global Omniscience: Automated Officer Hunter.
    Uses multiple simpler dorks instead of one complex boolean.
    Searches for Founders, CEOs, and Owners via LinkedIn snippet caching.
    """
    print(f"\n[V9 Omniscience] Initiating Officer Hunt for: {company_name}...")

    # Clean the name
    clean_name = company_name.lower().replace("www.", "").replace(".com", "").replace(".org", "").replace(".net", "")

    # Multiple targeted dorks instead of one complex boolean
    dorks = [
        f'site:linkedin.com/in "{clean_name}" "Founder" OR "CEO" OR "Owner"',
        f'site:linkedin.com/in "{clean_name}" "Director" OR "Managing" email',
        f'"{clean_name}" "Founder" OR "CEO" "@gmail.com" OR "@yahoo.com"',
        f'"{clean_name}" "Owner" OR "Director" contact email',
    ]

    officers = []
    seen_names = set()

    # Try DDG first
    try:
        with DDGS(proxy=V6_PROXY) as ddgs:
            if hasattr(ddgs, 'headers'):
                ddgs.headers.update(get_spoofed_headers())

            for dork in dorks:
                if len(officers) >= 5:
                    break
                try:
                    results = ddgs.text(dork, max_results=5)
                    for r in results:
                        title = r.get("title", "")
                        body = r.get("body", "")

                        # Extract Name from LinkedIn Title
                        name = title.split("-")[0].strip()
                        if "|" in name:
                            name = name.split("|")[0].strip()

                        # Skip bad names
                        if not name or len(name) > 40 or "LinkedIn" in name or name in seen_names:
                            continue

                        # Extract Email via Regex from snippet
                        full_text = f"{title} {body}"
                        email_match = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,10}(?:\.[a-zA-Z]{2,10})?', full_text)
                        # Filter noise
                        raw_emails = [e for e in email_match if not any(x in e.lower() for x in
                                       ["sentry", "w3.org", "example", ".png", "noreply", "linkedin"])]

                        # V11 Infinite Quality: SMTP/DNS Validation
                        from verify_email import verify_email
                        valid_emails = [e for e in raw_emails if verify_email(e)["valid"]]

                        if valid_emails:
                            seen_names.add(name)
                            officers.append({
                                "Name": name,
                                "Company": company_name,
                                "Personal_Email": valid_emails[0],
                                "Source": "V9 LinkedIn X-Ray Auto-Mapper"
                            })
                            print(f"  -> Found: {name} ({valid_emails[0]})")
                    time.sleep(1.5)
                except Exception as e:
                    print(f"  -> DDG Officer dork error: {e}")
                    time.sleep(2)
                    continue
    except Exception as e:
        print(f"  -> DDG Global Error: {e}")

    # Google fallback for broader company searches
    if not officers:
        print(f"  -> Google fallback for {company_name}...")
        try:
            q = f'"{clean_name}" "founder" OR "CEO" "@gmail.com" OR "@yahoo.com"'
            results = search(q, num_results=10, lang="en", advanced=True)
            for r in results:
                title = r.title or ""
                snippet = r.description or ""
                full_text = f"{title} {snippet}"

                email_match = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,10}(?:\.[a-zA-Z]{2,10})?', full_text)
                raw_emails = [e for e in email_match if not any(x in e.lower() for x in
                               ["sentry", "w3.org", "example", ".png", "noreply", "linkedin"])]
                               
                from verify_email import verify_email
                valid_emails = [e for e in raw_emails if verify_email(e)["valid"]]

                if valid_emails:
                    name = title.split("-")[0].strip() if "-" in title else title.split("|")[0].strip()
                    if name and name not in seen_names and len(name) < 40:
                        seen_names.add(name)
                        officers.append({
                            "Name": name,
                            "Company": company_name,
                            "Personal_Email": valid_emails[0],
                            "Source": "V9 Google X-Ray Fallback"
                        })
                        print(f"  -> Found: {name} ({valid_emails[0]})")

                if len(officers) >= 5:
                    break
            time.sleep(2)
        except Exception as e:
            print(f"  -> Google Officer error: {e}")

    print(f"  -> Officer Hunt complete: {len(officers)} found.")
    return officers


# Manual Test
if __name__ == "__main__":
    o = hunt_company_officers("Nike")
    print(o)
