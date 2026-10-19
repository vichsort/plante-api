from fastapi.testclient import TestClient

from src.modules.catalog import SpeciesNotFoundError
from src.modules.garden import PlantNotFoundError
from src.modules.subscription import PlantLimitExceededError
from src.shared.api import error_responses


def test_error_responses_groups_examples_by_status():
    responses = error_responses(PlantNotFoundError, SpeciesNotFoundError, PlantLimitExceededError)

    not_found = responses[404]["content"]["application/json"]["examples"]
    assert set(not_found) == {PlantNotFoundError.code, SpeciesNotFoundError.code}
    assert not_found[PlantNotFoundError.code]["value"]["error"]["code"] == PlantNotFoundError.code
    # Exceção com argumento obrigatório usa a docstring como mensagem de exemplo
    forbidden = responses[PlantLimitExceededError.status_code]["content"]["application/json"]["examples"]
    assert forbidden[PlantLimitExceededError.code]["value"]["error"]["message"]


def test_openapi_documents_domain_and_common_errors(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    water = paths["/garden/{user_plant_id}/water"]["post"]["responses"]
    # No 403: another user's plant is a 404, like a missing one
    assert set(water) == {"200", "401", "404", "409", "422", "429", "500"}
    examples_429 = water["429"]["content"]["application/json"]["examples"]
    assert "PLANTE_4050_RATE_LIMIT_EXCEEDED" in examples_429

    login = paths["/auth/login"]["post"]["responses"]
    assert "PLANTE_4102_WRONG_CREDENTIALS" in login["400"]["content"]["application/json"]["examples"]
    assert "PLANTE_4120_EMAIL_NOT_VERIFIED" in login["403"]["content"]["application/json"]["examples"]
    assert "401" not in login


def test_openapi_documents_common_errors_on_every_domain_route(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    domain_operations = [
        (path, method, operation)
        for path, item in paths.items()
        if not path.startswith("/health/")
        for method, operation in item.items()
    ]
    assert domain_operations
    for path, method, operation in domain_operations:
        assert "429" in operation["responses"], f"{method.upper()} {path} sem 429"
        assert "500" in operation["responses"], f"{method.upper()} {path} sem 500"


def test_openapi_probes_do_not_document_common_errors(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    for probe in ("/health/liveness", "/health/readiness"):
        responses = paths[probe]["get"]["responses"]
        assert "429" not in responses
        assert "500" not in responses
    assert "/healthz" not in paths


def test_openapi_ai_routes_document_invalid_image(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    for path in ("/identify", "/diagnose"):
        examples = paths[path]["post"]["responses"]["400"]["content"]["application/json"]["examples"]
        assert "PLANTE_4001_INVALID_IMAGE" in examples
