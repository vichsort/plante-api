import httpx
import pytest
from structlog.testing import capture_logs

from src.shared.adapters import translate_provider_errors
from src.shared.domain import ExternalServiceError, InvalidImageError

_REQUEST = httpx.Request("POST", "https://provider.test")


def _status_error(status: int) -> httpx.HTTPStatusError:
    return httpx.HTTPStatusError(
        "error", request=_REQUEST, response=httpx.Response(status, request=_REQUEST)
    )


async def _translate(exc: Exception) -> Exception:
    with pytest.raises(Exception) as raised:
        async with translate_provider_errors("Kindwise"):
            raise exc
    return raised.value


@pytest.mark.asyncio
async def test_bad_request_becomes_invalid_image():
    error = await _translate(_status_error(400))
    assert isinstance(error, InvalidImageError)
    assert error.code == "PLANTE_4001_INVALID_IMAGE"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc",
    [
        _status_error(500),
        _status_error(503),
        _status_error(429),
        httpx.ConnectError("down", request=_REQUEST),
        httpx.ReadTimeout("slow", request=_REQUEST),
    ],
)
async def test_infrastructure_failures_are_retryable(exc):
    error = await _translate(exc)
    assert isinstance(error, ExternalServiceError)
    assert error.retryable is True
    assert "Kindwise" in error.message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc", [_status_error(401), _status_error(404), httpx.TooManyRedirects("loop", request=_REQUEST)]
)
async def test_other_http_errors_are_not_retryable(exc):
    error = await _translate(exc)
    assert isinstance(error, ExternalServiceError)
    assert error.retryable is False


@pytest.mark.asyncio
async def test_non_http_errors_pass_through():
    error = await _translate(ValueError("no suggestions"))
    assert isinstance(error, ValueError)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403])
async def test_auth_errors_are_logged_as_misconfiguration(status):
    with capture_logs() as logs:
        error = await _translate(_status_error(status))
    assert isinstance(error, ExternalServiceError)
    assert error.retryable is False
    assert {"event": "provider.misconfigured", "log_level": "error", "service": "Kindwise", "status": status} in logs


@pytest.mark.asyncio
async def test_custom_invalid_image_statuses():
    with pytest.raises(InvalidImageError):
        async with translate_provider_errors("PlantNet", frozenset({404})):
            raise _status_error(404)
