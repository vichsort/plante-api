"""Accepting the terms: only the version in force, and the consent is on record."""
import pytest

from src.modules.identity.domain.exceptions import TermsNotAcceptedError
from src.modules.identity.domain.use_cases.accept_terms import (
    AcceptTermsInputDTO,
    AcceptTermsUseCase,
)
from src.modules.identity.domain.value_objects.terms import Terms
from src.modules.identity.tests.fakes import (
    FakeIdentityUnitOfWork,
    InMemoryUserRepository,
    make_user,
)

NEW_TERMS = Terms(version="2")


async def test_accepting_the_new_version_records_it() -> None:
    # Arrange: accepted version 1, version 2 is in force
    user = make_user(terms_version="1")
    uow = FakeIdentityUnitOfWork(InMemoryUserRepository(user))

    # Act
    await AcceptTermsUseCase(uow, NEW_TERMS).execute(AcceptTermsInputDTO(user_id=user.id, version="2"))

    # Assert
    assert user.has_accepted("2") and uow.commits == 1


async def test_accepting_another_version_is_refused() -> None:
    # Arrange
    user = make_user(terms_version="1")
    uow = FakeIdentityUnitOfWork(InMemoryUserRepository(user))

    # Act & Assert
    with pytest.raises(TermsNotAcceptedError):
        await AcceptTermsUseCase(uow, NEW_TERMS).execute(AcceptTermsInputDTO(user_id=user.id, version="1"))
    assert (user.terms_version, uow.commits) == ("1", 0)
