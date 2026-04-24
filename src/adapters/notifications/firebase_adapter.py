import firebase_admin
from firebase_admin import credentials, messaging
from src.domain.ports.notification_sender import INotificationSender

class FirebaseAdapter(INotificationSender):
    def __init__(self, credentials_path: str) -> None:
        if not firebase_admin._apps:
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred)

    async def send_push(
        self,
        fcm_token: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> None:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=fcm_token,
            data=data or {},
        )
        # firebase_admin é síncrono — roda em thread pool para não bloquear
        import asyncio
        await asyncio.get_event_loop().run_in_executor(
            None, messaging.send, message
        )

    async def invalidate_token(self, fcm_token: str) -> None:
        """Chamado quando UnregisteredError é recebido — sem retry."""
        pass  # token inválido é tratado no use case, não aqui