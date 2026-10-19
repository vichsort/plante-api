"""Identificador da conquista desbloqueada: UUID gerado na criação (nunca pelo banco)."""
from typing import NewType
from uuid import UUID

AchievementId = NewType("AchievementId", UUID)
