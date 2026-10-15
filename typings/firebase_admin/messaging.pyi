class Notification:
    def __init__(self, title: str | None = None, body: str | None = None) -> None: ...

class Message:
    def __init__(
        self,
        data: dict[str, str] | None = None,
        notification: Notification | None = None,
        token: str | None = None,
    ) -> None: ...

class UnregisteredError(Exception): ...

def send(message: Message, dry_run: bool = False) -> str: ...
