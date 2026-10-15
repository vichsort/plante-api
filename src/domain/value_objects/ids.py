"""
Identificadores das entidades.

Todo ID é um UUID gerado pelo domínio no momento da criação (nunca pelo banco), então uma
entidade já nasce com identidade. Cada entidade tem o seu tipo para o mypy impedir que o ID de
uma seja passado no lugar do de outra (ex.: `UserId` onde se espera `UserPlantId`).
"""
from typing import NewType
from uuid import UUID

UserId = NewType("UserId", UUID)
UserPlantId = NewType("UserPlantId", UUID)
PlantSpeciesId = NewType("PlantSpeciesId", UUID)
IdentificationSampleId = NewType("IdentificationSampleId", UUID)
HealthRecordId = NewType("HealthRecordId", UUID)
HealthSampleId = NewType("HealthSampleId", UUID)
ReferenceImageId = NewType("ReferenceImageId", UUID)
AchievementId = NewType("AchievementId", UUID)
