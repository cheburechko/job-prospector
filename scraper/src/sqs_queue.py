import asyncio
import logging
from dataclasses import dataclass, field

import aioboto3

from models.company import Company
from models.config import SqsConfig

logger = logging.getLogger(__name__)


@dataclass
class QueueMessage:
    company: Company
    receipt_handle: str
    _heartbeat_task: asyncio.Task | None = field(default=None, repr=False)

    def stop_heartbeat(self):
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()


async def _heartbeat(queue: "SqsQueue", receipt_handle: str):
    visibility_timeout = await queue.get_visibility_timeout()
    delay = visibility_timeout // 2
    while True:
        await asyncio.sleep(delay)
        logger.debug("Extending visibility timeout for %s", receipt_handle)
        await queue.extend_message_visibility_timeout(receipt_handle)


class SqsQueue:
    def __init__(self, config: SqsConfig):
        self.config = config
        self.session = aioboto3.Session()
        self._visibility_timeout: int | None = None

    async def __aenter__(self):
        kwargs = {"region_name": self.config.region}
        if self.config.endpoint_url:
            kwargs["endpoint_url"] = self.config.endpoint_url
        self._client_ctx = self.session.client("sqs", **kwargs)
        self.client = await self._client_ctx.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client_ctx.__aexit__(exc_type, exc_val, exc_tb)

    async def get_visibility_timeout(self) -> int:
        if self._visibility_timeout is None:
            attrs = await self.client.get_queue_attributes(
                QueueUrl=self.config.queue_url,
                AttributeNames=["VisibilityTimeout"],
            )
            self._visibility_timeout = int(attrs["Attributes"]["VisibilityTimeout"])
        return self._visibility_timeout

    async def receive_messages(self) -> list[QueueMessage]:
        response = await self.client.receive_message(
            QueueUrl=self.config.queue_url,
            MaxNumberOfMessages=self.config.max_messages,
            WaitTimeSeconds=self.config.wait_time_seconds,
        )
        messages = []
        for msg in response.get("Messages", []):
            company = Company.from_json(msg["Body"])
            receipt_handle = msg["ReceiptHandle"]
            queue_msg = QueueMessage(company=company, receipt_handle=receipt_handle)
            queue_msg._heartbeat_task = asyncio.create_task(
                _heartbeat(self, receipt_handle)
            )
            messages.append(queue_msg)
        return messages

    async def extend_message_visibility_timeout(self, receipt_handle: str) -> None:
        visibility_timeout = await self.get_visibility_timeout()
        await self.client.change_message_visibility(
            QueueUrl=self.config.queue_url,
            ReceiptHandle=receipt_handle,
            VisibilityTimeout=visibility_timeout,
        )

    async def delete_message(self, receipt_handle: str) -> None:
        await self.client.delete_message(
            QueueUrl=self.config.queue_url,
            ReceiptHandle=receipt_handle,
        )

    async def send_message(self, company: Company) -> None:
        await self.client.send_message(
            QueueUrl=self.config.queue_url,
            MessageBody=company.to_json(),
        )
