from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from src.domain.entities.care_schedule import CareSchedule, CareType
from src.domain.entities.training import (
    FeedbackOrigin,
    FeedbackVerdict,
    TrainingFeedback,
)
from src.domain.entities.user_plant import (
    GardenPlant,
    IdentificationSource,
    IdentificationStatus,
    UserPlant,
)
from src.domain.events.domain_events import PlantAddedToGardenEvent
from src.domain.exceptions import (
    IdentificationNotFoundError,
    PlantLimitExceededError,
    UserNotFoundError,
)
from src.domain.policies.subscription_policy import SubscriptionPolicy
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.care_interval import CareInterval
from src.domain.value_objects.ids import IdentificationId, UserPlantId
from src.domain.value_objects.local_calendar import LocalCalendar
from src.domain.value_objects.sources import IdentificationOrigin
from src.shared.domain import IDomainPublisher, UserId


@dataclass(frozen=True)
class AddPlantToGardenInputDTO:
    user_id: UserId
    identification_id: IdentificationId
    nickname: str | None = None


# Origem da identificação -> como a planta registra quem a identificou
_IDENTIFICATION_SOURCE: dict[IdentificationOrigin, IdentificationSource] = {
    "kindwise": IdentificationSource.KINDWISE,
    "plantnet": IdentificationSource.PLANTNET,
    "consensus": IdentificationSource.CONSENSUS,
    "consensus_partial": IdentificationSource.CONSENSUS,
}


class AddPlantToGardenUseCase:
    """
    Cria a planta no jardim a partir de uma identificação. Adicionar é um sinal implícito de que
    a identificação acertou (peso baixo na engine de confiança). Idempotente: a mesma
    identificação devolve a planta que já está no jardim, sem novo sinal.
    """

    raises = (IdentificationNotFoundError, PlantLimitExceededError, UserNotFoundError)

    def __init__(
        self,
        uow: IUnitOfWork,
        publisher: IDomainPublisher,
        calendar: LocalCalendar,
    ) -> None:
        self.uow = uow
        self.publisher = publisher
        self.calendar = calendar

    async def execute(self, dto: AddPlantToGardenInputDTO) -> GardenPlant:
        now = datetime.now(UTC)
        today = self.calendar.date_of(now)

        async with self.uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if user is None:
                raise UserNotFoundError(user_id=dto.user_id)

            identification = await uow.identifications.get_for_user(dto.identification_id, dto.user_id)
            if identification is None:
                raise IdentificationNotFoundError(dto.identification_id)

            existing = await uow.user_plants.get_by_identification(identification.id, dto.user_id)
            if existing is not None:
                return GardenPlant.of(existing, today)

            plants_in_garden = await uow.user_plants.count_by_user(dto.user_id)
            SubscriptionPolicy.enforce_can_add_to_garden(user, plants_in_garden, now)

            plant = await uow.user_plants.save(UserPlant(
                id=UserPlantId(uuid4()),
                user_id=user.id,
                scientific_name=identification.scientific_name,
                identification_confidence=identification.confidence,
                identification_source=_IDENTIFICATION_SOURCE[identification.source],
                status=IdentificationStatus.IDENTIFIED,
                care_schedule=CareSchedule(
                    care_type=CareType.WATER,
                    interval=CareInterval(days=7),
                    is_active=True,
                    created_at=now,
                ),
                identification_id=identification.id,
                added_at=now,
                nickname=dto.nickname,
                primary_image_url=identification.image_key,
            ))

            await uow.training.add_feedback(TrainingFeedback.on_identification(
                sample_id=identification.training_sample_id,
                verdict=FeedbackVerdict.CORRECT,
                origin=FeedbackOrigin.ADDED_TO_GARDEN,
                given_on=now.date(),
            ))
            await uow.commit()

        await self.publisher.publish(PlantAddedToGardenEvent.create(
            user_id=user.id,
            user_plant_id=plant.id,
            species_id=identification.species_id,
            is_first_plant=plants_in_garden == 0,
        ))

        return GardenPlant.of(plant, today)
