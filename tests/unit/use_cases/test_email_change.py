"""Troca de e-mail: o endereço novo só vale depois do código (antes trocava na hora e trancava a conta)."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.entities.user import User
from src.domain.exceptions import EmailAlreadyInUseError
from src.domain.use_cases.change_email_use_case import (
    ChangeEmailInputDTO,
    ChangeEmailUseCase,
)
from src.domain.use_cases.verify_email_use_case import (
    VerifyEmailInputDTO,
    VerifyEmailUseCase,
)
from tests.factories import make_user
from tests.fakes import FakeUnitOfWork

CODE = "PLA1234567"


def _users(user: User, taken: User | None = None) -> AsyncMock:
    users = AsyncMock()
    users.get_by_id.return_value = user
    users.get_by_email.return_value = taken
    return users


def _otp() -> AsyncMock:
    otp = AsyncMock()
    otp.get_active_code_for_user.return_value = CODE
    return otp


@pytest.mark.asyncio
async def test_requesting_a_change_keeps_the_current_email_working():
    # Arrange
    user = make_user(email="atual@plante.org", is_verified=True)
    email_sender = AsyncMock()
    hasher = MagicMock()
    hasher.verify.return_value = True
    use_case = ChangeEmailUseCase(uow=FakeUnitOfWork(users=_users(user)), otp_repo=AsyncMock(), hasher=hasher, email_sender=email_sender)

    # Act
    await use_case.execute(ChangeEmailInputDTO(user_id=user.id, current_password="x", new_email="Novo@Plante.org"))

    # Assert
    assert (user.email, user.pending_email, user.is_verified) == ("atual@plante.org", "novo@plante.org", True)
    assert email_sender.send_verification_code.call_args.kwargs["to_email"] == "novo@plante.org"


@pytest.mark.asyncio
async def test_code_confirms_the_pending_email():
    # Arrange
    user = make_user(email="atual@plante.org", is_verified=True)
    user.request_email_change("novo@plante.org")
    otp = _otp()
    uow = FakeUnitOfWork(users=_users(user))

    # Act
    await VerifyEmailUseCase(uow=uow, otp_repo=otp).execute(VerifyEmailInputDTO(user_id=user.id, raw_code=CODE))

    # Assert
    assert (user.email, user.pending_email, user.is_verified) == ("novo@plante.org", None, True)
    assert uow.committed
    otp.consume_code.assert_awaited_once_with(user.id)


@pytest.mark.asyncio
async def test_address_taken_meanwhile_is_not_confirmed():
    # Arrange
    user = make_user(email="atual@plante.org", is_verified=True)
    user.request_email_change("novo@plante.org")
    uow = FakeUnitOfWork(users=_users(user, taken=make_user(email="novo@plante.org")))

    # Act & Assert
    with pytest.raises(EmailAlreadyInUseError):
        await VerifyEmailUseCase(uow=uow, otp_repo=_otp()).execute(VerifyEmailInputDTO(user_id=user.id, raw_code=CODE))
    assert user.email == "atual@plante.org"
    assert not uow.committed
