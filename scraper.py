from playwright.sync_api import sync_playwright
import pathlib
import json
import hashlib
from datetime import datetime

SEARCH_URL = (
    "https://www.trademe.co.nz/a/motors/"
    "caravans-motorhomes/motorhomes/search"
    "?user_type=dealer&price_max=100000&berths_min=4"
)

LISTINGS_JSON = "listings.json"
SEEN_FILE = "seen_listings.txt"
HASH_FILE = ".last_hash"


def load_seen_urls():
    try:
        return set(
            pathlib.Path(SEEN_FILE).read_text(encoding="utf-8").splitlines()
        )
    except FileNotFoundError:
        return set()


def save_seen_urls(urls):
    pathlib.Path(SEEN_FILE).write_text(
        "\n".join(sorted(urls)),
        encoding="utf-8"
    )


def generate_hash(data):
    normalized = json.dumps(data, sort_keys=True)
    return hashlib.md5(normalized.encode()).hexdigest()


def load_previous_hash():
    try:
        return pathlib.Path(HASH_FILE).read_text().strip()
    except FileNotFoundError:
        return None


def save_hash(value):
    pathlib.Path(HASH_FILE).write_text(value)


def extract_listings(page):
    page.wait_for_timeout(5000)

    return page.evaluate("""
    () => {
        const results = [];
        const anchors = Array.from(document.querySelectorAll('a[href*="/listing/"]'));
        const seen = new Set();

        anchors.forEach(a => {
            const href = a.href;
            if (!href || seen.has(href)) return;
            seen.add(href);

            const container =
                a.closest('[class*="card"]') ||
                a.closest('li') ||
                a.closest('div');

            const text = container ? container.innerText : a.innerText;
            if (!text || text.length < 20) return;
            if (!text.toLowerCase().includes("berth")) return;

            const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);

            const title =
                lines.find(l => /(Toyota|Ford|Mercedes|Fiat|Kea|Transit|Camper)/i.test(l))
                || lines[0]
                || "Untitled";

            const priceMatches = [...text.matchAll(/\$[\d,]+/g)]
                .map(m => m[0]);

            // filter out obvious "fake prices"
            const filtered = priceMatches.filter(p => {
                const num = parseInt(p.replace(/[$,]/g, ""));
                return num > 10000; // motorhomes threshold (filters deposits/offers)
            });

            const price = filtered.length
                ? filtered[0]
                : (priceMatches[0] || "0");

            const img = container?.querySelector('img')?.src || "";

            let seller_type = text.toLowerCase().includes("private seller")
                ? "Private Seller"
                : "Dealer";

            results.push({
                title,
                price,
                url: href,
                summary: lines.slice(1, 6).join(" • "),
                image: img,
                seller_type
            });
        });

        return results;
    }
    """)


def normalize_items(items):
    cleaned = []
    seen = set()

    for item in items:
        if item["url"] in seen:
            continue
        seen.add(item["url"])

        price_digits = "".join(c for c in item["price"] if c.isdigit())
        price_numeric = int(price_digits) if price_digits else 0

        cleaned.append({
            **item,
            "id": hashlib.md5(item["url"].encode()).hexdigest(),
            "price_numeric": price_numeric,
            "is_new": False
        })

    return cleaned


def main():
    seen_urls = load_seen_urls()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 2200},
            locale="en-NZ"
        )
        page = context.new_page()

        print("Loading Trade Me...")
        page.goto(SEARCH_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(8000)

        for _ in range(5):
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(1200)

        listings = extract_listings(page)
        browser.close()

    for item in listings:
        item["is_new"] = item["url"] not in seen_urls

    listings = normalize_items(listings)

    current_hash = generate_hash(listings)
    previous_hash = load_previous_hash()

    if current_hash == previous_hash:
        print("No changes detected.")
        return

    all_urls = seen_urls.union({x["url"] for x in listings})
    save_seen_urls(all_urls)

    pathlib.Path(LISTINGS_JSON).write_text(
        json.dumps(listings, indent=2),
        encoding="utf-8"
    )

    save_hash(current_hash)

    print("Updated listings.json")


if __name__ == "__main__":
    main()
