# tests/test_container_wiring.py
import pytest
from dependency_injector import providers

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

def test_every_subcontainer_dependency_is_provided():
    container = Container()
    undefined = [
        f"{name}.{dep_name}"
        for name, sub in container.providers.items()
        if isinstance(sub, providers.Container)
        for dep_name, dep in sub.container.providers.items()
        if isinstance(dep, providers.Dependency) and not dep.is_defined
    ]
    assert undefined == []


@pytest.mark.parametrize("consensus_enabled", ["true", "false"])
def test_every_use_case_resolves(monkeypatch, consensus_enabled):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("CONSENSUS_ENABLED", consensus_enabled)
    container = Container()
    for provider in container.use_cases.container.providers.values():
        if not isinstance(provider, providers.Dependency):
            provider()


def test_ai_breakers_use_settings_thresholds(monkeypatch):
    monkeypatch.setenv("AI_BREAKER_FAILURE_THRESHOLD", "2")
    monkeypatch.setenv("AI_BREAKER_RECOVERY_TIMEOUT_SECONDS", "7.5")
    container = Container()
    for breaker in (container.adapters.kindwise_breaker(), container.adapters.plantnet_breaker()):
        assert breaker._failure_threshold == 2
        assert breaker._recovery_timeout == 7.5
