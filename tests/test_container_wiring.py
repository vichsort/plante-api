# tests/test_container_wiring.py
from src.infrastructure.container import Container


def test_container_wires_without_error():
    container = Container()
    container.wire(modules=[
        "src.api.deps",
        "src.api.routers.auth",
        "src.api.routers.identification",
        "src.api.routers.garden",
        "src.api.routers.plants",
        "src.api.routers.health",
        "src.api.routers.profile",
        "src.api.routers.probes",
    ])