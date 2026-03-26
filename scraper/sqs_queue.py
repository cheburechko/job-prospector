from dataclasses import dataclass

import aioboto3

from models.company import Company
from models.config import SqsConfig


@dataclass
class QueueMessage:
    company: Company
    receipt_handle: str


class SqsQueue:
    def __init__(self, config: SqsConfig):
        self.config = config
        self.session = aioboto3.Session()

    async def __aenter__(self):
        kwargs = {"region_name": self.config.region}
        if self.config.endpoint_url:
            kwargs["endpoint_url"] = self.config.endpoint_url
        self._client_ctx = self.session.client("sqs", **kwargs)
        self.client = await self._client_ctx.__aenter__()
        self.queue_url = self.config.queue_url
        self.wait_time_seconds = self.config.wait_time_seconds
        self.max_messages = self.config.max_messages
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client_ctx.__aexit__(exc_type, exc_val, exc_tb)

    async def receive_messages(self) -> list[QueueMessage]:
        response = await self.client.receive_message(
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
        await self.client.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle,
        )

    async def send_message(self, company: Company) -> None:
        await self.client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=company.to_json(),
        )
