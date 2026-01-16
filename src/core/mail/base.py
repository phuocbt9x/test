from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MailMessage:
    subject: str
    recipients: list[str]
    body: str | None = None
    subtype: str = "html"
    template_name: str | None = None
    template_body: dict[str, Any] = field(default_factory=dict)


class BaseMailProvider(ABC):
    @abstractmethod
    async def send(self, message: MailMessage) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_provider_name(self) -> str:
        raise NotImplementedError
