from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from src.domain.ports.achievement_repository import IAchievementRepository
from src.domain.ports.health_identification_sample_repository import (
    IHealthIdentificationSampleRepository,
)
from src.domain.ports.health_record_repository import IHealthRecordRepository
from src.domain.ports.identification_sample_repository import (
    IIdentificationSampleRepository,
)
from src.domain.ports.plant_nutritional_repository import IPlantNutritionalRepository
from src.domain.ports.plant_reference_image_repository import (
    IPlantReferenceImageRepository,
)
from src.domain.ports.plant_species_repository import IPlantSpeciesRepository
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.ports.user_repository import IUserRepository


class IUnitOfWork(ABC):
    """
    Transação do banco: os repositórios só existem dentro de `async with uow:` e compartilham
    a mesma transação. Nada é gravado sem `await uow.commit()`; ao sair do bloco, o que não foi
    confirmado é desfeito (inclusive quando há exceção).

    O use case define a fronteira: lê e grava dentro do bloco, confirma e só então publica
    eventos ou chama serviços que não podem ser desfeitos. Chamadas externas lentas (IA, S3)
    ficam fora do bloco para não segurar uma conexão; o mesmo `uow` pode ser aberto de novo
    depois (cada `async with` é uma transação nova).

    Cache e arquivos (Redis, S3) não fazem parte da transação.
    """

    users: IUserRepository
    user_plants: IUserPlantRepository
    species: IPlantSpeciesRepository
    nutritional: IPlantNutritionalRepository
    reference_images: IPlantReferenceImageRepository
    identification_samples: IIdentificationSampleRepository
    health_records: IHealthRecordRepository
    health_samples: IHealthIdentificationSampleRepository
    achievements: IAchievementRepository

    @abstractmethod
    async def __aenter__(self) -> Self:
        ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Desfaz o que não foi confirmado e libera a conexão."""
        ...

    @abstractmethod
    async def commit(self) -> None:
        ...
