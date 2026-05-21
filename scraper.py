from playwright.sync_api import sync_playwright
from datetime import datetime
import pathlib
import json

SEARCH_URL = (
    "https://www.trademe.co.nz/a/motors/"
    "caravans-motorhomes/motorhomes/search"
    "?user_type=dealer&price_max=100000&berths_min=4"
)

OUTPUT_HTML = "index.html"
SEEN_FILE = "seen_listings.txt"


def load_seen_urls():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f.readlines())
    except FileNotFoundError:
        return set()


def save_seen_urls(urls):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        for url in sorted(urls):
            f.write(url + "\n")


def extract_listings(page):
    page.wait_for_timeout(5000)

    listings = page.evaluate("""
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

            const lines = text
                .split('\\n')
                .map(l => l.trim())
                .filter(Boolean);

            const title =
                lines.find(l =>
                    l.match(/(Toyota|Ford|Mercedes|Fiat|Kea|Transit|Camper)/i)
                ) || lines[0] || "Untitled";

            const priceMatch = text.match(/\\$[\\d,]+/);
            const price = priceMatch ? priceMatch[0] : "Price unavailable";

            const img =
                container.querySelector('img')?.src || "";

            let seller_type = "Dealer";

            if (text.toLowerCase().includes("private seller")) {
                seller_type = "Private Seller";
            }

            results.push({
                title,
                price,
                url: href,
                summary: lines.slice(1, 8).join(' • '),
                image: img,
                seller_type
            });
        });

        return results;
    }
    """)

    deduped = []
    seen_urls = set()

    for item in listings:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            deduped.append(item)

    return deduped


def generate_cards(items):
    cards = ""

    for item in items:
        new_badge = (
            "<span class='badge'>NEW</span>"
            if item.get("is_new")
            else ""
        )

        image_html = (
            f"<img src='{item['image']}' class='thumb' />"
            if item.get("image")
            else ""
        )

        cards += f"""
        <div class="card">
            {image_html}

            <div class="header-row">
                <h2>{item['title']}</h2>
                {new_badge}
            </div>

            <p class="price">{item['price']}</p>

            <p class="seller">{item['seller_type']}</p>

            <p class="summary">{item['summary']}</p>

            <a href="{item['url']}" target="_blank">
                View Listing
            </a>
        </div>
        """

    return cards


def build_html(listings):
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    dealers = [
        x for x in listings
        if x["seller_type"] == "Dealer"
    ]

    private = [
        x for x in listings
        if x["seller_type"] == "Private Seller"
    ]

    dealer_cards = generate_cards(dealers)
    private_cards = generate_cards(private)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />

        <title>Trade Me Motorhomes</title>

        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f4f6f8;
                margin: 0;
                padding: 30px;
                color: #222;
            }}

            .container {{
                max-width: 1400px;
                margin: auto;
            }}

            h1 {{
                margin-bottom: 8px;
                font-size: 42px;
            }}

            .meta {{
                color: #666;
                margin-bottom: 40px;
                font-size: 15px;
            }}

            h2.section-title {{
                margin-top: 50px;
                margin-bottom: 20px;
                font-size: 28px;
            }}

            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
                gap: 24px;
            }}

            .card {{
                background: white;
                border-radius: 18px;
                overflow: hidden;
                box-shadow: 0 4px 16px rgba(0,0,0,0.08);
                transition: 0.2s ease;
            }}

            .card:hover {{
                transform: translateY(-4px);
                box-shadow: 0 8px 24px rgba(0,0,0,0.12);
            }}

            .card-content {{
                padding: 20px;
            }}

            .thumb {{
                width: 100%;
                height: 240px;
                object-fit: cover;
                background: #ddd;
            }}

            .header-row {{
                display: flex;
                justify-content: space-between;
                align-items: start;
                gap: 12px;
                padding: 20px 20px 0;
            }}

            .header-row h2 {{
                font-size: 22px;
                margin: 0;
                line-height: 1.3;
            }}

            .badge {{
                background: #ff4d4f;
                color: white;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 10px;
                border-radius: 999px;
                white-space: nowrap;
            }}

            .price {{
                font-size: 30px;
                font-weight: bold;
                color: #0a7d33;
                margin: 14px 20px;
            }}

            .seller {{
                margin: 0 20px;
                color: #0057cc;
                font-weight: bold;
            }}

            .summary {{
                margin: 18px 20px;
                color: #444;
                line-height: 1.5;
                min-height: 100px;
            }}

            a {{
                display: inline-block;
                margin: 0 20px 24px;
                text-decoration: none;
                font-weight: bold;
                color: #0057cc;
            }}

            a:hover {{
                text-decoration: underline;
            }}

            @media (max-width: 700px) {{
                body {{
                    padding: 16px;
                }}

                h1 {{
                    font-size: 30px;
                }}

                .grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>

    <body>
        <div class="container">

            <h1>🚐 Trade Me Motorhomes</h1>

            <div class="meta">
                Generated: {generated}<br>
                Total Listings: {len(listings)}
            </div>

            <h2 class="section-title">
                🚐 Dealer Listings ({len(dealers)})
            </h2>

            <div class="grid">
                {dealer_cards}
            </div>

            <h2 class="section-title">
                👤 Private Sellers ({len(private)})
            </h2>

            <div class="grid">
                {private_cards}
            </div>

        </div>
    </body>
    </html>
    """


def main():
    seen_urls = load_seen_urls()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            slow_mo=100,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 2200},
            locale="en-NZ"
        )

        page = context.new_page()

        print("Opening Trade Me...")

        page.goto(
            SEARCH_URL,
            wait_until="domcontentloaded",
            timeout=120000
        )

        page.wait_for_timeout(8000)

        for _ in range(5):
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(1500)

        page.screenshot(path="debug.png", full_page=True)

        listings = extract_listings(page)

        for item in listings:
            item["is_new"] = item["url"] not in seen_urls

        all_urls = set(seen_urls)

        for item in listings:
            all_urls.add(item["url"])

        save_seen_urls(all_urls)

        print(f"Found {len(listings)} listings")

        html = build_html(listings)

        pathlib.Path(OUTPUT_HTML).write_text(
            html,
            encoding="utf-8"
        )

        pathlib.Path("listings.json").write_text(
            json.dumps(listings, indent=2),
            encoding="utf-8"
        )

        browser.close()

        print(f"Saved {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
