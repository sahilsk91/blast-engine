# Project Constitution

## Data Schemas
### Input Schema (Query)
```json
{
  "keywords": "business type",
  "location": "city or area",
  "num_leads": 50,
  "sources": ["ddg", "google", "yelp"]
}
```

### Output Schema (Omni-Lead Payload)
```json
{
  "entity_type": "Person | Company",
  "name": "Jane Doe | Acme Inc",
  "title_or_description": "Marketing Director | Plumbing services",
  "website_or_social": "https://linkedin.com/in/janedoe",
  "source_url": "https://source.com/acme",
  "emails": ["jane@gmail.com"],
  "phones": ["+1-555-5555"]
}
```

## Behavioral Rules
- **Accurate Leads Only**: Filter out generic/irrelevant results.
- **Stealth Mode (Zero-Cost)**: Never scrape protected directories (LinkedIn, Yelp) directly. Use X-Ray SERP Dorking to pull emails from Google/DDG cache snippets.
- **Batch Size**: Target as many unique leads as possible, respecting strict rate limits to avoid IP bans.
- **Polite Crawling**: High delays (2-5s) on X-Ray queries to prevent CAPTCHAs.
- **Error Resilience**: Do not crash on a single website failure. Retry gracefully.
- **Firecrawl**: Use the local open-source instance, fallback to SDK tools if available.
- **Delivery**: Export to CSV with normalized columns.

## Architectural Invariants
- 3-Layer Architecture (A.N.T.):
  - Layer 1: Architecture (SOPs in `architecture/`)
  - Layer 2: Navigation (Decision Making structure)
  - Layer 3: Tools (`tools/` - Deterministic Python scripts)
- B.L.A.S.T. Protocol is strictly followed.
- Data-First: No code until Payload shape is confirmed.
