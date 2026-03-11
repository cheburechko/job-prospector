Project layout

- proxy - proxy that is used for scraping, docker image + deployment config
- scraper - script for scraping job sites in Python

### Scraper
- After all edits are done:
  - `pytest test/` - run all tests, including integration tests when verifying that the code works
  - `ruff check .` - lint files
  - `ruff format .` - format files
