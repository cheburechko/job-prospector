import json

import boto3
from moto import mock_aws

from models.job import Job
from storage.dynamodb_storage import (
    DynamoDbStorage,
    create_configs_table,
    create_jobs_table,
)
from storage.json_storage import JsonStorage


class TestJsonStorage:
    def test_load_site_configs(self, tmp_path):
        site_data = {
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
        (tmp_path / "acme.json").write_text(json.dumps(site_data))

        storage = JsonStorage(sites_dir=str(tmp_path), output_path="unused")
        configs = storage.load_site_configs()
        assert len(configs) == 1
        assert configs[0].company == "Acme"

    def test_save_jobs(self, tmp_path):
        output_path = str(tmp_path / "results.json")
        storage = JsonStorage(sites_dir="unused", output_path=output_path)

        jobs = [
            Job(
                company="Acme",
                url="https://example.com/jobs/1",
                title="Engineer",
                location="Remote",
                description="Build things",
            ),
            Job(
                company="Acme",
                url="https://example.com/jobs/2",
                title="Designer",
                location="Berlin",
                description="Design things",
            ),
        ]
        storage.save_jobs(jobs)

        saved = json.loads((tmp_path / "results.json").read_text())
        assert len(saved) == 2
        assert saved[0]["title"] == "Engineer"
        assert saved[0]["url"] == "https://example.com/jobs/1"
        assert saved[1]["location"] == "Berlin"


REGION = "eu-central-1"
CONFIGS_TABLE = "scraper-site-configs"
JOBS_TABLE = "scraper-jobs"


class TestDynamoDbStorage:
    @mock_aws
    def test_load_site_configs(self):
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        create_configs_table(dynamodb, CONFIGS_TABLE)
        table = dynamodb.Table(CONFIGS_TABLE)
        table.put_item(
            Item={
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
        )

        storage = DynamoDbStorage(
            configs_table=CONFIGS_TABLE, jobs_table=JOBS_TABLE, region=REGION
        )
        configs = storage.load_site_configs()
        assert len(configs) == 1
        assert configs[0].company == "Acme"
        assert configs[0].url == "https://example.com/jobs"
        assert configs[0].careers_page.job_card_selector == "div.job"

    @mock_aws
    def test_save_jobs(self):
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        create_jobs_table(dynamodb, JOBS_TABLE)

        storage = DynamoDbStorage(
            configs_table=CONFIGS_TABLE, jobs_table=JOBS_TABLE, region=REGION
        )
        jobs = [
            Job(
                company="Acme",
                url="https://example.com/jobs/1",
                title="Engineer",
                location="Remote",
                description="Build things",
            ),
            Job(
                company="Acme",
                url="https://example.com/jobs/2",
                title="Designer",
                location="Berlin",
                description="Design things",
            ),
        ]
        storage.save_jobs(jobs)

        table = dynamodb.Table(JOBS_TABLE)
        response = table.scan()
        items = response["Items"]
        assert len(items) == 2
        titles = {item["title"] for item in items}
        assert titles == {"Engineer", "Designer"}
        urls = {item["url"] for item in items}
        assert urls == {"https://example.com/jobs/1", "https://example.com/jobs/2"}
