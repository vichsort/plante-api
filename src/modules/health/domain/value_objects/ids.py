"""Identificador do diagnóstico: UUID gerado pelo domínio na criação (nunca pelo banco)."""
from typing import NewType
from uuid import UUID

HealthRecordId = NewType("HealthRecordId", UUID)
