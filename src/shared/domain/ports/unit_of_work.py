from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self


class IUnitOfWork(ABC):
    """
    Transação do banco. Os repositórios só existem dentro de `async with uow:` e compartilham a
    mesma transação. Nada é gravado sem `await uow.commit()`; ao sair do bloco, o que não foi
    confirmado é desfeito (inclusive quando há exceção).

    **Uma transação física por vez.** O primeiro UoW aberto é o dono: confirma e fecha. Um UoW
    aberto dentro dele (o de outro módulo, chamado por um `service`) só se junta à mesma
    transação (`joined`) e não pode confirmar. Assim, gravar a amostra de treino e cobrar o token
    acontece junto com a identificação, ou nada acontece.

    Cada módulo estende esta porta com os próprios repositórios (o UoW do módulo é uma visão da
    transação, não uma sessão separada). Cache e arquivos (Redis, S3) não fazem parte dela.
    """

    @property
    @abstractmethod
    def joined(self) -> bool:
        """Dentro do bloco: True se entrou numa transação aberta por outro UoW."""
        ...

    @abstractmethod
    async def __aenter__(self) -> Self:
        ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Dono: desfaz o que não foi confirmado e libera a conexão. Quem se juntou: nada."""
        ...

    @abstractmethod
    async def commit(self) -> None:
        """Só o dono confirma; quem se juntou recebe erro (a fronteira é do use case que abriu)."""
        ...
