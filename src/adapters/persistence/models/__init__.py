from src.shared.adapters import Base

from .achievement_model import AchievementModel
from .health_record_model import HealthRecordModel
from .user_plant_model import UserPlantModel

# obs: models/care_model.py (para o CareSchedule) é completamente achatado em
# models/user_plant_model.py, então não tem mais um modelo separado por que sua
# única interação é justamente com essa tabela sendo 1-para-1. Se futuramente for 
# necessário para alguma coisa ter o care schedule separado fazemos uma tabela.

__all__ = [
    "Base",
    "UserPlantModel",
    "HealthRecordModel",
    'AchievementModel'
]
