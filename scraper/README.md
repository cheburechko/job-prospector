# LinkedIn Jobs Scraper (Example)

Example Python script for scraping LinkedIn job listings.

## Setup

```bash
cd scraper
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
python linkedin_jobs_example.py
```

## Configuration

Edit `linkedin_jobs_example.py` to change:

- **keywords**: Job title search (default: "software engineer")
- **location**: City or region (default: Barcelona)
- **past_hours**: Time filter in hours (default: 24)
- **max_results**: Max listings to collect (default: 25)

## Notes

- LinkedIn renders content with JavaScript; Playwright is used for browser automation
