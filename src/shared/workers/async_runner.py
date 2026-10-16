import asyncio
import functools
from collections.abc import Callable, Coroutine


def run_async[**P, R](
    async_fn: Callable[P, Coroutine[object, object, R]],
) -> Callable[P, R | asyncio.Task[R]]:
    """
    Decorator para transformar corrotinas async def em funções síncronas
    compátiveis com o Celery, gerenciando o event loop de forma isolada e segura.
    Dentro de um event loop já rodando (pool assíncrono), agenda a corrotina e devolve a Task.
    """
    @functools.wraps(async_fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | asyncio.Task[R]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            return loop.create_task(async_fn(*args, **kwargs))
        return asyncio.run(async_fn(*args, **kwargs))

    return wrapper
