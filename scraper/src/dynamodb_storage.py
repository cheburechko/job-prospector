import aioboto3
from boto3.dynamodb.conditions import Key

from models.company import Company
from models.config import DynamoDbConfig
from models.job import Job

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


class DynamoDbStorage:
    def __init__(self, config: DynamoDbConfig):
        self.config = config
        self.session = aioboto3.Session()

    async def __aenter__(self):
        kwargs = {"region_name": self.config.region}
        if self.config.endpoint_url:
            kwargs["endpoint_url"] = self.config.endpoint_url
        self._resource_ctx = self.session.resource("dynamodb", **kwargs)
        self.dynamodb = await self._resource_ctx.__aenter__()
        self.configs_table = await self.dynamodb.Table(self.config.configs_table)
        self.jobs_table = await self.dynamodb.Table(self.config.jobs_table)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._resource_ctx.__aexit__(exc_type, exc_val, exc_tb)

    async def create_tables(self) -> None:
        await self.dynamodb.create_table(
            TableName=self.configs_table.name,
            **CONFIGS_TABLE_SCHEMA,
            BillingMode="PAY_PER_REQUEST",
        )
        await self.dynamodb.create_table(
            TableName=self.jobs_table.name,
            **JOBS_TABLE_SCHEMA,
            BillingMode="PAY_PER_REQUEST",
        )

    async def load_companies(self) -> list[Company]:
        response = await self.configs_table.scan()
        return [Company.from_dict(item) for item in response["Items"]]

    async def add_company(self, company: Company) -> None:
        await self.configs_table.put_item(Item=company.to_dict())

    async def delete_company(self, company: str) -> None:
        await self.configs_table.delete_item(Key={"company": company})

    async def add_job(self, job: Job) -> None:
        await self.jobs_table.put_item(Item=job.to_dict())

    async def delete_job(self, company: str, url: str) -> None:
        await self.jobs_table.delete_item(Key={"company": company, "url": url})

    async def list_jobs(self, company: str) -> list[Job]:
        response = await self.jobs_table.query(
            KeyConditionExpression=Key("company").eq(company),
        )
        return [Job.from_dict(item) for item in response["Items"]]
