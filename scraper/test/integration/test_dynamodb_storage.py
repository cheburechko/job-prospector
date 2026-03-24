import json

import boto3
import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from models.job import Job
from storage.base import SiteConfig
from storage.dynamodb_storage import (
    DynamoDbStorage,
    create_configs_table,
    create_jobs_table,
)

pytestmark = pytest.mark.integration

CONFIGS_TABLE = "test-configs"
JOBS_TABLE = "test-jobs"
REGION = "us-east-1"


@pytest.fixture(scope="module")
def dynamodb_container():
    container = (
        DockerContainer("amazon/dynamodb-local:latest")
        .with_exposed_ports(8000)
        .with_command("-jar DynamoDBLocal.jar -sharedDb -inMemory")
    )
    with container:
        wait_for_logs(container, "CorsParams", timeout=30)
        yield container


@pytest.fixture
def dynamodb_endpoint(dynamodb_container):
    host = dynamodb_container.get_container_host_ip()
    port = dynamodb_container.get_exposed_port(8000)
    return f"http://{host}:{port}"


@pytest.fixture
def storage(dynamodb_endpoint, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)

    resource = boto3.resource(
        "dynamodb",
        region_name=REGION,
        endpoint_url=dynamodb_endpoint,
    )
    create_configs_table(resource, CONFIGS_TABLE)
    create_jobs_table(resource, JOBS_TABLE)

    s = DynamoDbStorage(
        configs_table=CONFIGS_TABLE,
        jobs_table=JOBS_TABLE,
        region=REGION,
        endpoint_url=dynamodb_endpoint,
    )
    yield s

    resource.Table(CONFIGS_TABLE).delete()
    resource.Table(JOBS_TABLE).delete()


def test_save_and_scan_jobs(storage):
    jobs = [
        Job(
            company="Acme Corp",
            url="https://acme.com/jobs/1",
            title="Software Engineer",
            location="Remote",
            description="Build things",
        ),
    ]
    storage.save_jobs(jobs)

    items = storage.jobs_table.scan()["Items"]
    assert len(items) == 1
    item = items[0]
    assert item["company"] == "Acme Corp"
    assert item["url"] == "https://acme.com/jobs/1"
    assert item["title"] == "Software Engineer"
    assert item["location"] == "Remote"
    assert item["description"] == "Build things"


def test_load_site_configs(storage, fixtures_dir):
    site_data = json.loads(fixtures_dir.joinpath("site.json").read_text())
    storage.configs_table.put_item(Item=site_data)

    configs = storage.load_site_configs()
    assert len(configs) == 1
    config = configs[0]
    assert isinstance(config, SiteConfig)
    assert config.company == "Acme Corp"
    assert config.careers_page.job_card_selector == "tr.job-post"
    assert config.job_page.title_selectors == [
        "h1.section-header",
        'meta[property="og:title"]',
    ]


def test_sort_key_two_jobs_same_company(storage):
    jobs = [
        Job(
            company="Acme Corp",
            url="https://acme.com/jobs/1",
            title="Engineer",
            location="Remote",
            description="A",
        ),
        Job(
            company="Acme Corp",
            url="https://acme.com/jobs/2",
            title="Designer",
            location="NYC",
            description="B",
        ),
    ]
    storage.save_jobs(jobs)

    items = storage.jobs_table.scan()["Items"]
    assert len(items) == 2
    urls = {item["url"] for item in items}
    assert urls == {"https://acme.com/jobs/1", "https://acme.com/jobs/2"}
