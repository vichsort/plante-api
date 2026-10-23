from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.identity.domain.exceptions import TermsNotAcceptedError
from src.modules.identity.domain.ports.unit_of_work import IIdentityUnitOfWork
from src.modules.identity.domain.value_objects.terms import Terms
from src.shared.domain import UserId, UserNotFoundError


@dataclass(frozen=True)
class AcceptTermsInputDTO:
    user_id: UserId
    version: str


class AcceptTermsUseCase:
    """The user accepts the terms in force (after a new version, to use the AI again)."""

    raises = (TermsNotAcceptedError, UserNotFoundError)

    def __init__(self, uow: IIdentityUnitOfWork, terms: Terms) -> None:
        self.uow = uow
        self.terms = terms

    async def execute(self, dto: AcceptTermsInputDTO) -> None:
        # Only the version in force: accepting an old one would record consent to other text
        if dto.version != self.terms.version:
            raise TermsNotAcceptedError(self.terms.version)

        async with self.uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if user is None:
                raise UserNotFoundError(user_id=dto.user_id)
            user.accept_terms(dto.version, datetime.now(UTC))
            await uow.users.save(user)
            await uow.commit()
