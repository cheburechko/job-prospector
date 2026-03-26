from models.company import Company
from models.job import Job
from models.scenario import CareersPageScenario, JobPageScenario

COMPANY_DEFAULTS = {
    "company": "Acme",
    "url": "https://example.com/jobs",
    "careers_page": CareersPageScenario(
        job_card_selector="div.job",
        job_link_selector="a",
    ),
    "job_page": JobPageScenario(
        title_selectors=["h1"],
        location_selectors=[".loc"],
        description_selectors=[".desc"],
    ),
}

COMPANY_JSON_DEFAULTS = {
    "company": "Acme",
    "url": "https://example.com/jobs",
    "careers_page": {
        "job_card_selector": "div.job",
        "job_link_selector": "a",
    },
    "job_page": {
        "title_selectors": ["h1"],
        "location_selectors": [".loc"],
        "description_selectors": [".desc"],
    },
}


def make_company(**overrides) -> Company:
    return Company(**{**COMPANY_DEFAULTS, **overrides})


def make_company_json(**overrides) -> dict:
    return {**COMPANY_JSON_DEFAULTS, **overrides}


def make_job(
    company="Acme",
    url="https://example.com/jobs/1",
    title="Engineer",
    location="Remote",
    description="Build things",
) -> Job:
    return Job(
        company=company,
        url=url,
        title=title,
        location=location,
        description=description,
    )
