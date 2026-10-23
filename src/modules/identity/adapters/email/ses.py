import asyncio

import boto3

from src.modules.identity.adapters.email.messages import (
    EmailMessage,
    password_changed,
    verification_code,
)
from src.modules.identity.domain.ports.email_sender import IEmailSender


class SesEmailSender(IEmailSender):
    def __init__(self, region: str, sender_email: str) -> None:
        self._client = boto3.client("ses", region_name=region)
        self._sender = sender_email

    async def send_verification_code(self, to_email: str, code: str) -> None:
        await self._send(to_email, verification_code(code))

    async def send_password_changed_notice(self, to_email: str) -> None:
        await self._send(to_email, password_changed())

    async def _send(self, to_email: str, message: EmailMessage) -> None:
        await asyncio.to_thread(
            self._client.send_email,
            Source=self._sender,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": message.subject},
                "Body": {"Text": {"Data": message.body}},
            },
        )
