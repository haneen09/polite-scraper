# Polite Scraper — FlyRank Internship, Week 5 (A9)

## Target Classification

- **Site:** Books to Scrape (https://books.toscrape.com)
- **Why this site:** It is an official practice sandbox explicitly built for people to learn
  and practice web scraping. The site's own homepage states it "desperately wants to be scraped"
  and exists for beginners and developers to safely test scraping tools.
- **Scope:** Only the first 3 catalogue pages (and the individual book pages linked from them) —
  no more than that.
- **Data collected:** Book title, price, availability, star rating, description, and product URL —
  publicly displayed catalogue data only.
- **robots.txt result:** Requested https://books.toscrape.com/robots.txt — returned a 404
  (no robots file found). A missing file is not explicit permission, but combined with the site's
  own stated purpose as a scraping practice sandbox, proceeding is appropriate here.

I will not reuse this code on another site without checking its rules and terms first.

## How to run

1. Install Python 3.10+
2. Install dependencies: pip install requests beautifulsoup4 pydantic
3. Run the scraper: python scraper/src/main.py
4. Output appears in `output/books.json` and `output/run-report.json`

## Record schema

Each book record contains:

- `title` (string)
- `product_url` (string, canonical identity)
- `price_text` (string, raw)
- `price_gbp` (number, cleaned)
- `availability_text` (string)
- `rating_text` (string or null)
- `description` (string or null)
- `source_page` (string)
- `fetched_at` (ISO timestamp string)

## Politeness

- Identifies itself with a custom User-Agent
- 10 second timeout on every request
- 0.5 second delay between real requests
- Checks status code before parsing
- Caches every page locally so development never re-hits the site
- Retries once on timeout or 5xx errors, never retries 404 or 403

## Sample run report

```json
{
  "start_time": "2026-09-12T16:25:42.470165+00:00",
  "duration_seconds": 2.568254,
  "catalogue_pages": 3,
  "pages_fetched": null,
  "cache_hits": null,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1,
  "failed_page_details": [
    {
      "url": "https://books.toscrape.com/catalogue/this-book-does-not-exist/index.html",
      "reason": "Status 404 \u2014 will not retry"
    }
  ]
}
```

## Why no browser was needed

This assignment needed no browser because the book data is already present in the HTML the
server sends — a browser would only add cost (memory, startup time) with no benefit here.

## Ethics note

I only scraped a site built for practice, and I would use an official API instead of scraping
if one were available. I never bypass logins, paywalls, or access blocks, and I only collect the
minimum data needed for the task at hand.

## Limitations

This scraper does not handle JavaScript-rendered content, and its retry logic is basic — one
retry on timeout or server errors, with no exponential backoff.
