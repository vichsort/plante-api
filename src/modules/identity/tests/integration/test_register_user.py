from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.identity.adapters.persistence.unit_of_work import (
    SqlAlchemyIdentityUnitOfWork,
)
from src.modules.identity.domain.events import UserRegisteredEvent
from src.modules.identity.domain.use_cases.register_user import (
    RegisterUserInputDTO,
    RegisterUserUseCase,
)
from src.modules.identity.tests.fakes import PlainHasher, StubCaptchaVerifier
from src.shared.domain import DomainEvent, IDomainPublisher


async def _user_exists(session_factory: async_sessionmaker[AsyncSession], email: str) -> bool:
    async with SqlAlchemyIdentityUnitOfWork(session_factory) as uow:
        return await uow.users.get_by_email(email) is not None


class _PublisherThatChecksPersistence(IDomainPublisher):
    """Ao receber o evento, confere numa sessão separada que o usuário já foi gravado."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.user_was_persisted: bool | None = None

    async def publish(self, event: DomainEvent) -> None:
        assert isinstance(event, UserRegisteredEvent)
        self.user_was_persisted = await _user_exists(self._session_factory, event.email)


async def test_register_persists_the_user_before_publishing(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange: o e-mail de verificação não pode sair para um usuário que não foi gravado
    publisher = _PublisherThatChecksPersistence(session_factory)
    use_case = RegisterUserUseCase(
        uow=SqlAlchemyIdentityUnitOfWork(session_factory), hasher=PlainHasher(), publisher=publisher,
        captcha=StubCaptchaVerifier(), verification_required=True,
    )

    # Act
    await use_case.execute(RegisterUserInputDTO(
        email="E2E@Plante.org", password="Secret123", country="BR", state="SP", captcha_token="captcha-ok",
    ))

    # Assert
    assert publisher.user_was_persisted is True
    assert await _user_exists(session_factory, "e2e@plante.org")
