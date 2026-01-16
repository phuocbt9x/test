from typing import cast

from fastapi_mail import (  # type: ignore[import-untyped]
    ConnectionConfig,
    FastMail,
    MessageSchema,
    MessageType,
    NameEmail,
)

from .base import BaseMailProvider, MailMessage


class FastApiMailProvider(BaseMailProvider):
    def __init__(self, config: ConnectionConfig):
        self._mailer = FastMail(config)

    async def send(self, message: MailMessage) -> None:
        recipients = [
            NameEmail(name=email, email=email) for email in message.recipients
        ]
        subtype = cast(MessageType, message.subtype)
        schema = MessageSchema(
            subject=message.subject,
            recipients=recipients,
            body=message.body,
            subtype=subtype,
            template_body=message.template_body or None,
        )
        if message.template_name:
            await self._mailer.send_message(schema, template_name=message.template_name)
        else:
            await self._mailer.send_message(schema)

    def get_provider_name(self) -> str:
        return "fastapi-mail"
