import requests
import random
import time

_SEARX_INSTANCES = []

def get_searx_instances():
    global _SEARX_INSTANCES
    if not _SEARX_INSTANCES:
        try:
            print("[SearXNG] Fetching active public instances...")
            r = requests.get("https://searx.space/data/instances.json", timeout=10)
            data = r.json()
            # Filter for instances that support API, have decent scores, and aren't Google blocked
            valid = []
            for url, info in data.get("instances", {}).items():
                if info.get("network_type") == "normal" and info.get("error") is None:
                    timing = info.get("timing", {}).get("search", {}).get("all", {}).get("median", 9999)
                    if timing < 2.0:  # Respond under 2 seconds
                        valid.append(url)
                        
            _SEARX_INSTANCES = valid
            print(f"[SearXNG] Found {len(_SEARX_INSTANCES)} highly responsive public search instances.")
        except Exception as e:
            print(f"[SearXNG] Failed to fetch instances: {e}")
            _SEARX_INSTANCES = ["https://searx.be/", "https://search.ononoki.org/", "https://paulgo.io/"]
            
    return _SEARX_INSTANCES

def searx_search(query: str, target=10):
    instances = get_searx_instances()
    random.shuffle(instances)
    
    urls = []
    
    for instance in instances[:10]:
        # Using Google and Bing engines on the Searx instances for highest quality
        search_url = f"{instance}search?q={requests.utils.quote(query)}&format=json&engines=google,bing,duckduckgo"
        try:
            r = requests.get(search_url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                for res in data.get("results", []):
                    u = res.get("url")
                    if u and "http" in u:
                        urls.append(u)
                
                # If we got valid results, return them immediately
                if urls:
                    return list(set(urls))[:target]
        except Exception:
            continue
            
    return []

if __name__ == "__main__":
    print(searx_search("roofing contractors in austin", 25))
