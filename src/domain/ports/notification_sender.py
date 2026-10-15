from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

from src.domain.value_objects.ids import UserId


class NotificationType(StrEnum):
    CARE_REMINDER = "care_reminder"         # lembrete de rega/poda
    WEATHER_ALERT = "weather_alert"         # evento climático crítico
    HEALTH_ALERT = "health_alert"           # planta precisa de atenção
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    ENRICHMENT_READY = "enrichment_ready"   # deep analysis concluída

@dataclass(frozen=True)
class Notification:
    user_id: UserId
    fcm_token: str
    notification_type: NotificationType
    title: str
    body: str
    data: dict[str, str]  # o FCM só aceita valores string no payload

class INotificationSender(ABC):
    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """Envia uma notificação push. Retorna True se enviada com sucesso."""
        ...

    @abstractmethod
    async def send_batch(self, notifications: list[Notification]) -> dict[UserId, bool]:
        """
        Envia múltiplas notificações.
        Retorna dict {user_id: sucesso} pra rastrear falhas individuais.
        """
        ...