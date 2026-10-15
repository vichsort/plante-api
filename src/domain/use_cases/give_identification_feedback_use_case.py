from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.entities.training import (
    FeedbackOrigin,
    FeedbackVerdict,
    TrainingFeedback,
)
from src.domain.exceptions import IdentificationNotFoundError
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import IdentificationId, UserId


@dataclass(frozen=True)
class GiveIdentificationFeedbackInputDTO:
    user_id: UserId
    identification_id: IdentificationId
    verdict: FeedbackVerdict
    suggested_name: str | None = None


class GiveIdentificationFeedbackUseCase:
    """
    "Acertou / errou / não sei" sobre uma identificação, a qualquer momento e quantas vezes o
    usuário quiser: cada resposta é um evento na amostra de treino (sem dizer de quem veio).
    A sugestão de espécie é só uma candidata; quem decide o peso é a engine de confiança.
    """

    raises = (IdentificationNotFoundError,)

    def __init__(self, uow: IUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, dto: GiveIdentificationFeedbackInputDTO) -> None:
        async with self.uow as uow:
            identification = await uow.identifications.get_for_user(dto.identification_id, dto.user_id)
            if identification is None:
                raise IdentificationNotFoundError(dto.identification_id)

            await uow.training.add_feedback(TrainingFeedback.on_identification(
                sample_id=identification.training_sample_id,
                verdict=dto.verdict,
                origin=FeedbackOrigin.EXPLICIT,
                given_on=datetime.now(UTC).date(),
                suggested_name=dto.suggested_name,
            ))
            await uow.commit()
