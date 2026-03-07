# Extraction Standard Operating Procedure (SOP)

## Goal
Extract accurate, structured lead data from business URLs using Firecrawl.

## Inputs
- `url`: The business URL to scrape
- `schema`: The Pydantic JSON schema defining Name, Website, Description, Emails, Phones, Socials.

## Rules
1. **Firecrawl Endpoint**: Send requests to `http://localhost:3002/v1/scrape`.
2. **Extraction Format**: Use `formats: ["extract"]`, passing the prompt and JSON schema.
3. **Accuracy Check**: Only keep the lead if `Emails` or `Phones` is non-empty. A lead without contact info is not a "high quality lead".
4. **Concurrency**: Do not overwhelm the local Firecrawl. Use a max concurrency limit (e.g., 5 concurrent async jobs) to scrape the URLs. BROWSER_POOL_SIZE is 5 by default.

## Schema
```json
{
  "name": "string",
  "website": "string",
  "description": "string",
  "source_url": "string",
  "emails": ["string"],
  "phones": ["string"],
  "socials": ["string"]
}
```

## Tools
- `tools/firecrawl_client.py`

## Error Handling
- If Firecrawl fails or times out on a URL, log the error and skip.
- Do not let a single failed URL crash the entire run.
