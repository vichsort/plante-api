"""
Composição do worker do Celery (carregada pelo `include` do `celery_app`): um container ligado às
tasks dos módulos. Cada task roda num event loop próprio (`run_async`), então os singletons (o
cliente do Redis, preso ao loop em que nasceu) são recriados a cada task.
"""
from celery.signals import task_postrun

from src.bootstrap.container import Container
from src.bootstrap.wiring import wire

container = Container()
wire(container)


@task_postrun.connect
def _fresh_singletons_for_the_next_task(**_: object) -> None:
    container.reset_singletons()
