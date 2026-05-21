import os
import requests

def debug_scan():
    print("=== STARTING DIAGNOSTIC NETWORK SCAN ===")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Test AutoTrader API
    try:
        at_url = "https://www.autotrader.co.nz/api/search?bodyStyle=Motorhomes&priceTo=100000"
        at_res = requests.get(at_url, headers=headers, timeout=10)
        print(f"AutoTrader HTTP Status Code: {at_res.status_code}")
        print(f"AutoTrader Raw Content Snippet (First 200 chars): {at_res.text[:200]}")
    except Exception as e:
        print(f"AutoTrader Network Crash: {e}")
        
    print("-" * 50)
    
    # Test TradeMe Web View
    try:
        tm_url = "https://www.trademe.co.nz/a/motors/caravans-motorhomes/motorhomes/search?user_type=dealer&price_max=100000&berths_min=4"
        tm_res = requests.get(tm_url, headers=headers, timeout=10)
        print(f"TradeMe HTTP Status Code: {tm_res.status_code}")
        print(f"TradeMe Raw Content Snippet (First 200 chars): {tm_res.text[:200]}")
    except Exception as e:
        print(f"TradeMe Network Crash: {e}")
        
    print("=== DIAGNOSTIC SCAN COMPLETE ===")

    # Write a plain message to the HTML file so we know it updated
    with open("index.html", "w") as f:
        f.write("<h1>System diagnostic complete. Check your GitHub Actions console log for details.</h1>")

if __name__ == "__main__":
    debug_scan()
