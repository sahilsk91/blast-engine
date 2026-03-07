import asyncio
import aiohttp

async def test_url(url: str):
    print(f"\n[Test] Attempting to scrape {url}")
    payload = {"url": url, "formats": ["markdown"]}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:3002/v1/scrape", json=payload, timeout=45) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    md = data.get("data", {}).get("markdown", "")
                    print(f"✅ Success! Extracted {len(md)} chars.")
                    print(f"Sample: {md[:200]}")
                else:
                    text = await resp.text()
                    print(f"❌ Failed! Status: {resp.status} - {text}")
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    urls = [
        "https://www.yelp.com/biz/hub-plumbing-and-mechanical-new-york", # Yelp
        "https://www.google.com/maps/place/Hub+Plumbing+%26+Mechanical/@40.7186638,-74.0022415,17z/", # GMaps
        "https://www.yellowpages.com/new-york-ny/mip/hub-plumbing-mechanical-467645025" # YellowPages
    ]
    await asyncio.gather(*(test_url(u) for u in urls))

if __name__ == "__main__":
    asyncio.run(main())
