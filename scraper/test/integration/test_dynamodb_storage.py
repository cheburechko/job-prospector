import json

import boto3
import pytest
from testcontainers.core.container import DockerContainer, LogMessageWaitStrategy

from models.job import Job
from models.scenario import CareersPageScenario, JobPageScenario
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
        container.waiting_for(
            LogMessageWaitStrategy("CorsParams").with_startup_timeout(30)
        )
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


def _make_job(
    company="Acme Corp", url="https://acme.com/jobs/1", title="Software Engineer"
):
    return Job(
        company=company,
        url=url,
        title=title,
        location="Remote",
        description="Build things",
    )


def test_add_and_list_jobs(storage):
    job = _make_job()
    storage.add_job(job)

    jobs = storage.list_jobs("Acme Corp")
    assert jobs == [job]


def test_add_two_jobs_same_company(storage):
    job1 = _make_job(url="https://acme.com/jobs/1", title="Engineer")
    job2 = _make_job(url="https://acme.com/jobs/2", title="Designer")
    storage.add_job(job1)
    storage.add_job(job2)

    jobs = storage.list_jobs("Acme Corp")
    assert sorted(jobs, key=lambda x: x.url) == [job1, job2]


def test_delete_job(storage):
    job = _make_job()
    storage.add_job(job)
    storage.delete_job(job.company, job.url)

    jobs = storage.list_jobs("Acme Corp")
    assert jobs == []


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


@pytest.fixture
def site_config():
    return SiteConfig(
        company="TestCo",
        url="https://testco.com/careers",
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


def test_add_site_config(storage, site_config):
    storage.add_site_config(site_config)

    configs = storage.load_site_configs()
    assert len(configs) == 1
    assert configs[0] == site_config


def test_delete_site_config(storage, site_config):
    storage.add_site_config(site_config)
    storage.delete_site_config(site_config.company)

    configs = storage.load_site_configs()
    assert len(configs) == 0
