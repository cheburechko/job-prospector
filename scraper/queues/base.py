from abc import ABC, abstractmethod
from dataclasses import dataclass

from models.company import Company


@dataclass
class QueueMessage:
    company: Company
    receipt_handle: str


class Queue(ABC):
    @abstractmethod
    async def receive_messages(self) -> list[QueueMessage]: ...

    @abstractmethod
    async def delete_message(self, receipt_handle: str) -> None: ...
