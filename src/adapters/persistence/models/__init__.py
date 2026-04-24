from .base import Base
from .user_model import UserModel
from .plant_species_model import PlantSpeciesModel
from .plant_nutritional_model import PlantNutritionalModel
from .plant_reference_image_model import PlantReferenceImageModel
from .user_plant_model import UserPlantModel
from .plant_identification_sample_model import PlantIdentificationSampleModel
from .health_record_model import HealthRecordModel

# obs: models/care_model.py (para o CareSchedule) é completamente achatado em
# models/user_plant_model.py, então não tem mais um modelo separado por que sua
# única interação é justamente com essa tabela sendo 1-para-1. Se futuramente for 
# necessário para alguma coisa ter o care schedule separado fazemos uma tabela.

__all__ = [
    "Base",
    "UserModel",
    "PlantSpeciesModel",
    "PlantNutritionalModel",
    "PlantReferenceImageModel",
    "UserPlantModel",
    "PlantIdentificationSampleModel",
    'HealthRecordModel'
]