"""
Liga os containers às entradas (rotas e tasks). A ligação do `dependency-injector` é global, por
módulo Python: a última chamada vence, e é por isso que o app, o worker e os testes passam por aqui.
"""
from src.bootstrap.container import Container

# Entradas do código antigo, ligadas ao container raiz
_LEGACY_ENTRYPOINTS = [
    "src.api.routers.health",
    "src.api.routers.profile",
    "src.bootstrap.probes",
]


def wire(container: Container) -> None:
    container.wire(modules=_LEGACY_ENTRYPOINTS)
    # Cada módulo liga as próprias entradas ao container dele (aninhado no raiz)
    container.identity().wire(modules=["src.modules.identity.api.router", "src.modules.identity.workers.tasks"])
    container.subscription().wire(modules=["src.modules.subscription.api.router"])
    container.identification().wire(modules=["src.modules.identification.api.router"])
    container.garden().wire(modules=["src.modules.garden.api.router", "src.modules.garden.workers.tasks"])
