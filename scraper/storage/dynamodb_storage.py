import boto3

from models.job import Job
from storage.base import SiteConfig, Storage

CONFIGS_TABLE_SCHEMA = {
    "KeySchema": [{"AttributeName": "company", "KeyType": "HASH"}],
    "AttributeDefinitions": [{"AttributeName": "company", "AttributeType": "S"}],
}

JOBS_TABLE_SCHEMA = {
    "KeySchema": [
        {"AttributeName": "company", "KeyType": "HASH"},
        {"AttributeName": "title", "KeyType": "RANGE"},
    ],
    "AttributeDefinitions": [
        {"AttributeName": "company", "AttributeType": "S"},
        {"AttributeName": "title", "AttributeType": "S"},
    ],
}


def create_configs_table(dynamodb, table_name: str):
    dynamodb.create_table(
        TableName=table_name,
        **CONFIGS_TABLE_SCHEMA,
        BillingMode="PAY_PER_REQUEST",
    )


def create_jobs_table(dynamodb, table_name: str):
    dynamodb.create_table(
        TableName=table_name,
        **JOBS_TABLE_SCHEMA,
        BillingMode="PAY_PER_REQUEST",
    )


class DynamoDbStorage(Storage):
    def __init__(self, configs_table: str, jobs_table: str, region: str):
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.configs_table = self.dynamodb.Table(configs_table)
        self.jobs_table = self.dynamodb.Table(jobs_table)

    def load_site_configs(self) -> list[SiteConfig]:
        response = self.configs_table.scan()
        return [SiteConfig.from_dict(item) for item in response["Items"]]

    def save_jobs(self, jobs: list[Job]) -> None:
        with self.jobs_table.batch_writer() as batch:
            for job in jobs:
                batch.put_item(Item=job.to_dict())
