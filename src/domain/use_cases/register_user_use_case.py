from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.domain.entities.user import User
from src.domain.events.domain_events import UserRegisteredEvent
from src.domain.exceptions import EmailAlreadyInUseError
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.password_hasher import IPasswordHasher
from src.domain.ports.user_repository import IUserRepository
from src.domain.value_objects.user_location import UserLocation


@dataclass(frozen=True)
class RegisterUserInputDTO:
    email: str
    password: str
    country: str
    state: str

class RegisterUserUseCase:
    raises = (EmailAlreadyInUseError,)

    def __init__(
        self,
        user_repo: IUserRepository,
        hasher: IPasswordHasher,
        publisher: IDomainPublisher,
    ) -> None:
        self.user_repo = user_repo
        self.hasher = hasher
        self.publisher = publisher

    async def execute(self, dto: RegisterUserInputDTO) -> dict[str, Any]:
        if await self.user_repo.get_by_email(dto.email):
            raise EmailAlreadyInUseError()

        hashed_pw = self.hasher.hash(dto.password)

        now = datetime.now(UTC)
        user = User.create_new(
            email=dto.email,
            hashed_password=hashed_pw,
            location=UserLocation(country=dto.country, state=dto.state),
            current_time=now,
        )

        saved_user = await self.user_repo.save(user)

        event = UserRegisteredEvent.create(user_id=saved_user.id, email=saved_user.email)
        await self.publisher.publish(event)

        return {
            "user_id": saved_user.id,
            "message": "Cadastro realizado. Verifique seu e-mail para ativar a conta.",
        }