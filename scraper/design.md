## Design

This is the service for scraping jobs off of the tech companies sites. Its goal is to 
- iterate through all of the job postings available at the given URL, including paging
- visit the pages of all of the jobs and collect the following info
  - job title
  - job location
  - job description

The service consists of two components and a test tool:
- scheduler - schedules scraping of sites by sending all company sites from storage to the queue
- worker - listens for the scraping tasks on the queue
- test - scrapes a single company from a local JSON config file and writes results to a JSON file


### Worker
- It receives Company objects in JSON format from the queue. 
- It can process multiple companies at the same time asynchronously.
- The script will be written in Python using playwright library
- The request should be handled with async
- Scraping should be done through configurable HTTPS proxy
- Sites should be scraped in parallel, each site is scraped sequentially with a rate limit. By default site uses the global rate limit, but it can be overriden in the site config
- Runs as ECS service, scales up when there scraping tasks in queue, deallocates otherwise

### Test
- Accepts a JSON file with Company scraping config (same format as site configs in DynamoDB)
- Scrapes the single company and writes results as JSON to an output file (default: out.json)
- Supports HTTPS proxy settings
- Used for developing and validating scraping configs locally


## Outline
- docker/ - docker image for scraper
- src/commands/scheduler.py - one time scheduler for scraping tasks
- src/commands/worker.py - worker queue processing loop
- src/commands/test.py - single company test scraper
- src/models/ - dataclasses for scraping scenarios and jobs
- src/template/ - engine for scraping sites
- src/test/fixtures/ - test data shared by all tests
- src/test/integraion/
- src/test/unit/
- src/main.py - CLI


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
