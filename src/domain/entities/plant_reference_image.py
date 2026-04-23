from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class ImageSource(Enum):
    KINDWISE_SIMILAR = "kindwise_similar"   # URL retornada pela Kindwise como imagem similar
    USER_CONFIRMED = "user_confirmed"       # Foto de usuário que confirmou a identificação

@dataclass(frozen=True)
class PlantReferenceImage:
    id: int | None
    scientific_name: str
    storage_key: str        # caminho no bucket: "references/aloe_vera/user_confirmed_xyz.jpg"
    source: ImageSource
    created_at: datetime

    user_id: int | None = None      # None se vier do Kindwise

    def __post_init__(self) -> None:
        if not self.scientific_name:
            raise ValueError("scientific_name cannot be empty.")
        if not self.storage_key:
            raise ValueError("storage_key cannot be empty.")
        if self.source == ImageSource.USER_CONFIRMED and self.user_id is None:
            raise ValueError("user_confirmed images must have a user_id.")
        if self.source == ImageSource.KINDWISE_SIMILAR and self.user_id is not None:
            raise ValueError("kindwise_similar images must not have a user_id.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")