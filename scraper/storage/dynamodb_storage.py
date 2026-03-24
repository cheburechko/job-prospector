import boto3
from boto3.dynamodb.conditions import Key

from models.job import Job
from storage.base import SiteConfig, Storage

CONFIGS_TABLE_SCHEMA = {
    "KeySchema": [{"AttributeName": "company", "KeyType": "HASH"}],
    "AttributeDefinitions": [{"AttributeName": "company", "AttributeType": "S"}],
}

JOBS_TABLE_SCHEMA = {
    "KeySchema": [
        {"AttributeName": "company", "KeyType": "HASH"},
        {"AttributeName": "url", "KeyType": "RANGE"},
    ],
    "AttributeDefinitions": [
        {"AttributeName": "company", "AttributeType": "S"},
        {"AttributeName": "url", "AttributeType": "S"},
    ],
}


class DynamoDbStorage(Storage):
    def __init__(
        self,
        configs_table: str,
        jobs_table: str,
        region: str,
        endpoint_url: str | None = None,
    ):
        kwargs = {"region_name": region}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self.dynamodb = boto3.resource("dynamodb", **kwargs)
        self.configs_table = self.dynamodb.Table(configs_table)
        self.jobs_table = self.dynamodb.Table(jobs_table)

    def create_tables(self) -> None:
        self.dynamodb.create_table(
            TableName=self.configs_table.name,
            **CONFIGS_TABLE_SCHEMA,
            BillingMode="PAY_PER_REQUEST",
        )
        self.dynamodb.create_table(
            TableName=self.jobs_table.name,
            **JOBS_TABLE_SCHEMA,
            BillingMode="PAY_PER_REQUEST",
        )

    def load_site_configs(self) -> list[SiteConfig]:
        response = self.configs_table.scan()
        return [SiteConfig.from_dict(item) for item in response["Items"]]

    def add_site_config(self, site_config: SiteConfig) -> None:
        self.configs_table.put_item(Item=site_config.to_dict())

    def delete_site_config(self, company: str) -> None:
        self.configs_table.delete_item(Key={"company": company})

    def add_job(self, job: Job) -> None:
        self.jobs_table.put_item(Item=job.to_dict())

    def delete_job(self, company: str, url: str) -> None:
        self.jobs_table.delete_item(Key={"company": company, "url": url})

    def list_jobs(self, company: str) -> list[Job]:
        response = self.jobs_table.query(
            KeyConditionExpression=Key("company").eq(company)
        )
        return [Job.from_dict(item) for item in response["Items"]]
