"""
Identificadores das entidades.

Todo ID é um UUID gerado pelo domínio no momento da criação (nunca pelo banco), então uma
entidade já nasce com identidade. Cada entidade tem o seu tipo para o mypy impedir que o ID de
uma seja passado no lugar do de outra (ex.: `UserId` onde se espera `UserPlantId`). O `UserId`
fica no kernel (`src.shared.domain`), porque todo módulo se refere ao usuário.
"""
from typing import NewType
from uuid import UUID

UserPlantId = NewType("UserPlantId", UUID)
HealthRecordId = NewType("HealthRecordId", UUID)
AchievementId = NewType("AchievementId", UUID)
