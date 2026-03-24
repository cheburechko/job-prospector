## Plan

This is the script for scraping jobs off of the tech companies sites. Its goal is to 
- iterate through all of the job postings available at the given URL, including paging
- visit the pages of all of the jobs and collect the following info
  - job title
  - job location
  - job description

The script will be used to go through a list of given company URLs and collect the data once. The script will be run regularly by cron.

- The script will be written in Python using playwright library
- The request should be handled with async
- Scraping should be done through configurable HTTPS proxy
- Sites should be scraped in parallel, each site is scraped sequentially with a rate limit. By default site uses the global rate limit, but it can be overriden in the site config
- Use class Job scraper/models/job.py

### Scraping configs

In order to allow scarping many different websites, there should be a universal configurable abstraction for scraping websites, which should be implemented in a library located in scraper/template. The abstraction should provide two classes
- CareersPageScenario
  - Contains css selectors for the jobs cards and the "pagination" buttons
    - Pagination example: https://job-boards.greenhouse.io/wolt/
- JobPageScenario
  - Contains css selectors to use to fill the fields of the Job object
  - There may be list of selectors to fill the same field

These classes should be serilizable to/from json. Classes should be placed in the scraper/models folder

Config should be used by the script for scraping. There may be more configs in the future, so allow the script to be extended with new types of configs.

### Storage
The script should use abstract storage for retrieving scraping configs and storing scraping results. Implementaions:
- JSON files
- DynamoDB


### Tests
Write tests in scraper/test. Use files in test/data as test data to for a mock server that would be scraped by the script.
