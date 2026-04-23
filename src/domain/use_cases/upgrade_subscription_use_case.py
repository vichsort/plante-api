from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from src.domain.exceptions import UserNotFoundError
from src.domain.ports.user_repository import IUserRepository
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.events.domain_events import SubscriptionUpgradedEvent

@dataclass(frozen=True)
class UpgradeSubscriptionInputDTO:
    user_id: int
    plan_duration_days: int = 30

class UpgradeSubscriptionUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        publisher: IDomainPublisher
    ):
        self.user_repo = user_repo
        self.publisher = publisher

    def execute(self, dto: UpgradeSubscriptionInputDTO) -> dict:
        user = self.user_repo.get_by_id(dto.user_id)
        if not user:
            raise UserNotFoundError(dto.user_id)

        # Define a data de expiração (Regra: hoje + duração do plano)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=dto.plan_duration_days)

        # O User agora vira PRO
        user.upgrade_to_pro(expires_at=expires_at)

        # Gamificação: Concede a medalha de apoiador/premium
        # (Isso pode ser feito via evento ou direto na entidade se tivermos a lista lá)
        # Por enquanto, vamos sinalizar no evento para o AchievementListener agir.

        self.user_repo.save(user)

        # Publica o evento: 
        # Isso vai disparar o e-mail de boas-vindas e a medalha no perfil.
        event = SubscriptionUpgradedEvent.create(
            user_id=user.id,
            plan_name="PRO",
            expires_at=expires_at
        )
        self.publisher.publish(event)

        return {
            "user_id": user.id,
            "new_tier": "PRO",
            "expires_at": expires_at.isoformat(),
            "message": "Parabéns! Você agora é um membro Premium do PlantE."
        }