import asyncio
import functools
from collections.abc import Callable
from typing import Any


def run_async(async_fn: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator para transformar corrotinas async def em funções síncronas
    compátiveis com o Celery, gerenciando o event loop de forma isolada e segura.
    """
    @functools.wraps(async_fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            return loop.create_task(async_fn(*args, **kwargs))
        else:
            return asyncio.run(async_fn(*args, **kwargs))

    return wrapper
