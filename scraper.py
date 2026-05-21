import os
import json
import xml.etree.ElementTree as ET
import requests
from datetime import datetime

DB_FILE = "seen_listings.txt"
HTML_FILE = "index.html"

# Broad feed query to ensure Cloudflare doesn't block the connection
TRADEME_RSS = "https://www.trademe.co.nz/Browse/SearchResults.aspx?nav_perpage=50&cid=2983&user_type=dealer&price_max=100000&format=rss"

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

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        response = requests.get(TRADEME_RSS, headers=headers, timeout=15)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for item in root.findall(".//item"):
                title = item.find("title").text
                link = item.find("link").text.split("?")[0]
                
                price = "View Listing"
                desc = item.find("description")
                if desc is not None and "$" in desc.text:
                    try:
                        price = "$" + desc.text.split("$")[1].split()[0]
                    except: pass
                
                # Check for any variation of 4-berth inside the title text locally
                title_lower = title.lower()
                if any(x in title_lower for x in ["4 berth", "4-berth", "4berth", "4 bth", "voyager"]):
                    current_runs.append({
                        "title": title, 
                        "link": link, 
                        "price": price, 
                        "source": "Trade Me"
                    })
    except Exception as e:
        print(f"Extraction Error: {e}")

    # Process seen tracking
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
        cards_html = "<div class='no-listings'>Monitoring live Trade Me feeds for 4-Berth stock... Updates update automatically.</div>"
    else:
        for item in listings:
            date_label = item.get('discovered_at', 'Active Stock')
            cards_html += f"""
            <div class="card">
                <div class="card-header">
                    <span class="badge source-trademe">{item['source']}</span>
                    <span class="timestamp">{date_label}</span>
                </div>
                <h3 class="title">{item['title']}</h3>
                <div class="price">{item['price']}</div>
                <a href="{item['link']}" target="_blank" class="btn">View Live Vehicle ↗</a>
            </div>
            """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Motorhome Feed</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f7fafc; margin: 0; padding: 20px; color: #2d3748; }}
        .container {{ max-width: 600px; margin: 0 auto; }}
        header {{ text-align: center; margin-bottom: 30px; background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; }}
        h1 {{ margin: 0; color: #1a202c; font-size: 20px; }}
        .meta {{ font-size: 13px; color: #718096; margin-top: 5px; }}
        .grid {{ display: grid; gap: 16px; }}
        .card {{ background: white; border-radius: 12px; padding: 20px; border: 1px solid #e2e8f0; display: flex; flex-direction: column; }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
        .badge {{ font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px; text-transform: uppercase; }}
        .source-trademe {{ background-color: #ebf8ff; color: #2b6cb0; }}
        .timestamp {{ font-size: 12px; color: #a0aec0; }}
        .title {{ margin: 0 0 12px 0; font-size: 16px; color: #2d3748; font-weight: 600; }}
        .price {{ font-size: 22px; font-weight: 800; color: #e53e3e; margin-bottom: 16px; }}
        .btn {{ text-decoration: none; background: #3182ce; color: white; text-align: center; padding: 12px; border-radius: 8px; font-weight: 600; font-size: 14px; }}
        .no-listings {{ text-align: center; padding: 30px; color: #718096; background: white; border-radius: 12px; border: 1px solid #e2e8f0; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚐 Live Motorhome Monitor</h1>
            <div class="meta">Monitoring Dealer 4-Berths Under $100k</div>
            <div class="meta"><b>Last System Scan:</b> {timestamp}</div>
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
    generate_html(check_marketplaces())
