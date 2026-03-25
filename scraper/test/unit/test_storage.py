import json

import pytest
from moto import mock_aws

from models.config import DynamoDbConfig
from storage.dynamodb_storage import DynamoDbStorage
from test.helpers import create_json_storage, make_company_json, make_job


class TestJsonStorage:
    def test_load_companies(self, tmp_path):
        site_data = make_company_json()
        (tmp_path / "acme.json").write_text(json.dumps(site_data))

        storage = create_json_storage(sites_dir=str(tmp_path))
        companies = storage.load_companies()
        assert len(companies) == 1
        assert companies[0].company == "Acme"

    def test_add_company(self, tmp_path, company):
        storage = create_json_storage(sites_dir=str(tmp_path))
        storage.add_company(company)

        path = tmp_path / "Acme.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data == company.to_dict()

    def test_delete_company(self, tmp_path):
        (tmp_path / "Acme.json").write_text("{}")
        storage = create_json_storage(sites_dir=str(tmp_path))
        storage.delete_company("Acme")
        assert not (tmp_path / "Acme.json").exists()

    def test_add_job(self, tmp_path):
        output_path = str(tmp_path / "results.json")
        storage = create_json_storage(output_path=output_path)

        job1 = make_job()
        job2 = make_job(url="https://example.com/jobs/2", title="Designer")
        storage.add_job(job1)
        storage.add_job(job2)

        saved = json.loads((tmp_path / "results.json").read_text())
        assert sorted(saved, key=lambda x: x["url"]) == [job1.to_dict(), job2.to_dict()]

    def test_delete_job(self, tmp_path):
        output_path = str(tmp_path / "results.json")
        storage = create_json_storage(output_path=output_path)

        job1 = make_job()
        job2 = make_job(url="https://example.com/jobs/2", title="Designer")
        storage.add_job(job1)
        storage.add_job(job2)
        storage.delete_job(job1.company, job1.url)

        saved = json.loads((tmp_path / "results.json").read_text())
        assert saved == [job2.to_dict()]

    def test_list_jobs(self, tmp_path):
        output_path = str(tmp_path / "results.json")
        storage = create_json_storage(output_path=output_path)

        job1 = make_job(company="Acme")
        job2 = make_job(company="Other", url="https://other.com/1")
        storage.add_job(job1)
        storage.add_job(job2)

        jobs = storage.list_jobs(job1.company)
        assert jobs == [job1]

    def test_list_jobs_empty(self, tmp_path):
        output_path = str(tmp_path / "results.json")
        storage = create_json_storage(output_path=output_path)
        assert storage.list_jobs("Acme") == []


REGION = "eu-central-1"
CONFIGS_TABLE = "scraper-site-configs"
JOBS_TABLE = "scraper-jobs"


@pytest.fixture
def dynamodb_storage():
    with mock_aws():
        storage = DynamoDbStorage(
            DynamoDbConfig(
                configs_table=CONFIGS_TABLE, jobs_table=JOBS_TABLE, region=REGION
            )
        )
        storage.create_tables()
        yield storage
        storage.dynamodb.Table(CONFIGS_TABLE).delete()
        storage.dynamodb.Table(JOBS_TABLE).delete()


class TestDynamoDbStorage:
    def test_load_companies(self, dynamodb_storage, company):
        dynamodb_storage.dynamodb.Table(CONFIGS_TABLE).put_item(Item=company.to_dict())
        companies = dynamodb_storage.load_companies()
        assert companies == [company]

    def test_add_company(self, dynamodb_storage, company):
        dynamodb_storage.add_company(company)

        items = dynamodb_storage.dynamodb.Table(CONFIGS_TABLE).scan()["Items"]
        assert items == [company.to_dict()]

    def test_delete_company(self, dynamodb_storage, company):
        dynamodb_storage.add_company(company)
        dynamodb_storage.delete_company(company.company)

        items = dynamodb_storage.dynamodb.Table(CONFIGS_TABLE).scan()["Items"]
        assert len(items) == 0

    def test_add_job(self, dynamodb_storage):
        job = make_job()
        dynamodb_storage.add_job(job)

        items = dynamodb_storage.dynamodb.Table(JOBS_TABLE).scan()["Items"]
        assert items == [job.to_dict()]

    def test_delete_job(self, dynamodb_storage):
        dynamodb_storage.add_job(make_job())
        dynamodb_storage.delete_job("Acme", "https://example.com/jobs/1")

        items = dynamodb_storage.dynamodb.Table(JOBS_TABLE).scan()["Items"]
        assert len(items) == 0

    def test_list_jobs(self, dynamodb_storage):
        job1 = make_job(company="Acme")
        job2 = make_job(company="Other", url="https://other.com/1")
        dynamodb_storage.add_job(job1)
        dynamodb_storage.add_job(job2)

        jobs = dynamodb_storage.list_jobs(job1.company)
        assert jobs == [job1]
