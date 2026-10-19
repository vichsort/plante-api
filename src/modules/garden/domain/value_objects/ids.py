"""Identificador da planta no jardim: UUID gerado pelo domínio na criação (nunca pelo banco)."""
from typing import NewType
from uuid import UUID

UserPlantId = NewType("UserPlantId", UUID)
