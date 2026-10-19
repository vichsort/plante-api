import asyncio
import functools
from collections.abc import Awaitable, Callable, Coroutine

_loop_cleanups: list[Callable[[], Awaitable[None]]] = []


def on_task_loop_end(cleanup: Callable[[], Awaitable[None]]) -> None:
    """
    Registra uma limpeza que roda no fim de cada task, ainda dentro do event loop dela (a composição
    do worker fecha aqui os clientes de rede, presos ao loop em que nasceram).
    """
    _loop_cleanups.append(cleanup)


def run_async[**P, R](
    async_fn: Callable[P, Coroutine[object, object, R]],
) -> Callable[P, R | asyncio.Task[R]]:
    """
    Decorator para transformar corrotinas async def em funções síncronas
    compátiveis com o Celery, gerenciando o event loop de forma isolada e segura.
    Dentro de um event loop já rodando (pool assíncrono), agenda a corrotina e devolve a Task;
    nesse caso o loop continua vivo e as limpezas de `on_task_loop_end` não rodam.
    """
    @functools.wraps(async_fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | asyncio.Task[R]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            return loop.create_task(async_fn(*args, **kwargs))
        return asyncio.run(_with_cleanups(async_fn(*args, **kwargs)))

    return wrapper


async def _with_cleanups[R](task: Coroutine[object, object, R]) -> R:
    try:
        return await task
    finally:
        for cleanup in _loop_cleanups:
            await cleanup()
