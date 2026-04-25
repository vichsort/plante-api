import structlog
from src.domain.ports.token_repository import ITokenRepository

log = structlog.get_logger()

class LogoutUseCase:
    def __init__(self, token_repo: ITokenRepository) -> None:
        self._token_repo = token_repo

    async def execute(self, user_id: int) -> None:
        await self._token_repo.delete_refresh_token(user_id)
        log.info("user.logout", user_id=user_id)