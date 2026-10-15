import asyncio

import firebase_admin
import structlog
from firebase_admin import credentials, messaging

from src.domain.ports.notification_sender import INotificationSender, Notification
from src.domain.value_objects.ids import UserId

log = structlog.stdlib.get_logger()


class FirebaseAdapter(INotificationSender):
    def __init__(self, credentials_path: str) -> None:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(credentials_path))

    async def send(self, notification: Notification) -> bool:
        message = messaging.Message(
            notification=messaging.Notification(title=notification.title, body=notification.body),
            token=notification.fcm_token,
            data={"type": notification.notification_type.value, **notification.data},
        )
        try:
            # firebase_admin é síncrono: roda numa thread para não bloquear o event loop
            await asyncio.to_thread(messaging.send, message)
        except messaging.UnregisteredError:
            log.info("push.token_unregistered", user_id=str(notification.user_id))
            return False
        return True

    async def send_batch(self, notifications: list[Notification]) -> dict[UserId, bool]:
        return {n.user_id: await self.send(n) for n in notifications}
