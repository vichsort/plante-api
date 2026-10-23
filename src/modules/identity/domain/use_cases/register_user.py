from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.events import UserRegisteredEvent
from src.modules.identity.domain.exceptions import (
    CaptchaFailedError,
    EmailAlreadyInUseError,
    TermsNotAcceptedError,
    WeakPasswordError,
)
from src.modules.identity.domain.policies.password_policy import PasswordPolicy
from src.modules.identity.domain.ports.captcha_verifier import ICaptchaVerifier
from src.modules.identity.domain.ports.password_hasher import IPasswordHasher
from src.modules.identity.domain.ports.unit_of_work import IIdentityUnitOfWork
from src.modules.identity.domain.value_objects.email import normalize_email
from src.modules.identity.domain.value_objects.terms import Terms
from src.modules.identity.domain.value_objects.user_location import UserLocation
from src.shared.domain import ExternalServiceError, IDomainPublisher


@dataclass(frozen=True)
class RegisterUserInputDTO:
    email: str
    password: str
    country: str
    state: str
    accepted_terms_version: str | None = None
    captcha_token: str | None = None
    client_ip: str | None = None

class RegisterUserUseCase:
    raises = (CaptchaFailedError, EmailAlreadyInUseError, ExternalServiceError, TermsNotAcceptedError, WeakPasswordError)

    def __init__(
        self,
        uow: IIdentityUnitOfWork,
        hasher: IPasswordHasher,
        publisher: IDomainPublisher,
        captcha: ICaptchaVerifier,
        terms: Terms,
        verification_required: bool,
    ) -> None:
        self.uow = uow
        self.hasher = hasher
        self.publisher = publisher
        self.captcha = captcha
        self.terms = terms
        self.verification_required = verification_required

    async def execute(self, dto: RegisterUserInputDTO) -> User:
        # First of all: a bot learns nothing (not even whether the email is taken) without solving it
        if not await self.captcha.verify(dto.captcha_token, dto.client_ip):
            raise CaptchaFailedError()
        if dto.accepted_terms_version != self.terms.version:
            raise TermsNotAcceptedError(self.terms.version)
        email = normalize_email(dto.email)
        PasswordPolicy.enforce_strong(dto.password)
        hashed_pw = self.hasher.hash(dto.password)

        now = datetime.now(UTC)
        async with self.uow as uow:
            if await uow.users.get_by_email(email):
                raise EmailAlreadyInUseError()

            user = User.create_new(
                email=email,
                hashed_password=hashed_pw,
                location=UserLocation(country=dto.country, state=dto.state),
                current_time=now,
            )
            user.accept_terms(self.terms.version, now)
            if not self.verification_required:
                # No provider sends the code yet: the account is born verified
                user.verify_email()
            saved_user = await uow.users.save(user)
            await uow.commit()

        # Depois do commit: o e-mail de verificação não sai para usuário que não foi gravado
        await self.publisher.publish(UserRegisteredEvent.create(
            user_id=saved_user.id, email=saved_user.email, requires_verification=self.verification_required,
        ))

        return saved_user
