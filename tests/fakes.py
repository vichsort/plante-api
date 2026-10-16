"""Dublês tipados das portas para os testes unitários."""
from types import TracebackType
from typing import Self
from unittest.mock import AsyncMock

from src.domain.ports.unit_of_work import IUnitOfWork
from src.shared.domain import IImageSanitizer


class FakeUnitOfWork(IUnitOfWork):
    """
    Repositórios em `AsyncMock` (sobrescrevíveis por nome) e contagem de commits. `committed`
    diz se a última transação aberta foi confirmada.
    """

    def __init__(self, **repositories: AsyncMock) -> None:
        for name in IUnitOfWork.__annotations__:  # só os repositórios (a base não declara atributos)
            setattr(self, name, repositories.pop(name, AsyncMock()))
        if repositories:
            raise TypeError(f"Unknown repositories: {sorted(repositories)}")
        self.commits = 0
        self.committed = False
        self.opened = 0

    async def __aenter__(self) -> Self:
        self.opened += 1
        self.committed = False
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    @property
    def joined(self) -> bool:
        return False

    async def commit(self) -> None:
        self.commits += 1
        self.committed = True


class MarkingSanitizer(IImageSanitizer):
    """Prefixa os bytes: o teste confere que provedores e armazenamento só recebem a imagem limpa."""

    def sanitize(self, image_bytes: bytes) -> bytes:
        return b"clean:" + image_bytes
