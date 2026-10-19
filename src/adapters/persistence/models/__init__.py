from src.shared.adapters import Base

from .achievement_model import AchievementModel
from .health_record_model import HealthRecordModel

__all__ = [
    "Base",
    "HealthRecordModel",
    "AchievementModel",
]
