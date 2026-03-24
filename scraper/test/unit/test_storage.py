import json

import boto3
import pytest
from moto import mock_aws

from models.job import Job
from storage.base import SiteConfig
from storage.dynamodb_storage import (
    DynamoDbStorage,
    create_configs_table,
    create_jobs_table,
)
from storage.json_storage import JsonStorage
from models.scenario import CareersPageScenario, JobPageScenario


@pytest.fixture
def site_config():
    return SiteConfig(
        company="Acme",
        url="https://example.com/jobs",
        careers_page=CareersPageScenario(
            job_card_selector="div.job",
            job_link_selector="a",
        ),
        job_page=JobPageScenario(
            title_selectors=["h1"],
            location_selectors=[".loc"],
            description_selectors=[".desc"],
        ),
    )


def _make_job(company="Acme", url="https://example.com/jobs/1", title="Engineer"):
    return Job(
        company=company,
        url=url,
        title=title,
        location="Remote",
        description="Build things",
    )


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

    def test_add_site_config(self, tmp_path, site_config):
        storage = JsonStorage(sites_dir=str(tmp_path), output_path="unused")
        storage.add_site_config(site_config)

        path = tmp_path / "Acme.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data == site_config.to_dict()

    def test_delete_site_config(self, tmp_path):
        (tmp_path / "Acme.json").write_text("{}")
        storage = JsonStorage(sites_dir=str(tmp_path), output_path="unused")
        storage.delete_site_config("Acme")
        assert not (tmp_path / "Acme.json").exists()

    def test_add_job(self, tmp_path):
        output_path = str(tmp_path / "results.json")
        storage = JsonStorage(sites_dir="unused", output_path=output_path)

        job1 = _make_job()
        job2 = _make_job(url="https://example.com/jobs/2", title="Designer")
        storage.add_job(job1)
        storage.add_job(job2)

        saved = json.loads((tmp_path / "results.json").read_text())
        assert sorted(saved, key=lambda x: x["url"]) == [job1.to_dict(), job2.to_dict()]

    def test_delete_job(self, tmp_path):
        output_path = str(tmp_path / "results.json")
        storage = JsonStorage(sites_dir="unused", output_path=output_path)

        job1 = _make_job()
        job2 = _make_job(url="https://example.com/jobs/2", title="Designer")
        storage.add_job(job1)
        storage.add_job(job2)
        storage.delete_job(job1.company, job1.url)

        saved = json.loads((tmp_path / "results.json").read_text())
        assert saved == [job2.to_dict()]

    def test_list_jobs(self, tmp_path):
        output_path = str(tmp_path / "results.json")
        storage = JsonStorage(sites_dir="unused", output_path=output_path)

        job1 = _make_job(company="Acme")
        job2 = _make_job(company="Other", url="https://other.com/1")
        storage.add_job(job1)
        storage.add_job(job2)

        jobs = storage.list_jobs(job1.company)
        assert jobs == [job1]

    def test_list_jobs_empty(self, tmp_path):
        output_path = str(tmp_path / "results.json")
        storage = JsonStorage(sites_dir="unused", output_path=output_path)
        assert storage.list_jobs("Acme") == []


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
    def test_add_site_config(self, site_config):
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        create_configs_table(dynamodb, CONFIGS_TABLE)
        create_jobs_table(dynamodb, JOBS_TABLE)

        storage = DynamoDbStorage(
            configs_table=CONFIGS_TABLE, jobs_table=JOBS_TABLE, region=REGION
        )
        storage.add_site_config(site_config)

        items = dynamodb.Table(CONFIGS_TABLE).scan()["Items"]
        assert items == [site_config.to_dict()]

    @mock_aws
    def test_delete_site_config(self, site_config):
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        create_configs_table(dynamodb, CONFIGS_TABLE)
        create_jobs_table(dynamodb, JOBS_TABLE)

        storage = DynamoDbStorage(
            configs_table=CONFIGS_TABLE, jobs_table=JOBS_TABLE, region=REGION
        )
        storage.add_site_config(site_config)
        storage.delete_site_config(site_config.company)

        items = dynamodb.Table(CONFIGS_TABLE).scan()["Items"]
        assert len(items) == 0

    @mock_aws
    def test_add_job(self):
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        create_configs_table(dynamodb, CONFIGS_TABLE)
        create_jobs_table(dynamodb, JOBS_TABLE)

        storage = DynamoDbStorage(
            configs_table=CONFIGS_TABLE, jobs_table=JOBS_TABLE, region=REGION
        )
        job = _make_job()
        storage.add_job(job)

        items = dynamodb.Table(JOBS_TABLE).scan()["Items"]
        assert items == [job.to_dict()]

    @mock_aws
    def test_delete_job(self):
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        create_configs_table(dynamodb, CONFIGS_TABLE)
        create_jobs_table(dynamodb, JOBS_TABLE)

        storage = DynamoDbStorage(
            configs_table=CONFIGS_TABLE, jobs_table=JOBS_TABLE, region=REGION
        )
        storage.add_job(_make_job())
        storage.delete_job("Acme", "https://example.com/jobs/1")

        items = dynamodb.Table(JOBS_TABLE).scan()["Items"]
        assert len(items) == 0

    @mock_aws
    def test_list_jobs(self):
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        create_configs_table(dynamodb, CONFIGS_TABLE)
        create_jobs_table(dynamodb, JOBS_TABLE)

        storage = DynamoDbStorage(
            configs_table=CONFIGS_TABLE, jobs_table=JOBS_TABLE, region=REGION
        )
        job1 = _make_job(company="Acme")
        job2 = _make_job(company="Other", url="https://other.com/1")
        storage.add_job(job1)
        storage.add_job(job2)

        jobs = storage.list_jobs(job1.company)
        assert jobs == [job1]
