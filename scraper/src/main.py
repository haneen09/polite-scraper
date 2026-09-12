import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone
import time

USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/haneen09/polite-scrapper)"
TIMEOUT_SECONDS = 10
CACHE_DIR = Path(__file__).parent.parent / "cache"
DELAY_SECONDS = 0.5


def fetch_page(url, cache_filename):
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        print(f"CACHE HIT — {cache_filename} ({len(html)} bytes)")
        return html

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
    response.encoding = "utf-8"
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch {url} — status code {response.status_code}")

    html = response.text
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path.write_text(html, encoding="utf-8")

    print(f"FETCH — {cache_filename} ({len(html)} bytes)")
    time.sleep(DELAY_SECONDS)
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
    source_pages = {}

    while page_url is not None and page_number <= max_pages:
        cache_filename = f"catalogue-page-{page_number}.html"
        html = fetch_page(page_url, cache_filename)

        book_links = get_book_links(html, page_url)
        all_book_urls.extend(book_links)

        for link in book_links:
            source_pages[link] = page_url

        page_url = get_next_page_url(html, page_url)
        page_number += 1

    unique_urls = list(dict.fromkeys(all_book_urls))

    print(f"catalogue_pages={page_number - 1}")
    print(f"discovered={len(all_book_urls)}")
    print(f"unique_urls={len(unique_urls)}")

    return unique_urls, source_pages


def extract_book_record(html, product_url, source_page):
    soup = BeautifulSoup(html, "html.parser")
    product_area = soup.select_one("div.product_main")

    title = product_area.select_one("h1").get_text(strip=True)
    price_text = product_area.select_one("p.price_color").get_text(strip=True)
    availability_text = product_area.select_one("p.availability").get_text(strip=True)

    rating_tag = product_area.select_one("p.star-rating")
    rating_text = rating_tag["class"][1] if rating_tag else None

    description_heading = soup.select_one("#product_description")
    if description_heading is not None:
        description_p = description_heading.find_next_sibling("p")
        description = description_p.get_text(strip=True) if description_p is not None else None
    else:
        description = None

    fetched_at = datetime.now(timezone.utc).isoformat()

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }


def cache_filename_for_book(product_url):
    slug = product_url.rstrip("/").split("/")[-2]
    return f"book-{slug}.html"


def extract_all_books(book_urls, source_pages):
    records = []
    for url in book_urls:
        cache_filename = cache_filename_for_book(url)
        html = fetch_page(url, cache_filename)
        record = extract_book_record(html, url, source_pages[url])
        records.append(record)

    print(f"detail_pages={len(records)}")
    return records


if __name__ == "__main__":
    book_urls, source_pages = discover_all_book_urls()
    records = extract_all_books(book_urls, source_pages)
    print(records[0])