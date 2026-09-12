import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/haneen09/polite-scraper)"
TIMEOUT_SECONDS = 10
CACHE_DIR = Path(__file__).parent.parent / "cache"
BASE_URL = "https://books.toscrape.com/catalogue/"


def fetch_page(url, cache_filename):
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        print(f"CACHE HIT — {cache_filename} ({len(html)} bytes)")
        return html

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch {url} — status code {response.status_code}")

    html = response.text
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path.write_text(html, encoding="utf-8")

    print(f"FETCH — {cache_filename} ({len(html)} bytes)")
    return html


def get_book_links(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for article in soup.select("article.product_pod"):
        a_tag = article.select_one("h3 a")
        relative_href = a_tag["href"]
        absolute_url = urljoin(page_url, relative_href)
        links.append(absolute_url)
    return links


def get_next_page_url(html, current_page_url):
    soup = BeautifulSoup(html, "html.parser")
    next_li = soup.select_one("li.next a")
    if next_li is None:
        return None
    relative_href = next_li["href"]
    return urljoin(current_page_url, relative_href)


def discover_all_book_urls():
    all_book_urls = []
    page_url = "https://books.toscrape.com/catalogue/page-1.html"
    page_number = 1
    max_pages = 3

    while page_url is not None and page_number <= max_pages:
        cache_filename = f"catalogue-page-{page_number}.html"
        html = fetch_page(page_url, cache_filename)

        book_links = get_book_links(html, page_url)
        all_book_urls.extend(book_links)

        page_url = get_next_page_url(html, page_url)
        page_number += 1

    unique_urls = list(dict.fromkeys(all_book_urls))

    print(f"catalogue_pages={page_number - 1}")
    print(f"discovered={len(all_book_urls)}")
    print(f"unique_urls={len(unique_urls)}")

    return unique_urls 

if __name__ == "__main__":
    discover_all_book_urls()