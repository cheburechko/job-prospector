from dynamodb_storage import DynamoDbStorage
from models.config import SchedulerConfig
from sqs_queue import SqsQueue


async def run(storage: DynamoDbStorage, queue: SqsQueue):
    companies = await storage.load_companies()
    for company in companies:
        await queue.send_message(company)


async def run_scheduler(config: SchedulerConfig):
    async with (
        DynamoDbStorage(config.dynamodb) as storage,
        SqsQueue(config.sqs) as queue,
    ):
        await run(storage, queue)
