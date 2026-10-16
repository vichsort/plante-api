from dataclasses import dataclass

import structlog

from src.domain.exceptions import UnauthorizedError
from src.domain.ports.token_repository import ITokenRepository
from src.domain.ports.token_service import ITokenService, TokenKind
from src.domain.use_cases.login_use_case import ACCESS_TOKEN_TTL, REFRESH_TOKEN_TTL

log = structlog.stdlib.get_logger()


@dataclass(frozen=True)
class RefreshResult:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenUseCase:
    """
    Rotação: cada refresh devolve um refresh token novo e o anterior deixa de valer. Um refresh
    token antigo (já trocado) que volta assinado corretamente é sinal de roubo: a sessão inteira é
    revogada e o usuário precisa entrar de novo. Efeito colateral aceito: um app que repete a
    mesma chamada de refresh (retry) também derruba a sessão.
    """

    raises = (UnauthorizedError,)

    def __init__(self, token_repo: ITokenRepository, token_service: ITokenService) -> None:
        self._token_repo = token_repo
        self._token_service = token_service

    async def execute(self, refresh_token: str) -> RefreshResult:
        user_id = self._token_service.verify(refresh_token, TokenKind.REFRESH)

        stored = await self._token_repo.get_refresh_token(user_id)
        if stored is None:
            raise UnauthorizedError("Refresh token revoked or superseded.")
        if stored != refresh_token:
            await self._token_repo.delete_refresh_token(user_id)
            log.warning("token.refresh_reused", user_id=str(user_id))
            raise UnauthorizedError("Refresh token revoked or superseded.")

        access_token = self._token_service.issue(user_id, TokenKind.ACCESS, ACCESS_TOKEN_TTL)
        new_refresh_token = self._token_service.issue(user_id, TokenKind.REFRESH, REFRESH_TOKEN_TTL)
        await self._token_repo.save_refresh_token(
            user_id=user_id,
            token=new_refresh_token,
            ttl_seconds=int(REFRESH_TOKEN_TTL.total_seconds()),
        )

        log.info("token.refreshed", user_id=str(user_id))
        return RefreshResult(access_token=access_token, refresh_token=new_refresh_token)
