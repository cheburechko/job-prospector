import asyncio

import boto3

from models.company import Company
from models.config import SqsConfig
from queues.base import Queue, QueueMessage


class SqsQueue(Queue):
    def __init__(self, config: SqsConfig):
        kwargs = {"region_name": config.region}
        if config.endpoint_url:
            kwargs["endpoint_url"] = config.endpoint_url
        self.client = boto3.client("sqs", **kwargs)
        self.queue_url = config.queue_url
        self.wait_time_seconds = config.wait_time_seconds
        self.max_messages = config.max_messages

    async def receive_messages(self) -> list[QueueMessage]:
        response = await asyncio.to_thread(
            self.client.receive_message,
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=self.max_messages,
            WaitTimeSeconds=self.wait_time_seconds,
        )
        messages = []
        for msg in response.get("Messages", []):
            company = Company.from_json(msg["Body"])
            messages.append(
                QueueMessage(company=company, receipt_handle=msg["ReceiptHandle"])
            )
        return messages

    async def delete_message(self, receipt_handle: str) -> None:
        await asyncio.to_thread(
            self.client.delete_message,
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle,
        )

    async def send_message(self, company: Company) -> None:
        await asyncio.to_thread(
            self.client.send_message,
            QueueUrl=self.queue_url,
            MessageBody=company.to_json(),
        )
