# Search Standard Operating Procedure (SOP)

## Goal
Reliably fetch 50 high-quality business URLs from search engines without triggering IP bans.

## Inputs
- `query`: The search keyword (e.g., "plumbers in New York")
- `num_results`: Target number of leads (default 50)
- `sources`: List of engines to use (e.g., `["ddg", "google"]`)

## Rules
1. **Fallback Strategy**: Always try DuckDuckGo (`ddgs`) first as it is historically less restrictive. If it fails or returns `< 50` URLs, fallback to Google (`googlesearch-python`).
2. **De-duplication**: Maintain a `set()` of scraped URLs to avoid redundant hits in the payload.
3. **Filtering**: Exclude directory sites (yelp, yellowpages, angi, thumbtack) from the results to ensure we scrape actual business websites, not aggregator pages.
4. **Rate Limiting**: Add a sleep of 1-3 seconds between paginated search queries. Keep batch size around 10-20 per query pagination.

## Tools
- `tools/search_engine.py`

## Error Handling
- If an engine throws a rate limit error, immediately fallback to the next engine in the list.
- If all engines error out before reaching 50 leads, return what was found with a warning.
