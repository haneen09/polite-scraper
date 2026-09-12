import requests
import os
from pathlib import Path

# Settings
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/haneen09/polite-scraper)"
TIMEOUT_SECONDS = 10
CACHE_DIR = Path(__file__).parent.parent / "cache"

def fetch_page(url, cache_filename):
    """
    Downloads a page and saves it to cache.
    If it's already cached, reads from the saved file instead.
    """
    cache_path = CACHE_DIR / cache_filename

    # If we already saved this page before, just read it from disk
    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        print(f"CACHE HIT — {cache_filename} ({len(html)} bytes)")
        return html

    # Otherwise, actually go fetch it from the internet
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)

    # Only proceed if the page actually loaded successfully
    if response.status_code != 200:
        raise Exception(f"Failed to fetch {url} — status code {response.status_code}")

    html = response.text

    # Save it to the cache folder for next time
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path.write_text(html, encoding="utf-8")

    print(f"FETCH — {cache_filename} ({len(html)} bytes)")
    return html


if __name__ == "__main__":
    url = "https://books.toscrape.com/catalogue/page-1.html"
    fetch_page(url, "catalogue-page-1.html")