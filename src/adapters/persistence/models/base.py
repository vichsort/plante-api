from sqlalchemy.orm import DeclarativeBase, MappedColumn, mapped_column
from sqlalchemy import DateTime
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

def utcnow() -> datetime:
    return datetime.now(timezone.utc)