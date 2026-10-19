"""Dublês das portas do kernel (sanitizer, armazenamento, eventos) para os testes de quem as usa."""
from dataclasses import dataclass, field

from src.shared.domain import (
    DomainEvent,
    IDomainPublisher,
    IImageSanitizer,
    IImageStorage,
    UserId,
)


class MarkingSanitizer(IImageSanitizer):
    """Prefixa os bytes: o teste confere que provedores e armazenamento só recebem a imagem limpa."""

    def sanitize(self, image_bytes: bytes) -> bytes:
        return b"clean:" + image_bytes


@dataclass
class RecordingImageStorage(IImageStorage):
    """Guarda os bytes de cada envio e devolve chaves previsíveis, no formato das reais."""
    user_uploads: list[bytes] = field(default_factory=list)
    training_uploads: list[bytes] = field(default_factory=list)
    rehosted: list[str] = field(default_factory=list)
    deleted_users: list[UserId] = field(default_factory=list)

    async def upload_identification_image(
        self, image_bytes: bytes, scientific_name: str, confidence_value: float, user_id: UserId,
    ) -> str:
        self.user_uploads.append(image_bytes)
        return f"identifications/{len(self.user_uploads)}.jpg"

    async def download_and_rehost(self, external_url: str, scientific_name: str) -> str:
        self.rehosted.append(external_url)
        return f"species/references/{len(self.rehosted)}.jpg"

    async def delete_user_images(self, user_id: UserId) -> int:
        self.deleted_users.append(user_id)
        return 0

    async def upload_training_image(self, image_bytes: bytes, scientific_name: str) -> str:
        self.training_uploads.append(image_bytes)
        return f"training/identifications/{len(self.training_uploads)}.jpg"


@dataclass
class RecordingPublisher(IDomainPublisher):
    events: list[DomainEvent] = field(default_factory=list)

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)
