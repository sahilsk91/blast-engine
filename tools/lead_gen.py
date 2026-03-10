"""
B.L.A.S.T V12 — Orchestrator
=============================
Pulls URLs from 3 parallel sources, feeds them into the V12
8-layer extraction waterfall, deduplicates against the SQLite
history, and writes a clean timestamped CSV.

Sources:
  1. DDG/Google web search (search_engine.py)
  2. Google Maps business listings (gmaps_scraper.py)
  3. LinkedIn X-Ray snippet emails (xray_search.py) — zero login

Usage:
  python lead_gen.py "Dentists in Miami" --count 50
  python lead_gen.py "Lawyers" --location "Houston" --count 30
  python lead_gen.py "Marketing Director" --person --location "NYC" --count 20
"""

import os
import sys
import datetime
import argparse
import pandas as pd

from search_engine  import get_search_results
from firecrawl_client import extract_all_leads
from local_db       import init_db, email_exists, save_lead

BATCH_SIZE = 20


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_niche_location(query: str, location_override: str) -> tuple[str, str]:
    """Split 'Lawyers in Houston' → ('Lawyers', 'Houston')."""
    parts = query.split(" in ", 1)
    niche    = parts[0].strip()
    location = location_override or (parts[1].strip() if len(parts) > 1 else "")
    return niche, location


def _record_to_row(lead, new_emails: list[str]) -> dict:
    return {
        "Entity":         "Company",
        "Name":           lead.name or "N/A",
        "Role/Desc":      lead.description or "N/A",
        "Website/Social": lead.website,
        "Emails":         ", ".join(new_emails),
        "Phones":         ", ".join(lead.phones),
        "Source_URL":     lead.source_url,
    }


def _save_csv(data: list[dict], query: str) -> str:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(project_root, "exports")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = "".join(c if c.isalnum() else "_" for c in query)
    path = os.path.join(out_dir, f"{slug}_{ts}.csv")
    pd.DataFrame(data).to_csv(path, index=False)
    return path


# ── Person / LinkedIn X-Ray mode ─────────────────────────────────────────────

def run_person_mode(niche: str, location: str, count: int, query: str) -> list[dict]:
    if not location:
        print("❌  --location is required with --person mode.")
        sys.exit(1)

    print(f"[Mode] LinkedIn X-Ray  |  {niche}  in  {location}")
    from xray_search import run_xray_search
    leads = run_xray_search("", count, niche=niche, location=location)

    data = []
    for lead in leads:
        new_emails = [e for e in lead.emails if not email_exists(e)]
        if new_emails:
            for e in new_emails:
                save_lead(e, lead.name, lead.source_url, query, location)
            data.append({
                "Entity":         lead.entity_type,
                "Name":           lead.name,
                "Role/Desc":      lead.title_or_description[:120],
                "Website/Social": lead.website_or_social,
                "Emails":         ", ".join(new_emails),
                "Phones":         ", ".join(lead.phones),
                "Source_URL":     "LinkedIn X-Ray",
            })
    return data


# ── Business / Omni-Source mode ───────────────────────────────────────────────

def run_business_mode(query: str, niche: str, location: str, count: int) -> list[dict]:
    print(f"[Mode] V12 Omni-Source  |  {niche}  {('in ' + location) if location else ''}")

    # ── Collect URLs from all 3 sources ─────────────────────────────────────
    all_urls: list[str] = []

    # Source 1 — Web DDG/Google
    print(f"\n[S1] Web search → {count * 8} URLs…")
    web_urls = get_search_results(query, count * 8)
    all_urls.extend(web_urls)
    print(f"     {len(web_urls)} URLs collected")

    # Source 2 — Google Maps
    if location:
        try:
            from gmaps_scraper import find_business_urls_via_gmaps
            print(f"\n[S2] Google Maps → '{niche}' in '{location}'…")
            maps_urls = find_business_urls_via_gmaps(niche, location, target=min(60, count * 3))
            known = set(all_urls)
            new_m = [u for u in maps_urls if u not in known]
            all_urls.extend(new_m)
            print(f"     {len(new_m)} NEW URLs from Maps")
        except Exception as e:
            print(f"[S2] Maps skipped: {e}")

    # Source 3 — LinkedIn X-Ray (collect emails directly from snippets)
    linkedin_rows: list[dict] = []
    try:
        from xray_search import run_xray_search
        print(f"\n[S3] LinkedIn X-Ray → '{niche}' in '{location}'…")
        xray_leads = run_xray_search("", min(count, 30), niche=niche, location=location)
        for lead in xray_leads:
            new_emails = [e for e in lead.emails if not email_exists(e)]
            if new_emails:
                for e in new_emails:
                    save_lead(e, lead.name, lead.source_url, query, location)
                linkedin_rows.append({
                    "Entity":         lead.entity_type,
                    "Name":           lead.name,
                    "Role/Desc":      lead.title_or_description[:120],
                    "Website/Social": lead.website_or_social,
                    "Emails":         ", ".join(new_emails),
                    "Phones":         ", ".join(lead.phones),
                    "Source_URL":     "LinkedIn X-Ray",
                })
        print(f"     {len(linkedin_rows)} leads from LinkedIn X-Ray")
    except Exception as e:
        print(f"[S3] X-Ray skipped: {e}")

    if not all_urls and not linkedin_rows:
        print("No URLs found from any source.")
        return linkedin_rows

    # ── Waterfall extraction loop ─────────────────────────────────────────────
    unique_rows: list[dict] = []
    dups = 0

    for i in range(0, len(all_urls), BATCH_SIZE):
        if len(unique_rows) >= count:
            break

        batch = all_urls[i : i + BATCH_SIZE]
        print(f"\n[Waterfall] Batch {i // BATCH_SIZE + 1}  ({len(batch)} URLs)…")
        
        # Wrapping in asyncio event loop since Firecrawl client was reverted to async
        import asyncio
        leads = asyncio.run(extract_all_leads(batch))

        for lead in leads:
            if len(unique_rows) >= count:
                break

            new_emails = [e for e in lead.emails if not email_exists(e)]

            if lead.emails and not new_emails:
                dups += 1
                continue

            if new_emails:
                for e in new_emails:
                    save_lead(e, lead.name or "", lead.source_url, query, location)
                unique_rows.append(_record_to_row(lead, new_emails))

        print(f"[Pipeline] {len(unique_rows)}/{count} unique verified leads so far.")

    if dups:
        print(f"\n[DB] Caught {dups} duplicate leads from past runs.")

    return unique_rows + linkedin_rows


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="B.L.A.S.T V12 Lead Engine")
    ap.add_argument("query",       type=str)
    ap.add_argument("--count",     type=int,  default=50)
    ap.add_argument("--person",    action="store_true")
    ap.add_argument("--location",  type=str,  default="")
    ap.add_argument("--omniscience", action="store_true")  # kept for CLI compat
    args = ap.parse_args()

    print(f"\n{'='*50}")
    print(f"  B.L.A.S.T V12 — {args.query}")
    print(f"  Target: {args.count} leads")
    print(f"{'='*50}\n")

    init_db()
    niche, location = _parse_niche_location(args.query, args.location)

    if args.person:
        data = run_person_mode(niche, location, args.count, args.query)
    else:
        data = run_business_mode(args.query, niche, location, args.count)

    if not data:
        print("\n[Done] No new unique leads found this run.")
        return

    path = _save_csv(data, args.query)
    print(f"\n[Done] {len(data)} leads → {path}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
