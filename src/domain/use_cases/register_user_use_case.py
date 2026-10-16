from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.entities.user import User
from src.domain.events.domain_events import UserRegisteredEvent
from src.domain.exceptions import EmailAlreadyInUseError, WeakPasswordError
from src.domain.policies.password_policy import PasswordPolicy
from src.domain.ports.password_hasher import IPasswordHasher
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.email import normalize_email
from src.domain.value_objects.user_location import UserLocation
from src.shared.domain import IDomainPublisher


@dataclass(frozen=True)
class RegisterUserInputDTO:
    email: str
    password: str
    country: str
    state: str

class RegisterUserUseCase:
    raises = (EmailAlreadyInUseError, WeakPasswordError)

    def __init__(
        self,
        uow: IUnitOfWork,
        hasher: IPasswordHasher,
        publisher: IDomainPublisher,
    ) -> None:
        self.uow = uow
        self.hasher = hasher
        self.publisher = publisher

    async def execute(self, dto: RegisterUserInputDTO) -> User:
        email = normalize_email(dto.email)
        PasswordPolicy.enforce_strong(dto.password)
        hashed_pw = self.hasher.hash(dto.password)

        async with self.uow as uow:
            if await uow.users.get_by_email(email):
                raise EmailAlreadyInUseError()

            user = User.create_new(
                email=email,
                hashed_password=hashed_pw,
                location=UserLocation(country=dto.country, state=dto.state),
                current_time=datetime.now(UTC),
            )
            saved_user = await uow.users.save(user)
            await uow.commit()

        # Depois do commit: o e-mail de verificação não sai para usuário que não foi gravado
        await self.publisher.publish(UserRegisteredEvent.create(user_id=saved_user.id, email=saved_user.email))

        return saved_user
