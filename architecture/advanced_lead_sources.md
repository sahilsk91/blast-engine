# Advanced Lead Generation Architecture

## Core Philosophy
To build the ultimate global lead engine, we must graduate from naive Search Engine Dorking to a multi-tiered enrichment pipeline. We do not just find names; we build comprehensive dossiers.

## 1. The Multi-Tiered Approach

### Tier 1: The "Wide Net" (Discovery)
*   **Google Maps / Places API (or unofficial equivalents like Outscraper):** Best for local businesses (plumbers, dentists). Yields highly accurate Names, Addresses, Phones, and Website URLs.
*   **LinkedIn Company/People X-Ray:** Best for B2B and specific roles (e.g., "Vice President of Marketing in London").
    *   *Dorking Pattern:* `site:linkedin.com/in "Vice President of Marketing" "London" -"Dir"`
*   **Industry-Specific Directories (Targeted Scrapes):**
    *   Software/Tech: G2, Capterra, Crunchbase.
    *   Trades/Local: Trustpilot, Checkatrade (UK), Houzz (Architects/Builders).
    *   Real Estate: Zillow, Realtor.com.

### Tier 2: The "Deep Dive" (Enrichment)
Once we have a Website or a Company Name, we enrich it:
*   **OpenCorporates / Companies House (UK) / SEC (US):** (As per KI) Fetch legal entity data, exact registered addresses, and crucially, the names of active Directors/Officers.
*   **Hunter.io / Snov.io / Apollo (or Open-Source equivalents):** Domain-level email discovery. If we have `acme.com`, we find the email pattern (e.g., `first.last@acme.com`) and verify it.
*   **Firecrawl (Deep Scrape):** Scrape the target company's "About Us", "Contact", and "Team" pages to extract unstructured emails, phone numbers, and employee names.

### Tier 3: The "Verification" (Quality Control)
A lead is useless if the email bounces or the phone is disconnected.
*   **SMTP Email Verification:** Ping the mail server to check if the exact inbox exists (without sending an email).
*   **Catch-all Domain Detection:** Flag domains that accept all emails (risky for cold outreach).
*   **Phone Number Formatting & Type Checking:** Determine if a number is Mobile, Landline, or VoIP (useful for SMS vs. Cold Call strategies).

## 2. Global Niche Strategies

### B2B (Corporate/SaaS)
*   *Primary:* LinkedIn X-Ray + Domain Email Pattern Matching + Crunchbase.
*   *High-Value:* OpenCorporates for Director names.

### B2C / Local Trades
*   *Primary:* Google Maps + Yelp (via Stealth/Proxies) + Facebook Pages.
*   *High-Value:* Direct scraping of their local websites for mobile numbers.

### E-commerce
*   *Primary:* BuiltWith/Wappalyzer (find stores using Shopify/WooCommerce) + Instagram/TikTok bio scraping.

## 3. The B.L.A.S.T Implementation Path

To implement this, we need to expand the `A` (Architect) and `tools/` layers:

1.  **`tools/maps_extractor.py`**: A dedicated scraper for Google Maps data (high-quality local leads).
2.  **`tools/linkedin_xray.py`**: Specialized X-Ray logic specifically tuned for LinkedIn profiles, extracting names, current roles, and locations.
3.  **`tools/registry_extractor.py`**: (Already identified in KI) Pulling director/officer info from corporate registries.
4.  **`tools/enrichment_engine.py`**: A master script that takes a basic lead (Name + Website) and runs it through the Deep Dive (Tier 2) and Verification (Tier 3) steps.

## Next Steps for User Decision
We need to agree on which of these advanced avenues to build first based on the immediate goal.
