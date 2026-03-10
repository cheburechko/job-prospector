This is the original task. Do not edit it, write any amendments in separate .md files.

## Plan

This is the script for scraping jobs off of the tech companies sites. Its goal is to 
- iterate through all of the job postings available at the given URL, including paging
- visit the pages of all of the jobs and collect the following info
  - job title
  - job location
  - job description

The script will be used to go through a list of given company URLs and collect the data once. The script will be run regularly by cron.

- The script will be written in Python using playwright library
- The request shoudl be handled with async
- Scraping should be done through configurable HTTPS proxy
- The script should not overload any specific site and should have a restriction on the number of requests per second (RPS) addressed to a site, the RPS setting should be global for all sites.
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

### Tests
Write tests in scraper/test. Use files in test/data as test data to for a mock server that would be scraped by the script.

