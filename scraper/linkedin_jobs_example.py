#!/usr/bin/env python3
import contextlib
from urllib.parse import urlencode

import playwright.sync_api as sync_api


def build_search_url(keywords: str, location: str, past_hours: int = 24) -> str:
    """Build LinkedIn jobs search URL with filters."""
    base = "https://www.linkedin.com/jobs/search/"
    params = {
        "keywords": keywords,
        "location": location,
        "f_TPR": f"r{past_hours * 3600}",  # Past N hours (seconds)
    }
    return f"{base}?{urlencode(params)}"


def get_proxy_password() -> str:
    with open("../.secrets/proxy_password", "r") as f:
        return f.read().strip()


@contextlib.contextmanager
def create_context(
    playwright: sync_api.Playwright,
) -> sync_api.BrowserContext:
    browser = playwright.chromium.launch(headless=True)
    try:
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            proxy={
                "server": "https://proxy.aws-is-the-best.com",
                "username": "admin",
                "password": get_proxy_password(),
            },
        )
        yield context
    finally:
        context.close()
        browser.close()


def scrape_linkedin_jobs(
    keywords: str = "software engineer",
    location: str = "Barcelona",
    past_hours: int = 24,
    max_results: int = 25,
) -> list[dict]:
    """
    Scrape job listings from LinkedIn.

    Args:
        keywords: Job title or keywords to search.
        location: Geographic location (city or region).
        past_hours: Only include jobs posted in the last N hours.
        max_results: Maximum number of listings to collect.

    Returns:
        List of dicts with keys: title, company, location, link, posted_time.
    """
    url = build_search_url(keywords, location, past_hours)

    with sync_api.sync_playwright() as p, create_context(p) as context:
        page = context.new_page()

        page.goto(url, timeout=30000)

        # Extract job cards
        cards = page.query_selector_all(".base-card__full-link")[:max_results]
        links = [card.get_attribute("href") for card in cards]

    return links


def main() -> None:
    """Run the scraper and print results."""
    print("Searching LinkedIn for 'software engineer' in Barcelona (past 24h)...")

    links = scrape_linkedin_jobs(
        keywords="software engineer",
        location="Barcelona",
        past_hours=24,
        max_results=5,
    )

    print(f"\nFound {len(links)} job(s):\n")
    for i, link in enumerate(links, 1):
        print(f"{i}. {link}")


if __name__ == "__main__":
    main()
