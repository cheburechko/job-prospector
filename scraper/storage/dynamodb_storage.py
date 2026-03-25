import boto3
from boto3.dynamodb.conditions import Key

from models.company import Company
from models.config import DynamoDbConfig
from models.job import Job
from storage.base import Storage

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
    def __init__(self, config: DynamoDbConfig):
        kwargs = {"region_name": config.region}
        if config.endpoint_url:
            kwargs["endpoint_url"] = config.endpoint_url
        self.dynamodb = boto3.resource("dynamodb", **kwargs)
        self.configs_table = self.dynamodb.Table(config.configs_table)
        self.jobs_table = self.dynamodb.Table(config.jobs_table)

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

    def load_companies(self) -> list[Company]:
        response = self.configs_table.scan()
        return [Company.from_dict(item) for item in response["Items"]]

    def add_company(self, company: Company) -> None:
        self.configs_table.put_item(Item=company.to_dict())

    def delete_company(self, company: str) -> None:
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
