from dataclasses import dataclass
from src.domain.exceptions import PlantEError
from src.domain.entities.user import User
from src.domain.ports.user_repository import IUserRepository
from src.domain.ports.password_hasher import IPasswordHasher
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.events.domain_events import UserRegisteredEvent

class EmailAlreadyInUseError(PlantEError):
    def __init__(self):
        super().__init__("Este e-mail já está cadastrado.", "EMAIL_IN_USE")

@dataclass(frozen=True)
class RegisterUserInputDTO:
    email: str
    password: str
    country: str
    state: str

class RegisterUserUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        hasher: IPasswordHasher,
        publisher: IDomainPublisher
    ):
        self.user_repo = user_repo
        self.hasher = hasher
        self.publisher = publisher

    def execute(self, dto: RegisterUserInputDTO) -> dict:
        # E-mail deve ser único
        if self.user_repo.get_by_email(dto.email):
            raise EmailAlreadyInUseError()

        # Embaralha a senha usando a porta
        hashed_pw = self.hasher.hash(dto.password)

        # Nasce a Entidade User (Free, 0 tokens, is_verified=False)
        user = User.create_new(
            email=dto.email,
            hashed_password=hashed_pw,
            country=dto.country,
            state=dto.state
        )

        saved_user = self.user_repo.save(user)

        # O NotificationAdapter vai escutar isso e enviar o e-mail
        event = UserRegisteredEvent.create(user_id=saved_user.id, email=saved_user.email)
        self.publisher.publish(event)

        return {
            "user_id": saved_user.id,
            "message": "Cadastro realizado. Verifique seu e-mail para ativar a conta."
        }