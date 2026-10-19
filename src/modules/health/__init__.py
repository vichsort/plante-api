"""
health: o diagnóstico de saúde de uma planta do jardim a partir de uma foto (README.md). A API
pública é só domínio; a composição monta o módulo por `src.modules.health.container` e `.api`.
"""
from src.modules.health.domain.entities.health_record import HealthRecord
from src.modules.health.domain.exceptions import HealthRecordNotFoundError
from src.modules.health.domain.value_objects.ids import HealthRecordId

__all__ = [
    "HealthRecord",
    "HealthRecordId",
    "HealthRecordNotFoundError",
]
