"""Respostas reais dos provedores (`tests/fixtures/providers`, catálogo único com a saúde) e transporte HTTP falso."""
import json
from pathlib import Path

import httpx
import pytest

from src.shared.domain import JsonObject

_FIXTURES = Path(__file__).parents[5] / "tests" / "fixtures" / "providers"
_RealAsyncClient = httpx.AsyncClient


def load(name: str) -> JsonObject:
    data: JsonObject = json.loads((_FIXTURES / name).read_text())
    return data


def respond_with(monkeypatch: pytest.MonkeyPatch, response: httpx.Response) -> list[httpx.Request]:
    """Toda chamada HTTP do teste recebe `response`; devolve as requisições enviadas."""
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return response

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, "AsyncClient", lambda: _RealAsyncClient(transport=transport))
    return sent
