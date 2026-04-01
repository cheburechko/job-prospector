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


async def _paginate(operation, **kwargs) -> list[dict]:
    items = []
    while True:
        response = await operation(**kwargs)
        items.extend(response["Items"])
        if "LastEvaluatedKey" not in response:
            return items
        kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]


class CompanyBatchWriter:
    def __init__(self, table):
        self._table = table

    async def __aenter__(self):
        self._writer_ctx = self._table.batch_writer()
        self._writer = await self._writer_ctx.__aenter__()
        return self

    async def __aexit__(self, *exc):
        await self._writer_ctx.__aexit__(*exc)

    async def add(self, company: Company) -> None:
        await self._writer.put_item(Item=company.to_dict())

    async def delete(self, company: str) -> None:
        await self._writer.delete_item(Key={"company": company})


class JobBatchWriter:
    def __init__(self, table):
        self._table = table

    async def __aenter__(self):
        self._writer_ctx = self._table.batch_writer()
        self._writer = await self._writer_ctx.__aenter__()
        return self

    async def __aexit__(self, *exc):
        await self._writer_ctx.__aexit__(*exc)

    async def add(self, job: Job) -> None:
        await self._writer.put_item(Item=job.to_dict())

    async def delete(self, company: str, url: str) -> None:
        await self._writer.delete_item(Key={"company": company, "url": url})


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

    def company_writer(self) -> CompanyBatchWriter:
        return CompanyBatchWriter(self.configs_table)

    def job_writer(self) -> JobBatchWriter:
        return JobBatchWriter(self.jobs_table)

    async def load_companies(self) -> list[Company]:
        items = await _paginate(self.configs_table.scan)
        return [Company.from_dict(item) for item in items]

    async def list_jobs(self, company: str) -> list[Job]:
        items = await _paginate(
            self.jobs_table.query,
            KeyConditionExpression=Key("company").eq(company),
        )
        return [Job.from_dict(item) for item in items]

    async def list_job_urls(self, company: str) -> set[str]:
        items = await _paginate(
            self.jobs_table.query,
            KeyConditionExpression=Key("company").eq(company),
            ProjectionExpression="#u",
            ExpressionAttributeNames={"#u": "url"},
        )
        return {item["url"] for item in items}
