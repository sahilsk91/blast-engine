import subprocess
import sys

def prompt_input(prompt_text, default=None):
    if default:
        res = input(f"{prompt_text} [{default}]: ").strip()
        return res if res else default
    else:
        res = input(f"{prompt_text}: ").strip()
        while not res:
            res = input(f"Required. {prompt_text}: ").strip()
        return res

def main():
    print("\n" + "="*50)
    print("  B.L.A.S.T. Engine Cloud Dispatcher")
    print("="*50 + "\n")

    query = prompt_input("Enter Niche/Role (e.g. Dentists)")
    locations = prompt_input("Enter target cities (comma-separated, e.g. Miami, Orlando)")
    count = prompt_input("Target leads per city", "50")

    print("\n[+] Dispatching payload to GitHub Actions cluster...")
    
    cmd = [
        "gh", "workflow", "run", "blast-engine.yml",
        "-f", f"query={query}",
        "-f", f"locations={locations}",
        "-f", f"count={count}",
        "-f", "mode=V5 Horizontal Business Scrape (Standard)"
    ]

    try:
        subprocess.run(cmd, check=True)
        print("\n[SUCCESS] Cloud nodes have been provisioned and the engine is running.")
        print("Track live progress here: https://github.com/sahilsk91/blast-engine/actions")
    except subprocess.CalledProcessError:
        print("\n[FAILED] Failed to trigger cloud workflow. Ensure GitHub CLI (gh) is authenticated.")
        sys.exit(1)

if __name__ == "__main__":
    main()
