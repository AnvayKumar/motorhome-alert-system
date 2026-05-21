import os

def run_scraper():
    print("--- Starting Motorhome Alert System Scraper ---")
    
    # 1. This is where our real scraping logic will go later.
    # For now, we are simulating finding 2 motorhome listings.
    mock_listings = [
        {"id": "12345", "title": "2015 Fiat Ducato 4-Berth", "price": "$85,000", "url": "https://example.com/listing/12345"},
        {"id": "67890", "title": "2018 Ford Transit Camper", "price": "$95,000", "url": "https://example.com/listing/67890"}
    ]
    
    # 2. Load the listings we've already seen in the past
    seen_file = "seen_listings.txt"
    seen_ids = set()
    if os.path.exists(seen_file):
        with open(seen_file, "r") as f:
            seen_ids = set(line.strip() for line in f if line.strip())
            
    # 3. Figure out what is brand new
    new_listings = []
    for item in mock_listings:
        if item["id"] not in seen_ids:
            new_listings.append(item)
            
    # 4. If there's a new listing, log it and add it to our seen file
    if new_listings:
        print(f"Found {len(new_listings)} NEW listings!")
        with open(seen_file, "a") as f:
            for item in new_listings:
                print(f"ALERT: {item['title']} - {item['price']} ({item['url']})")
                f.write(f"{item['id']}\n")
    else:
        print("No new listings found this run.")
        
    print("--- Scraper finished successfully ---")

if __name__ == "__main__":
    run_scraper()
