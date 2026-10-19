# tests/test_container_wiring.py
import pytest
from dependency_injector import providers

from src.bootstrap.container import Container
from src.bootstrap.settings import Settings
from src.bootstrap.wiring import wire
from src.modules.identification.adapters.consensus.identifier import ConsensusIdentifier
from src.modules.identification.adapters.resilience.circuit_breaker import (
    CircuitBreakerPlantIdentifier,
)


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
    for sub in (container.use_cases, container.identification, container.garden, container.health):
        for provider in sub.container.providers.values():
            if not isinstance(provider, providers.Dependency):
                provider()


@pytest.mark.parametrize(("consensus_enabled", "expected"), [
    ("true", ConsensusIdentifier),
    ("false", CircuitBreakerPlantIdentifier),  # só o Kindwise, protegido pelo breaker
])
def test_consensus_setting_picks_the_identifier(monkeypatch, consensus_enabled, expected):
    monkeypatch.setenv("CONSENSUS_ENABLED", consensus_enabled)

    identifier = Container().identification.plant_identifier()

    assert type(identifier) is expected


def test_ai_breakers_use_settings_thresholds(monkeypatch):
    monkeypatch.setenv("AI_BREAKER_FAILURE_THRESHOLD", "2")
    monkeypatch.setenv("AI_BREAKER_RECOVERY_TIMEOUT_SECONDS", "7.5")
    container = Container()
    for breaker in (container.adapters.kindwise_breaker(), container.adapters.plantnet_breaker()):
        assert breaker._failure_threshold == 2
        assert breaker._recovery_timeout == 7.5


@pytest.mark.parametrize(("env", "sent_key"), [
    ({"KINDWISE_API_KEY": "documented"}, "documented"),  # o nome do `.env.example` (antes ia vazio)
    ({"PLANT_ID_API_KEY": "legacy"}, "legacy"),           # o nome antigo continua valendo
    ({"KINDWISE_API_KEY": "documented", "PLANT_ID_API_KEY": "legacy"}, "documented"),
])
def test_kindwise_client_gets_the_documented_key(monkeypatch, env, sent_key):
    for name in ("KINDWISE_API_KEY", "PLANT_ID_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    container = Container()
    container.settings.override(providers.Object(Settings(_env_file=None)))

    client = container.adapters.kindwise_client()

    assert client._headers == {"Api-Key": sent_key}
