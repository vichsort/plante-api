import structlog

from src.modules.identity.domain.ports.token_repository import ITokenRepository
from src.shared.domain import UserId

log = structlog.stdlib.get_logger()

class LogoutUseCase:
    raises = ()

    def __init__(self, token_repo: ITokenRepository) -> None:
        self._token_repo = token_repo

    async def execute(self, user_id: UserId) -> None:
        await self._token_repo.delete_refresh_token(user_id)
        log.info("user.logout", user_id=str(user_id))