import uuid
from datetime import UTC, datetime
from enum import Enum, StrEnum

from sqlalchemy import UUID, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


def enum_values(enum_cls: type[Enum]) -> list[str]:
    """`values_callable` do SAEnum: o banco guarda o valor de cada membro (não o nome)."""
    return [str(member) for member in enum_cls if isinstance(member, StrEnum)]

class Base(DeclarativeBase):
    pass

class AuditMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None