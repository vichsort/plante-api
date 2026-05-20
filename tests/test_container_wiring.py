# tests/test_container_wiring.py
from src.infrastructure.container import Container

def test_container_wires_without_error():
    container = Container()
    container.wire(modules=[
        "src.api.deps",
        "src.api.routers.auth",
        "src.api.routers.identification",
        "src.api.routers.profile",
    ])