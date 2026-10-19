import asyncio

from src.shared.workers import async_runner, on_task_loop_end, run_async


def test_cleanup_runs_inside_the_task_event_loop_even_when_the_task_fails() -> None:
    # Arrange
    loops: list[asyncio.AbstractEventLoop] = []
    task_loops: list[asyncio.AbstractEventLoop] = []

    async def cleanup() -> None:
        loops.append(asyncio.get_running_loop())

    @run_async
    async def task() -> None:
        task_loops.append(asyncio.get_running_loop())
        raise RuntimeError("boom")

    on_task_loop_end(cleanup)

    # Act
    try:
        task()
    except RuntimeError:
        pass
    finally:
        async_runner._loop_cleanups.remove(cleanup)

    # Assert
    assert loops == task_loops
