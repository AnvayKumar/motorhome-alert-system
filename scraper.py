import os
import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

DB_FILE = "seen_listings.txt"
HTML_FILE = "index.html"

# Actual web pages a human browser opens
TRADEME_URL = "https://www.trademe.co.nz/a/motors/caravans-motorhomes/motorhomes/search?user_type=dealer&price_max=100000&berths_min=4"
AUTOTRADER_URL = "https://www.autotrader.co.nz/used-cars-for-sale/motorhomes?priceTo=100000"

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

    # High-grade browser headers to bypass cloud firewalls
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }

    # ---- PARSE ENGINE 1: TRADE ME ----
    try:
        response = requests.get(TRADEME_URL, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract Trade Me's embedded application state data layer containing full page search results
            script_tag = soup.find('script', text=re.compile('tg-initial-state'))
            if script_tag:
                data_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', script_tag.string)
                if data_match:
                    state_json = json.loads(data_match.group(1))
                    listings = state_json.get('search', {}).get('results', {}).get('listings', [])
                    for l in listings:
                        id_val = l.get('listingId')
                        title = l.get('title', '')
                        price = l.get('priceDisplay', 'View Details')
                        link = f"https://www.trademe.co.nz/a/motors/caravans-motorhomes/motorhomes/listing/{id_val}"
                        current_runs.append({"title": title, "link": link, "price": price, "source": "Trade Me"})
            
            # Backup: Regex extraction directly out of document strings if JSON shifts
            if not current_runs:
                ids = re.findall(r'"listingId":\s*(\d+)', response.text)
                titles = re.findall(r'"title":\s*"([^"]+)"', response.text)
                for i in range(min(len(ids), len(titles))):
                    if not any(x in titles[i].lower() for x in ["motorhome", "caravan", "search"]):
                        link = f"https://www.trademe.co.nz/a/motors/caravans-motorhomes/motorhomes/listing/{ids[i]}"
                        current_runs.append({"title": titles[i], "link": link, "price": "View Details", "source": "Trade Me"})
    except Exception as e:
        print(f"TradeMe Extraction Error: {e}")

    # ---- PARSE ENGINE 2: AUTOTRADER ----
    try:
        response = requests.get(AUTOTRADER_URL, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Targets the container links for vehicles in AutoTrader's grid layout
            cards = soup.select('a[href*="/used-cars-for-sale/motorhomes/"]')
            
            for card in cards:
                href = card.get('href')
                link = f"https://www.autotrader.co.nz{href}" if not href.startswith('http') else href
                
                title_el = card.select_one('.card-title, h3, h4, .title')
                price_el = card.select_one('.price, .card-price, font')
                
                title = title_el.text.strip() if title_el else "Motorhome Listing"
                price = price_el.text.strip() if price_el else "View Details"
                
                # Dynamic exclusion of known 2-berth keywords
                t_lower = title.lower()
                if not any(x in t_lower for x in ["2-berth", "2 berth", "3 berth"]):
                    current_runs.append({"title": title, "link": link, "price": price, "source": "AutoTrader"})
    except Exception as e:
        print(f"AutoTrader Extraction Error: {e}")

    # Assemble and filter against historical database
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
        cards_html = "<div class='no-listings'>No active dealer 4-berth listings under $100k found. Standing by for updates...</div>"
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

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live Motorhome Feed</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f7fafc; margin: 0; padding: 20px; color: #2d3748; }}
        .container {{ max-width: 600px; margin: 0 auto; }}
        header {{ text-align: center; margin-bottom: 30px; background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }}
        h1 {{ margin: 0; color: #1a202c; font-size: 20px; }}
        .meta {{ font-size: 13px; color: #718096; margin-top: 5px; }}
        .grid {{ display: grid; gap: 16px; }}
        .card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.01), 0 2px 4px -1px rgba(0,0,0,0.01); border: 1px solid #e2e8f0; display: flex; flex-direction: column; }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
        .badge {{ font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .source-trademe {{ background-color: #ebf8ff; color: #2b6cb0; }}
        .source-autotrader {{ background-color: #f0fff4; color: #38a169; }}
        .timestamp {{ font-size: 12px; color: #a0aec0; }}
        .title {{ margin: 0 0 12px 0; font-size: 16px; color: #2d3748; line-height: 1.5; font-weight: 600; }}
        .price {{ font-size: 22px; font-weight: 800; color: #e53e3e; margin-bottom: 16px; }}
        .btn {{ text-decoration: none; background: #3182ce; color: white; text-align: center; padding: 12px; border-radius: 8px; font-weight: 600; font-size: 14px; }}
        .no-listings {{ text-align: center; padding: 30px; color: #718096; background: white; border-radius: 12px; border: 1px solid #e2e8f0; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚐 Live Motorhome Monitor</h1>
            <div class="meta">Trade Me & AutoTrader Live Scanning (Dealer 4-Berths Under $100k)</div>
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
    listings_data = check_marketplaces()
    generate_html(listings_data)
