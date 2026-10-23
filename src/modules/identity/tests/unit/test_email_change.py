"""Troca de e-mail: o endereço novo só vale depois do código (antes trocava na hora e trancava a conta)."""
import pytest

from src.modules.identity.domain.exceptions import (
    EmailAlreadyInUseError,
    InvalidCredentialsError,
    InvalidVerificationCodeError,
)
from src.modules.identity.domain.use_cases.change_email import (
    ChangeEmailInputDTO,
    ChangeEmailUseCase,
)
from src.modules.identity.domain.use_cases.verify_email import (
    VerifyEmailInputDTO,
    VerifyEmailUseCase,
)
from src.modules.identity.tests.fakes import (
    FakeIdentityUnitOfWork,
    InMemoryOtpRepository,
    InMemoryUserRepository,
    PlainHasher,
    RecordingEmailSender,
    make_user,
)

CODE = "PLA1234567"  # formato válido: 1+2+3+5+6+7 = 24, dígito verificador 4


async def test_requesting_a_change_keeps_the_current_email_working() -> None:
    # Arrange
    user = make_user(email="atual@plante.org")
    otp, sender = InMemoryOtpRepository(), RecordingEmailSender()
    use_case = ChangeEmailUseCase(
        uow=FakeIdentityUnitOfWork(InMemoryUserRepository(user)), otp_repo=otp, hasher=PlainHasher(), email_sender=sender,
        verification_required=True,
    )

    # Act
    await use_case.execute(ChangeEmailInputDTO(user_id=user.id, current_password="Secret1password", new_email="Novo@Plante.org"))

    # Assert
    assert (user.email, user.pending_email, user.is_verified) == ("atual@plante.org", "novo@plante.org", True)
    assert sender.sent == [("novo@plante.org", otp.codes[user.id])]


async def test_wrong_password_does_not_start_a_change() -> None:
    # Arrange
    user = make_user(email="atual@plante.org")
    sender = RecordingEmailSender()
    use_case = ChangeEmailUseCase(
        uow=FakeIdentityUnitOfWork(InMemoryUserRepository(user)), otp_repo=InMemoryOtpRepository(), hasher=PlainHasher(),
        email_sender=sender, verification_required=True,
    )

    # Act & Assert
    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(ChangeEmailInputDTO(user_id=user.id, current_password="wrong", new_email="novo@plante.org"))
    assert (user.pending_email, sender.sent) == (None, [])


async def test_without_verification_the_new_email_applies_at_once() -> None:
    # Arrange: nobody could receive the code
    user = make_user(email="atual@plante.org")
    otp, sender = InMemoryOtpRepository(), RecordingEmailSender()
    use_case = ChangeEmailUseCase(
        uow=FakeIdentityUnitOfWork(InMemoryUserRepository(user)), otp_repo=otp, hasher=PlainHasher(), email_sender=sender,
        verification_required=False,
    )

    # Act
    await use_case.execute(ChangeEmailInputDTO(user_id=user.id, current_password="Secret1password", new_email="novo@plante.org"))

    # Assert
    assert (user.email, user.pending_email) == ("novo@plante.org", None)
    assert (sender.sent, otp.codes) == ([], {})


async def test_code_confirms_the_pending_email() -> None:
    # Arrange
    user = make_user(email="atual@plante.org")
    user.request_email_change("novo@plante.org")
    otp = InMemoryOtpRepository()
    otp.codes[user.id] = CODE
    uow = FakeIdentityUnitOfWork(InMemoryUserRepository(user))

    # Act
    await VerifyEmailUseCase(uow=uow, otp_repo=otp).execute(VerifyEmailInputDTO(user_id=user.id, raw_code="PLA-123-4-567"))

    # Assert
    assert (user.email, user.pending_email, user.is_verified) == ("novo@plante.org", None, True)
    assert uow.commits == 1
    assert user.id not in otp.codes


async def test_address_taken_meanwhile_is_not_confirmed() -> None:
    # Arrange
    user = make_user(email="atual@plante.org")
    user.request_email_change("novo@plante.org")
    otp = InMemoryOtpRepository()
    otp.codes[user.id] = CODE
    uow = FakeIdentityUnitOfWork(InMemoryUserRepository(user, make_user(email="novo@plante.org")))

    # Act & Assert
    with pytest.raises(EmailAlreadyInUseError):
        await VerifyEmailUseCase(uow=uow, otp_repo=otp).execute(VerifyEmailInputDTO(user_id=user.id, raw_code=CODE))
    assert (user.email, uow.commits) == ("atual@plante.org", 0)


async def test_wrong_code_does_not_verify() -> None:
    # Arrange
    user = make_user(is_verified=False)
    otp = InMemoryOtpRepository()
    otp.codes[user.id] = CODE
    uow = FakeIdentityUnitOfWork(InMemoryUserRepository(user))

    # Act & Assert: formato válido, mas não é o código enviado
    with pytest.raises(InvalidVerificationCodeError):
        await VerifyEmailUseCase(uow=uow, otp_repo=otp).execute(VerifyEmailInputDTO(user_id=user.id, raw_code="PLA0000000"))
    assert user.is_verified is False
