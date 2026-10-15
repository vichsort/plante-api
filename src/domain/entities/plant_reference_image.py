from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from src.domain.value_objects.ids import ReferenceImageId, UserId


class ImageSource(StrEnum):
    KINDWISE_SIMILAR = "kindwise_similar"
    PLANTNET_SIMILAR = "plantnet_similar"
    USER_CONFIRMED = "user_confirmed"

@dataclass(frozen=True)
class PlantReferenceImage:
    id: ReferenceImageId
    scientific_name: str
    storage_key: str
    source: ImageSource
    created_at: datetime

    user_id: UserId | None = None

    def __post_init__(self) -> None:
        if not self.scientific_name:
            raise ValueError("scientific_name cannot be empty.")
        if not self.storage_key:
            raise ValueError("storage_key cannot be empty.")
        if self.source == ImageSource.USER_CONFIRMED and self.user_id is None:
            raise ValueError("user_confirmed images must have a user_id.")
        if self.source != ImageSource.USER_CONFIRMED and self.user_id is not None:
            raise ValueError(f"{self.source.value} images must not have a user_id.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")