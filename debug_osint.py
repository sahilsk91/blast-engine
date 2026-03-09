from tools.domain_enrichment import lookup_domain_emails

test_urls = [
    "https://stripe.com",
    "https://openai.com",
    "https://godaddy.com",
    "https://aws.amazon.com"
]

print("=== Starting Local OSINT Dry Run ===")
for url in test_urls:
    print(f"\nProcessing: {url}")
    try:
        results = lookup_domain_emails(url)
        print(f"Results for {url}: {results}")
    except Exception as e:
        print(f"CRITICAL FAILURE on {url}: {str(e)}")
print("=== Finished ===")
