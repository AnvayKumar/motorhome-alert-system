import os
import json
import xml.etree.ElementTree as ET
import requests
from datetime import datetime

DB_FILE = "seen_listings.txt"
HTML_FILE = "index.html"

# Pre-filtered endpoints targeting 4-Berth, Dealer Only, Under NZD $100k
TRADEME_RSS_URL = "https://www.trademe.co.nz/Browse/SearchResults.aspx?nav_perpage=50&cid=2983&user_type=dealer&price_max=100000&attribute_70_72=71&format=rss"
AUTOTRADER_API_URL = "https://www.autotrader.co.nz/api/search?bodyStyle=Motorhomes&priceTo=100000&seatsFrom=4&dealer=true"

def load_seen_listings():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            # We filter out raw numerical IDs from our previous test run safely
            parsed = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    # If it's modern JSON data, load it
                    parsed.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip the old numerical mock IDs from step 1
                    continue
            return parsed
    return []

def save_seen_listings(all_items):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        for item in all_items:
            f.write(json.dumps(item) + "\n")

def check_marketplaces():
    seen_db = load_seen_listings()
    seen_links = {item['link'] for item in seen_db}
    current_runs = []

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # ---- 1. TRADE ME ENGINE ----
    try:
        response = requests.get(TRADEME_RSS_URL, headers=headers, timeout=15)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for item in root.findall(".//item"):
                title = item.find("title").text
                link = item.find("link").text.split("?")[0]
                price = "Check Listing"
                desc = item.find("description")
                if desc is not None and "$" in desc.text:
                    try:
                        price = "$" + desc.text.split("$")[1].split()[0]
                    except: pass
                
                current_runs.append({"title": title, "link": link, "price": price, "source": "Trade Me"})
    except Exception as e:
        print(f"TradeMe Processing Error: {e}")

    # ---- 2. AUTOTRADER ENGINE ----
    try:
        response = requests.get(AUTOTRADER_API_URL, headers=headers, timeout=15)
        if response.status_code == 200:
            listings = response.json().get("listings", [])
            for item in listings:
                id_val = str(item.get("id"))
                title = f"{item.get('year', '')} {item.get('make', '')} {item.get('model', '')}".strip()
                price_raw = item.get("price", "Check Listing")
                price = f"${price_raw:,}" if isinstance(price_raw, (int, float)) else price_raw
                link = f"https://www.autotrader.co.nz/used-cars-for-sale/motorhomes/{id_val}"
                
                current_runs.append({"title": title, "link": link, "price": price, "source": "AutoTrader"})
    except Exception as e:
        print(f"AutoTrader Processing Error: {e}")

    # Process and build chronological catalog history
    new_discoveries = []
    for item in current_runs:
        if item['link'] not in seen_links:
            item['discovered_at'] = datetime.now().strftime("%d %b %Y, %I:%M %p")
            new_discoveries.append(item)
            seen_links.add(item['link'])

    # Merge fresh matches onto the top of the timeline stack
    updated_db = new_discoveries + seen_db
    save_seen_listings(updated_db)
    return updated_db

def generate_html(listings):
    timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p NZST")
    
    cards_html = ""
    if not listings:
        cards_html = "<div class='no-listings'>No motorhomes discovered matching your criteria yet. The scraper is monitoring...</div>"
    else:
        for item in listings:
            source_class = "source-trademe" if item['source'] == "Trade Me" else "source-autotrader"
            date_label = item.get('discovered_at', 'Existing Stock')
            cards_html += f"""
            <div class="card">
                <div class="card-header">
                    <span class="badge {source_class}">{item['source']}</span>
                    <span class="timestamp">Logged: {date_label}</span>
                </div>
                <h3 class="title">{item['title']}</h3>
                <div class="price">{item['price']}</div>
                <a href="{item['link']}" target="_blank" class="btn">Open Listing Details ↗</a>
            </div>
            """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>4-Berth Motorhomes (<$100k)</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }}
        .container {{ max-width: 650px; margin: 0 auto; }}
        header {{ text-align: center; margin-bottom: 25px; border-bottom: 2px solid #e1e4e8; padding-bottom: 15px; }}
        h1 {{ margin: 0; color: #1a202c; font-size: 22px; }}
        .meta {{ font-size: 13px; color: #718096; margin-top: 6px; }}
        .grid {{ display: grid; gap: 14px; grid-template-columns: 1fr; }}
        .card {{ background: white; border-radius: 8px; padding: 18px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); border: 1px solid #e1e4e8; display: flex; flex-direction: column; }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
        .badge {{ font-size: 10px; font-weight: bold; padding: 4px 8px; border-radius: 4px; text-transform: uppercase; }}
        .source-trademe {{ background-color: #deebff; color: #0747a6; }}
        .source-autotrader {{ background-color: #e3fcef; color: #006644; }}
        .timestamp {{ font-size: 11px; color: #a0aec0; }}
        .title {{ margin: 0 0 10px 0; font-size: 16px; color: #2d3748; line-height: 1.4; font-weight: 600; }}
        .price {{ font-size: 20px; font-weight: bold; color: #e53e3e; margin-bottom: 14px; }}
        .btn {{ text-decoration: none; background: #2b6cb0; color: white; text-align: center; padding: 10px; border-radius: 6px; font-weight: 500; font-size: 13px; transition: background 0.1s; margin-top: auto; }}
        .btn:hover {{ background: #2c5282; }}
        .no-listings {{ text-align: center; padding: 20px; color: #718096; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚐 4-Berth Motorhomes Dashboard</h1>
            <div class="meta">Targeting NZ Dealerships Under $100,000</div>
            <div class="meta"><b>Last Scanned:</b> {timestamp}</div>
        </header>
        <div class="grid">
            {cards_html}
        </div>
    </div>
</body>
</html>"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    listings_data = check_marketplaces()
    generate_html(listings_data)
