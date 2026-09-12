import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone
import time
import re
import json
from pydantic import BaseModel, ValidationError


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
    attempts = 0
    max_attempts = 2

    while attempts < max_attempts:
        attempts += 1
        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
            response.encoding = "utf-8"
        except requests.exceptions.Timeout:
            if attempts < max_attempts:
                time.sleep(1)
                continue
            raise Exception(f"Timed out after {max_attempts} attempts")

        if response.status_code == 200:
            html = response.text
            CACHE_DIR.mkdir(exist_ok=True)
            cache_path.write_text(html, encoding="utf-8")
            print(f"FETCH — {cache_filename} ({len(html)} bytes)")
            time.sleep(DELAY_SECONDS)
            return html

        if response.status_code in (404, 403):
            raise Exception(f"Status {response.status_code} — will not retry")

        if response.status_code >= 500 and attempts < max_attempts:
            time.sleep(1)
            continue

        raise Exception(f"Failed to fetch {url} — status code {response.status_code}")

    raise Exception(f"Failed to fetch {url} after {max_attempts} attempts")


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
    failed_pages = []

    for url in book_urls:
        cache_filename = cache_filename_for_book(url)
        try:
            html = fetch_page(url, cache_filename)
            record = extract_book_record(html, url, source_pages[url])
            records.append(record)
        except Exception as error:
            print(f"FAILED — {url} ({error})")
            failed_pages.append({"url": url, "reason": str(error)})

    print(f"detail_pages={len(records)}")
    return records, failed_pages

class BookRecord(BaseModel):
    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str | None
    description: str | None
    source_page: str
    fetched_at: str


def clean_price(price_text):
    match = re.search(r"[\d.]+", price_text)
    if match is None:
        return None
    return float(match.group())


def normalize_record(raw_record):
    price_gbp = clean_price(raw_record["price_text"])
    normalized = dict(raw_record)
    normalized["price_gbp"] = price_gbp
    return normalized


def validate_and_store(raw_records):
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    valid_records = []
    invalid_records = []
    seen_urls = set()

    for raw_record in raw_records:
        normalized = normalize_record(raw_record)

        if normalized["product_url"] in seen_urls:
            continue
        seen_urls.add(normalized["product_url"])

        try:
            validated = BookRecord(**normalized)
            valid_records.append(validated.model_dump())
        except ValidationError as error:
            invalid_records.append({
                "record": normalized,
                "reason": str(error)
            })

    books_path = output_dir / "books.json"
    errors_path = output_dir / "errors.json"

    books_path.write_text(json.dumps(valid_records, indent=2), encoding="utf-8")
    errors_path.write_text(json.dumps(invalid_records, indent=2), encoding="utf-8")

    print(f"valid_records={len(valid_records)}")
    print(f"invalid_records={len(invalid_records)}")

    return valid_records, invalid_records

def write_run_report(start_time, catalogue_pages, cache_hits, fetch_count, valid_records, invalid_records, failed_pages):
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    end_time = datetime.now(timezone.utc)
    duration_seconds = (end_time - start_time).total_seconds()

    report = {
        "start_time": start_time.isoformat(),
        "duration_seconds": duration_seconds,
        "catalogue_pages": catalogue_pages,
        "pages_fetched": fetch_count,
        "cache_hits": cache_hits,
        "valid_records": valid_records,
        "invalid_records": invalid_records,
        "failed_pages": len(failed_pages),
        "failed_page_details": failed_pages
    }

    report_path = output_dir / "run-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"failed_pages={len(failed_pages)}")


if __name__ == "__main__":
    start_time = datetime.now(timezone.utc)

    book_urls, source_pages = discover_all_book_urls()

    book_urls.append("https://books.toscrape.com/catalogue/this-book-does-not-exist/index.html")
    source_pages["https://books.toscrape.com/catalogue/this-book-does-not-exist/index.html"] = "manual-test"

    records, failed_pages = extract_all_books(book_urls, source_pages)
    valid_records, invalid_records = validate_and_store(records)

    write_run_report(
        start_time=start_time,
        catalogue_pages=3,
        cache_hits=None,
        fetch_count=None,
        valid_records=len(valid_records),
        invalid_records=len(invalid_records),
        failed_pages=failed_pages
    )