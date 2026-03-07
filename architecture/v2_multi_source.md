# V2 Architecture: Multi-Source Lead Generation (22+ Sources)

## The Constraint (Engineering Reality)
We performed a live test of our local Firecrawl instance against Yelp, YellowPages, and Google Maps.
- **Yelp:** Blocked (0 chars extracted).
- **YellowPages:** Blocked (Hit Cloudflare "malicious bot" page).
- **Google Maps:** Returns UI noise, and Maps does not expose emails natively anyway.

**Rule Check:** Directly scraping 22+ major directories (Angi, Thumbtack, BBB, Yelp) with standard open-source tools will result in instant Cloudflare bans and infinite retry loops.

## Proposed Strategies

To achieve the goal of extracting leads from these 22 sources, we must choose one of the following architectural paths:

### Option A: The "SERP Dorking" Method (Free & Local)
Instead of scraping Yelp directly, we use Google/DuckDuckGo to search *inside* Yelp.
1. Query: `site:yelp.com "plumbers in new york"`
2. We parse the SERP titles to get the business names (e.g., "Hub Plumbing & Mechanical").
3. We run a second query for `"Hub Plumbing & Mechanical New York official website"`.
4. We feed that official website into Firecrawl to get the email/phone.
*Pros:* 100% Free. Bypasses Cloudflare on directories.
*Cons:* Slower, requires more search engine API calls (prone to rate limits).

### Option B: The Aggregator API Route (Production Grade)
We integrate a specialized Maps/Directory API (like Outscraper, Apify, or RapidAPI Google Maps/Yelp APIs).
1. We call the API to fetch 50-500 business names, phone numbers, and website URLs from GMaps/Yelp perfectly formatted.
2. We feed the `website` URL array into our existing Firecrawl `extract_all` tool to fetch the missing emails and social links.
*Pros:* Extremely reliable, returns data instantly, no bot-blocks.
*Cons:* Requires you to sign up for a 3rd party API key (many offer generous free tiers).

### Option C: Custom Playwright Stealth Scraper (High Maintenance)
We bypass Firecrawl entirely for the directories and build a custom Python `Playwright` script with stealth plugins specifically tailored for Google Maps DOM parsing.
*Pros:* Free, highly targeted.
*Cons:* Extremely brittle. Google changes CSS selectors weekly. High maintenance cost.

---
**Recommendation:** I strongly advise against Option C due to long-term maintenance costs. Option A is best if keeping it 100% free is the priority. Option B is best if you want high-scale, production-ready reliability.
