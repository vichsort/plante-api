"""
Composição do worker do Celery (carregada pelo `include` do `celery_app`): um container ligado às
tasks dos módulos. Cada task roda num event loop próprio (`run_async`), e os clientes de rede ficam
presos ao loop em que nasceram. Por isso, no fim de cada task e ainda dentro do loop dela, as
conexões são fechadas e os singletons recriados para a próxima (antes o reset vinha depois do
loop fechado, e o coletor de lixo fechava o Redis com aviso "Event loop is closed").
"""
from src.bootstrap.connections import close_connections
from src.bootstrap.container import Container
from src.bootstrap.wiring import wire
from src.shared.workers import on_task_loop_end

container = Container()
wire(container)


async def _close_task_connections() -> None:
    await close_connections(container)
    container.reset_singletons()


on_task_loop_end(_close_task_connections)
