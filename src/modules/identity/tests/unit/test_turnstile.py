"""The Turnstile check: Cloudflare's answer decides, and Cloudflare down is a 502, never a pass."""
import json
from urllib.parse import parse_qs

import httpx
import pytest

from src.modules.identity.adapters.captcha.turnstile import TurnstileCaptchaVerifier
from src.shared.domain import ExternalServiceError


def _verifier(reply: httpx.Response, sent: list[dict[str, list[str]]] | None = None) -> TurnstileCaptchaVerifier:
    def handle(request: httpx.Request) -> httpx.Response:
        if sent is not None:
            sent.append(parse_qs(request.content.decode()))
        return reply

    return TurnstileCaptchaVerifier("secret", transport=httpx.MockTransport(handle))


def _json(body: object, status: int = 200) -> httpx.Response:
    return httpx.Response(status, content=json.dumps(body).encode())


async def test_a_valid_token_passes_and_the_secret_and_ip_go_along() -> None:
    # Arrange
    sent: list[dict[str, list[str]]] = []
    verifier = _verifier(_json({"success": True}), sent)

    # Act
    passed = await verifier.verify("token", "203.0.113.7")

    # Assert
    assert passed
    assert sent == [{"secret": ["secret"], "response": ["token"], "remoteip": ["203.0.113.7"]}]


async def test_a_rejected_token_does_not_pass() -> None:
    # Act
    passed = await _verifier(_json({"success": False, "error-codes": ["timeout-or-duplicate"]})).verify("token", None)

    # Assert
    assert not passed


@pytest.mark.parametrize("token", [None, "", "x" * 2049])
async def test_a_missing_or_oversized_token_fails_without_asking(token: str | None) -> None:
    # Arrange
    sent: list[dict[str, list[str]]] = []

    # Act
    passed = await _verifier(_json({"success": True}), sent).verify(token, None)

    # Assert
    assert (passed, sent) == (False, [])


@pytest.mark.parametrize("reply", [_json({"error": "down"}, status=503), httpx.Response(200, content=b"<html>")])
async def test_cloudflare_failing_is_an_external_error(reply: httpx.Response) -> None:
    # Act & Assert
    with pytest.raises(ExternalServiceError):
        await _verifier(reply).verify("token", None)
