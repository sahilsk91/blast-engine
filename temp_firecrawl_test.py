import asyncio
import time
from tools.firecrawl_client import extract_all_leads

# Explicit list of major London independent estate dealers and directories to prove Firecrawl works locally
urls = [
    "https://www.dexters.co.uk/",
    "https://www.foxtons.co.uk/",
    "https://www.savills.co.uk/",
    "https://www.knightfrank.co.uk/",
    "https://www.struttandparker.com/",
    "https://www.chestertons.co.uk/",
    "https://www.winkworth.co.uk/",
    "https://www.marshandparsons.co.uk/",
    "https://www.kinleigh.co.uk/",
    "https://www.johndwood.co.uk/"
]

print(f"\nGathered {len(urls)} London Real Estate Dealer URLs directly. \nStarting Firecrawl API Extraction via Localhost (Docker)...")

async def run_firecrawl():
    start_time = time.time()
    results = await extract_all_leads(urls)
    end_time = time.time()
    
    print("\n" + "="*50)
    print("=== FINAL FIRECRAWL EXTRACTED LONDON LEADS ===")
    print(f"Time Taken: {end_time - start_time:.2f} seconds")
    print("="*50)
    for r in results:
        print(f"Name: {r.name}")
        print(f"URL: {r.website}")
        if r.emails: print(f"Emails: {r.emails}")
        if r.phones: print(f"Phones: {r.phones}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(run_firecrawl())
