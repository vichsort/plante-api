# tests/test_container_wiring.py
import pytest
from dependency_injector import providers

from src.bootstrap.container import Container
from src.main import wire


def test_container_wires_without_error():
    wire(Container())

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
