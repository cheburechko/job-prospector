#!/usr/bin/env python3
"""
Example script for scraping LinkedIn jobs.

Searches for "software engineer" positions in Barcelona posted in the past 24 hours.
Uses Playwright for browser automation (LinkedIn renders content with JavaScript).

Note: LinkedIn's Terms of Service restrict scraping. This is for educational purposes.
Consider using LinkedIn's official API for production use.
"""

import json
import time
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright


def build_search_url(keywords: str, location: str, past_hours: int = 24) -> str:
    """Build LinkedIn jobs search URL with filters."""
    base = "https://www.linkedin.com/jobs/search/"
    params = {
        "keywords": keywords,
        "location": location,
        "f_TPR": f"r{past_hours * 3600}",  # Past N hours (seconds)
    }
    return f"{base}?{urlencode(params)}"


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
    jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("[data-job-id]", timeout=15000)

            # Scroll to load more results
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)

            # Extract job cards
            cards = page.query_selector_all("[data-job-id]")[:max_results]

            for card in cards:
                try:
                    job_id = card.get_attribute("data-job-id")
                    title_el = card.query_selector(
                        ".base-card__full-link, .job-card-list__title"
                    )
                    company_el = card.query_selector(
                        ".hidden-nested-link, .job-card-container__company-name"
                    )
                    location_el = card.query_selector(
                        ".job-card-container__metadata-item"
                    )
                    time_el = card.query_selector(
                        "time, .job-card-container__listed-time"
                    )

                    title = title_el.inner_text().strip() if title_el else ""
                    company = company_el.inner_text().strip() if company_el else ""
                    job_location = (
                        location_el.inner_text().strip() if location_el else ""
                    )
                    posted_time = time_el.inner_text().strip() if time_el else ""

                    link = (
                        f"https://www.linkedin.com/jobs/view/{job_id}/"
                        if job_id
                        else ""
                    )

                    jobs.append(
                        {
                            "title": title,
                            "company": company,
                            "location": job_location,
                            "link": link,
                            "posted_time": posted_time,
                        }
                    )
                except Exception as e:
                    print(f"Skipping card due to: {e}")

        finally:
            browser.close()

    return jobs


def main() -> None:
    """Run the scraper and print results."""
    print("Searching LinkedIn for 'software engineer' in Barcelona (past 24h)...")

    jobs = scrape_linkedin_jobs(
        keywords="software engineer",
        location="Barcelona",
        past_hours=24,
        max_results=25,
    )

    print(f"\nFound {len(jobs)} job(s):\n")
    for i, job in enumerate(jobs, 1):
        print(f"{i}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   Posted: {job['posted_time']}")
        print(f"   Link: {job['link']}")
        print()

    # Optionally save to JSON
    out_path = "linkedin_jobs_barcelona.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    print(build_search_url("software engineer", "Barcelona", 24))
    # main()
