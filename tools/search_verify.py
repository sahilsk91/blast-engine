import subprocess
import sys
import os

print("Testing DuckDuckGo Search...")
try:
    from ddgs import DDGS
    with DDGS() as ddgs:
        results = [r for r in ddgs.text("plumbers in new york", max_results=5)]
        print(f"DDGS success: found {len(results)} results")
        if results:
            print(f"Sample: {results[0]}")
except Exception as e:
    print(f"DDGS failed: {e}")

print("\nTesting Google Search...")
try:
    from googlesearch import search
    results = list(search("plumbers in new york", num_results=5, lang="en"))
    print(f"Google Search success: found {len(results)} results")
    if results:
        print(f"Sample: {results[0]}")
except Exception as e:
    print(f"Google Search failed: {e}")

print("\nLink Phase Search Verification Complete.")
