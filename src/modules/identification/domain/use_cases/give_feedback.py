from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.identification.domain.exceptions import IdentificationNotFoundError
from src.modules.identification.domain.ports.unit_of_work import (
    IIdentificationUnitOfWork,
)
from src.modules.identification.domain.value_objects.ids import IdentificationId
from src.modules.training import (
    FeedbackOrigin,
    FeedbackVerdict,
    IdentificationLabel,
    ITrainingRecorder,
)
from src.shared.domain import UserId


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

    def __init__(self, uow: IIdentificationUnitOfWork, training: ITrainingRecorder) -> None:
        self.uow = uow
        self.training = training

    async def execute(self, dto: GiveIdentificationFeedbackInputDTO) -> None:
        async with self.uow as uow:
            identification = await uow.identifications.get_for_user(dto.identification_id, dto.user_id)
            if identification is None:
                raise IdentificationNotFoundError(dto.identification_id)

            await self.training.record_feedback(
                IdentificationLabel(identification.training_sample_id, dto.suggested_name),
                dto.verdict,
                FeedbackOrigin.EXPLICIT,
                given_on=datetime.now(UTC).date(),
            )
            await uow.commit()
