"""Identificador da identificação: UUID gerado pelo domínio na criação (nunca pelo banco)."""
from typing import NewType
from uuid import UUID

IdentificationId = NewType("IdentificationId", UUID)
