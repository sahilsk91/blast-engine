import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))

import asyncio
import aiohttp
from tools.firecrawl_client import _fetch_markdown

async def main():
    async with aiohttp.ClientSession() as session:
        # Example URL from OpenCorporates
        url = "https://opencorporates.com/companies/us_fl/P06000015172"
        md = await _fetch_markdown(url, session)
        print("MD LENGTH:", len(md))
        print("MD CONTENT preview:", md[:500])

asyncio.run(main())
