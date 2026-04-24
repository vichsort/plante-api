import boto3
from src.domain.ports.email_sender import IEmailSender

class SesEmailSender(IEmailSender):
    def __init__(self, region: str, sender_email: str) -> None:
        self._client = boto3.client("ses", region_name=region)
        self._sender = sender_email

    async def send_verification_code(self, to_email: str, code: str) -> None:
        import asyncio
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._client.send_email(
                Source=self._sender,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": "Seu código PlantE"},
                    "Body": {"Text": {"Data": f"Seu código de verificação: {code}"}},
                },
            ),
        )