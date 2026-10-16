from abc import abstractmethod
from contextvars import ContextVar, Token
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.shared.domain.ports.unit_of_work import IUnitOfWork

# A sessão da transação aberta no fluxo atual (requisição, task): um UoW aberto dentro de outro
# se junta a ela em vez de abrir uma conexão nova
_active_session: ContextVar[AsyncSession | None] = ContextVar("plante_active_session", default=None)


class SqlAlchemyUnitOfWork(IUnitOfWork):
    """Base dos UoW concretos: cuida da sessão; a subclasse só liga os repositórios (`_bind`)."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._owner_token: Token[AsyncSession | None] | None = None

    @abstractmethod
    def _bind(self, session: AsyncSession) -> None:
        """Cria os repositórios do módulo sobre a sessão da transação."""

    @property
    def joined(self) -> bool:
        if self._session is None:
            raise RuntimeError("Unit of work is not open.")
        return self._owner_token is None

    async def __aenter__(self) -> Self:
        if self._session is not None:
            raise RuntimeError("Unit of work already open: nested `async with` is not supported.")
        active = _active_session.get()
        if active is None:
            self._session = self._session_factory()
            self._owner_token = _active_session.set(self._session)
        else:
            self._session = active
        self._bind(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        session, token = self._session, self._owner_token
        self._session, self._owner_token = None, None
        if session is None or token is None:
            return  # quem se juntou não fecha a transação de outro
        try:
            await session.rollback()  # sem efeito depois de um commit
        finally:
            await session.close()
            _active_session.reset(token)

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not open.")
        if self._owner_token is None:
            raise RuntimeError("Only the unit of work that opened the transaction can commit it.")
        await self._session.commit()
