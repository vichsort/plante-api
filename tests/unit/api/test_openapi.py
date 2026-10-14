from fastapi.testclient import TestClient

from src.api.openapi import error_responses
from src.domain.exceptions import (
    PlantLimitExceededError,
    PlantNotFoundError,
    SampleNotFoundError,
)


def test_error_responses_groups_examples_by_status():
    responses = error_responses(PlantNotFoundError, SampleNotFoundError, PlantLimitExceededError)

    not_found = responses[404]["content"]["application/json"]["examples"]
    assert set(not_found) == {PlantNotFoundError.code, SampleNotFoundError.code}
    assert not_found[PlantNotFoundError.code]["value"]["error"]["code"] == PlantNotFoundError.code
    # Exceção com argumento obrigatório usa a docstring como mensagem de exemplo
    forbidden = responses[PlantLimitExceededError.status_code]["content"]["application/json"]["examples"]
    assert forbidden[PlantLimitExceededError.code]["value"]["error"]["message"]


def test_openapi_documents_domain_and_common_errors(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    water = paths["/garden/{user_plant_id}/water"]["post"]["responses"]
    assert set(water) == {"200", "400", "401", "403", "404", "422", "429", "500"}
    examples_429 = water["429"]["content"]["application/json"]["examples"]
    assert "PLANTE_4029_RATE_LIMIT_EXCEEDED" in examples_429

    login = paths["/auth/login"]["post"]["responses"]
    assert "PLANTE_4006_UNAUTHORIZED" in login["401"]["content"]["application/json"]["examples"]
