import os
import json
from openai import OpenAI
import sys

def generate_dorks(niche: str, location: str, count: int = 50) -> list[str]:
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("[AI Dork Generator] ⚠️ WARNING: NVIDIA_API_KEY not found in environment.")
        return []
        
    print(f"[AI Dork Generator] Engaging NVIDIA Llama 3.1 to generate {count} micro-niche queries for '{niche}' in '{location}'...")
    
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )
    
    sys_prompt = f"""
    You are an expert lead generation query engineer. 
    The user wants to find independent businesses in the {niche} niche in {location}.
    Generate exactly {count} highly specific, long-tail search queries (Google/DuckDuckGo syntax).
    
    Rules:
    - Include specialized industry terms, sub-services, and specific certifications.
    - Vary the search intent (e.g., "official website", "contact us", "book an appointment").
    - Do NOT include any 'site:' operators. We will append aggregator exclusions later.
    - Do NOT include quotes around the entire string, just write the raw search string.
    - Make them realistic. (e.g. Instead of just 'plumber miami', use 'emergency leak detection miami official site').
    - You must respond ONLY with a valid JSON array of strings under the root key "queries". Do not include Markdown blocks.
    
    Example JSON Output:
    {{"queries": ["emergency leak detection miami official site", "miami commercial plumbing contractors", "licensed backflow testing miami fl"]}}
    """
    
    try:
        response = client.chat.completions.create(
            model="meta/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": sys_prompt}],
            temperature=0.7,
            max_tokens=2048,
        )
        
        raw_output = response.choices[0].message.content
        if "```json" in raw_output:
            raw_output = raw_output.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_output:
            raw_output = raw_output.split("```")[1].split("```")[0].strip()
            
        parsed = json.loads(raw_output)
        return parsed.get("queries", [])
    except Exception as e:
        print(f"[AI Dork Generator] ❌ NVIDIA API Error: {e}")
        return []

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    dorks = generate_dorks("Plumbers", "Miami", 10)
    print("\n=== GENERATED DORKS ===")
    for d in dorks:
        print(d)
