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
        # Phase 1: Search (Layer 3 tool)
        urls = get_search_results(args.query, args.count)
        if not urls:
            print("No URLs found. Exiting.")
            return
            
        # Phase 2: Extraction (Layer 3 tool)
        leads = asyncio.run(extract_all_leads(urls))
        
        if not leads:
            print("No valid leads extracted (no contact info found). Exiting.")
            return
            
        # Phase 3: Stylize / Formatting (Payload Delivery)
        for lead in leads:
            # We cap at the target count if we somehow got more
            if len(data) >= args.count:
                break
                
            data.append({
                "Entity": "Company",
                "Name": lead.name or "N/A",
                "Role/Desc": lead.description or "N/A",
                "Website/Social": lead.website,
                "Emails": ", ".join(lead.emails),
                "Phones": ", ".join(lead.phones),
                "Source_URL": lead.source_url
            })
            
        if args.omniscience:
            from registry_extractor import hunt_company_officers
            print("\n[V7 Omniscience] Engaging Automated Officer Hunter for scraped businesses...")
            for lead in leads:
                if not lead.name: continue
                officers = hunt_company_officers(lead.name)
                for o in officers:
                    data.append({
                        "Entity": "Person (Officer)",
                        "Name": o["Name"],
                        "Role/Desc": f"Found via V7 Omniscience ({lead.name})",
                        "Website/Social": lead.website,
                        "Emails": o["Personal_Email"],
                        "Phones": "",
                        "Source_URL": o["Source"]
                    })
                    print(f"  -> Added {o['Name']} ({o['Personal_Email']})")
        
    if not data:
        print("No leads to save.")
        return
        
    import os
    import datetime
    from local_db import init_db, email_exists, save_lead
    
    # Initialize the local persistent deduplication database
    init_db()
    
    unique_data = []
    duplicates_caught = 0
    
    for row in data:
        emails_str = str(row.get("Emails", ""))
        emails_list = [e.strip() for e in emails_str.split(",") if e.strip()]
        new_emails = []
        
        for e in emails_list:
            if not email_exists(e):
                new_emails.append(e)
                save_lead(e, str(row.get("Name", "N/A")), str(row.get("Source_URL", "")), args.query, args.location)
                
        # If row had emails, but NONE are new (all existed in DB), completely skip this lead
        if emails_list and not new_emails:
            duplicates_caught += 1
            continue
            
        row["Emails"] = ", ".join(new_emails)
        unique_data.append(row)
        
    if duplicates_caught > 0:
        print(f"\n[DB Filter] Successfully caught and dropped {duplicates_caught} leads we already extracted in the past.")
        
    if not unique_data:
        print("\n[Delivery] No NEW unique leads to save (all were previously extracted).")
        print("=== B.L.A.S.T Lead Gen Complete ===")
        return
        
    print(f"\n[Delivery] Formatting {len(unique_data)} NEW unique leads into CSV...")
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "exports")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_query = "".join([c if c.isalnum() else "_" for c in args.query])
    output_file = os.path.join(output_dir, f"{clean_query}_{timestamp}.csv")
    
    df = pd.DataFrame(unique_data)
    df.to_csv(output_file, index=False)
    
    print(f"[Delivery] Success! Saved {len(unique_data)} NEW leads to {output_file}.")
    print("=== B.L.A.S.T Lead Gen Complete ===")

if __name__ == "__main__":
    main()
