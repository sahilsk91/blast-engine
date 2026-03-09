import asyncio
import pandas as pd
import argparse
from search_engine import get_search_results
from firecrawl_client import extract_all_leads
from xray_search import run_xray_search

def main():
    parser = argparse.ArgumentParser(description="B.L.A.S.T Lead Generation Script (Omni-Extractor V9)")
    parser.add_argument("query", type=str, help="Search query (e.g., 'plumbers in Miami') or Niche for people (e.g., 'Marketing Director')")
    parser.add_argument("--count", type=int, default=50, help="Number of leads to fetch")
    parser.add_argument("--person", action="store_true", help="Enable Stealth X-Ray mode to extract people (LinkedIn parsing)")
    parser.add_argument("--location", type=str, default="", help="Location required if --person is used (e.g. 'London')")
    parser.add_argument("--omniscience", action="store_true", help="V7 God-Tier: Engage Automated Officer Hunter for B2B searches")
    
    args = parser.parse_args()
    
    print(f"=== B.L.A.S.T Lead Gen V9 Started ===")
    print(f"Query: {args.query}")
    print(f"Target: {args.count} leads\n")
    
    data = []
    
    if args.person:
        if not args.location:
            print("❌ Error: --location is required when using --person mode.")
            return
            
        print("[Mode] Stealth X-Ray V9 (LinkedIn Parsing Bypass)")
        leads = run_xray_search("", args.count, niche=args.query, location=args.location)
        
        for lead in leads:
            data.append({
                "Entity": lead.entity_type,
                "Name": lead.name,
                "Role/Desc": lead.title_or_description,
                "Website/Social": lead.website_or_social,
                "Emails": ", ".join(lead.emails),
                "Phones": ", ".join(lead.phones),
                "Source_URL": lead.source_url
            })
    else:
        print("[Mode] Horizontal Business Search (Firecrawl Engine)")
        
        import os
        import datetime
        from local_db import init_db, email_exists, save_lead
        
        # Initialize the local persistent deduplication database immediately
        init_db()

        # Over-fetch URLs because 1 URL != 1 valid lead. We fetch 10x buffer.
        fetch_count = args.count * 10
        print(f"[Engine] Need {args.count} leads. Fetching up to {fetch_count} URLs to guarantee yield...")
        urls = get_search_results(args.query, fetch_count)
        
        if not urls:
            print("No URLs found from Search Engines. Exiting.")
            return

        unique_data = []
        duplicates_caught = 0
        batch_size = 20
        
        # Process URLs in chunks until we hit the exact target quota
        for i in range(0, len(urls), batch_size):
            if len(unique_data) >= args.count:
                break
                
            batch_urls = urls[i:i+batch_size]
            print(f"\n[Engine] Extraction Batch {i//batch_size + 1} ({len(batch_urls)} URLs)...")
            batch_leads = asyncio.run(extract_all_leads(batch_urls))
            
            # Immediately validate and deduplicate the batch
            for lead in batch_leads:
                if len(unique_data) >= args.count:
                    break
                    
                emails_list = lead.emails
                new_emails = []
                
                # Check absolute deduplication
                for e in emails_list:
                    if not email_exists(e):
                        new_emails.append(e)
                
                if emails_list and not new_emails:
                    duplicates_caught += 1
                    continue
                    
                if new_emails:
                    # Save to DB to block it in future batches/runs instantly
                    for e in new_emails:
                        save_lead(e, str(lead.name or "N/A"), str(lead.source_url), args.query, args.location)
                        
                    unique_data.append({
                        "Entity": "Company",
                        "Name": lead.name or "N/A",
                        "Role/Desc": lead.description or "N/A",
                        "Website/Social": lead.website,
                        "Emails": ", ".join(new_emails),
                        "Phones": ", ".join(lead.phones),
                        "Source_URL": lead.source_url
                    })

            print(f"[Pipeline] Current Yield: {len(unique_data)}/{args.count} unique verified leads.")

        if duplicates_caught > 0:
            print(f"\n[DB Filter] Successfully caught and dropped {duplicates_caught} leads we already extracted in the past.")
            
        data = unique_data # Point data to unique data for the delivery block below
    
    # ---------------------------------------------------------
    # Delivery Block
    # ---------------------------------------------------------
    if not data:
        print("\n[Delivery] No NEW unique leads were found during this run.")
        print("=== B.L.A.S.T Lead Gen Complete ===")
        return
        
    print(f"\n[Delivery] Formatting {len(data)} NEW unique leads into CSV...")
    
    import os
    import datetime
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "exports")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_query = "".join([c if c.isalnum() else "_" for c in args.query])
    output_file = os.path.join(output_dir, f"{clean_query}_{timestamp}.csv")
    
    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False)
    
    print(f"[Delivery] Success! Saved {len(data)} NEW leads to {output_file}.")
    print("=== B.L.A.S.T Lead Gen Complete ===")

if __name__ == "__main__":
    main()
