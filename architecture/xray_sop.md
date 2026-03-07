# V3 Architecture: Stealth Omni-Extractor (Zero-Cost SERP Dorking)

## The Objective
Extract targeted emails from *any* niche or specific person (e.g., LinkedIn profiles, specific companies) without triggering anti-bot walls or paying for Data Broker APIs.

## The Problem
Scraping LinkedIn, Yelp, or Facebook directly using Firecrawl is impossible without paid rotating residential proxies + headless authenticated browser sessions.

## The Solution: SERP Snippet Scraping (X-Raying)
Search engines (Google/DuckDuckGo) cache the preview text (snippets) of web pages. Often, people put their emails in their LinkedIn bios or Twitter bios, and Google caches it in the search result snippet.

We can extract the email *directly from the Google/DDG Search Result Page (SERP)* without actually visiting the underlying `linkedin.com` link.

### 1. The Dork Generator
When the user asks for "Marketing Directors in London", the engine translates this into a highly specific boolean query called a "Dork":
`site:linkedin.com/in "Marketing Director" "London" ("@gmail.com" OR "@hotmail.com" OR "@yahoo.com" OR "@outlook.com")`

### 2. The Execution Flow
1. **Dorking (Layer 3: `xray_search.py`)**: Execute the Dork queries on DuckDuckGo and Google.
2. **Snippet Parsing**: Instead of just extracting the URL, the python script extracts the *body definition snippet* of the search result.
3. **Regex Pass**: Run our email and phone regex algorithms *on the snippet text*.
4. **Outcome**: We get the Name, Role, LinkedIn URL, and Email, completely circumventing LinkedIn's bot protection because we only queried DuckDuckGo/Google.

## Rate Limit Constraints (The Reality Check)
Google and DuckDuckGo will flag X-Ray queries as bot traffic much faster than normal queries.
- We must use high delays (`time.sleep(3)`) between SERP pages.
- We must rotate User-Agents on every request.
- The volume will be lower than V2 (maybe 20-30 leads per run instead of 100), but the *quality and precision* (specific roles/individuals) will be infinitely higher.
