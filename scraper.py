import os
import json
import requests
from datetime import datetime

DB_FILE = "seen_listings.txt"
HTML_FILE = "index.html"

# Direct unblocked open endpoint for motorhomes
TRADEME_API = "https://api.trademe.co.nz/v1/Search/Motors/Caravans-motorhomes/Motorhomes.json?user_type=dealer&price_max=100000&berths_min=4&rows=50"

def load_seen_listings():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return [json.loads(line.strip()) for line in f if line.strip()]
    return []

def save_seen_listings(all_items):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        for item in all_items:
            f.write(json.dumps(item) + "\n")

def check_marketplaces():
    seen_db = load_seen_listings()
    seen_links = {item['link'] for item in seen_db}
    current_runs = []

    # 1. TRADE ME ENGINE
    try:
        response = requests.get(TRADEME_API, timeout=15)
        if response.status_code == 200:
            data = response.json()
            listings = data.get("List", [])
            for item in listings:
                title = item.get("Title", "")
                listing_id = item.get("ListingId", "")
                price = item.get("PriceDisplay", "View Details")
                link = f"https://www.trademe.co.nz/a/motors/caravans-motorhomes/motorhomes/listing/{listing_id}"
                
                current_runs.append({
                    "title": title,
                    "link": link,
                    "price": price,
                    "source": "Trade Me"
                })
    except Exception as e:
        print(f"Trade Me API Error: {e}")

    # 2. AUTOTRADER ENGINE (FALLBACK SECURE DATA PIPELINE)
    try:
        # Utilizing standard feed relay to collect matching assets without blocking
        at_url = "https://www.autotrader.co.nz/used-cars-for-sale/motorhomes"
        res = requests.get(at_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if res.status_code == 200:
            # Simple string search fallback to grab items safely
            import re
            links = re.findall(r'href="(/used-cars-for-sale/motorhomes/[^"]+)"', res.text)
            titles = re.findall(r'class="[^"]*card-title[^"]*">([^<]+)', res.text)
            for i in range(min(len(titles), len(links))):
                full_link = f"https://www.autotrader.co.nz{links[i]}"
                t_text = titles[i].strip()
                if not any(x in t_text.lower() for x in ["2-berth", "2 berth", "3 berth"]):
                    current_runs.append({
                        "title": t_text,
                        "link": full_link,
                        "price": "Check Site",
                        "source": "AutoTrader"
                    })
    except Exception as e:
        print(f"AutoTrader Error: {e}")

    # Update database
    new_discoveries = []
    for item in current_runs:
        if item['link'] not in seen_links:
            item['discovered_at'] = datetime.now().strftime("%d %b %Y, %I:%M %p")
            new_discoveries.append(item)
            seen_links.add(item['link'])

    updated_db = new_discoveries + seen_db
    save_seen_listings(updated_db)
    return updated_db

def generate_html(listings):
    timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p NZST")
    cards_html = ""
    
    if not listings:
        cards_html = "<div class='no-listings'>Waiting for listings to populate. Checking live data stream...</div>"
    else:
        for item in listings:
            source_class = "source-trademe" if item['source'] == "Trade Me" else "source-autotrader"
            date_label = item.get('discovered_at', 'Active Listing')
            cards_html += f"""
            <div class="card">
                <div class="card-header">
                    <span class="badge {source_class}">{item['source']}</span>
                    <span class="timestamp">{date_label}</span>
                </div>
                <h3 class="title">{item['title']}</h3>
                <div class="price">{item['price']}</div>
                <a href="{item['link']}" target="_blank" class="btn">View Live Vehicle ↗</a>
            </div>
            """

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live Vehicle Feed</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f7fafc; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; }}
        header {{ text-align: center; background: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #e2e8f0; }}
        h1 {{ margin: 0; font-size: 20px; }}
        .card {{ background: white; border-radius: 12px; padding: 20px; margin-bottom: 16px; border: 1px solid #e2e8f0; }}
        .card-header {{ display: flex; justify-content: space-between; margin-bottom: 12px; }}
        .badge {{ font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px; }}
        .source-trademe {{ background: #ebf8ff; color: #2b6cb0; }}
        .source-autotrader {{ background: #f0fff4; color: #38a169; }}
        .price {{ font-size: 22px; font-weight: 800; color: #e53e3e; margin-bottom: 12px; }}
        .btn {{ display: block; text-decoration: none; background: #3182ce; color: white; text-align: center; padding: 12px; border-radius: 8px; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚐 Live Motorhome Monitor</h1>
            <p><b>Last Update:</b> {timestamp}</p>
        </header>
        {cards_html}
    </div>
</body>
</html>""")

if __name__ == "__main__":
    generate_html(check_marketplaces())
