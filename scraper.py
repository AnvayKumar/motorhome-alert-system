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


def extract_listings(page):
    """
    Extract listings from the live rendered DOM.
    Uses multiple selector strategies because Trade Me
    changes class names frequently.
    """

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

            const lines = text
                .split('\\n')
                .map(l => l.trim())
                .filter(Boolean);

            const title = lines[0] || "Untitled";

            const priceMatch = text.match(/\\$[\\d,]+/);
            const price = priceMatch ? priceMatch[0] : "Price unavailable";

            results.push({
                title,
                price,
                url: href,
                summary: lines.slice(1, 6).join(' • ')
            });
        });

        return results;
    }
    """)

    # Remove obvious duplicates
    deduped = []
    seen_urls = set()

    for item in listings:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            deduped.append(item)

    return deduped


def build_html(listings):
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    cards = ""

    for item in listings:
        cards += f"""
        <div class="card">
            <h2>{item['title']}</h2>
            <p class="price">{item['price']}</p>
            <p>{item['summary']}</p>
            <a href="{item['url']}" target="_blank">View Listing</a>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <title>Trade Me Motorhomes</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f5f5f5;
                margin: 40px;
            }}

            h1 {{
                margin-bottom: 8px;
            }}

            .meta {{
                color: #666;
                margin-bottom: 30px;
            }}

            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
                gap: 20px;
            }}

            .card {{
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }}

            .card h2 {{
                font-size: 18px;
                margin-top: 0;
            }}

            .price {{
                font-size: 20px;
                font-weight: bold;
                color: #0a7d33;
            }}

            a {{
                display: inline-block;
                margin-top: 10px;
                text-decoration: none;
                color: #0057cc;
            }}
        </style>
    </head>
    <body>
        <h1>Trade Me Dealer Motorhomes</h1>
        <div class="meta">
            Generated: {generated}<br>
            Listings found: {len(listings)}
        </div>

        <div class="grid">
            {cards}
        </div>
    </body>
    </html>
    """


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
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

        # Give Cloudflare + JS time
        page.wait_for_timeout(8000)

        # Scroll to trigger lazy loading
        for _ in range(5):
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(1500)

        listings = extract_listings(page)

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
