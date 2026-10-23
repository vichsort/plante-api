"""The text of each email, the same whichever backend sends it."""
from dataclasses import dataclass


@dataclass(frozen=True)
class EmailMessage:
    subject: str
    body: str


def verification_code(code: str) -> EmailMessage:
    return EmailMessage(subject="Seu código PlantE", body=f"Seu código de verificação: {code}")


def password_changed() -> EmailMessage:
    return EmailMessage(
        subject="Sua senha PlantE foi alterada",
        body="Sua senha do PlantE foi alterada com sucesso.",
    )
