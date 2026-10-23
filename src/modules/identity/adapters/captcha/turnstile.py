import httpx
import structlog
from pydantic import BaseModel, Field, ValidationError

from src.modules.identity.domain.ports.captcha_verifier import ICaptchaVerifier
from src.shared.domain import ExternalServiceError

log = structlog.stdlib.get_logger()

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
_SERVICE = "Turnstile"
_TIMEOUT_SECONDS = 10.0
# Cloudflare's own limit: a longer token is never valid
_MAX_TOKEN_LENGTH = 2048


class _SiteverifyReply(BaseModel):
    success: bool
    error_codes: list[str] = Field(default_factory=list, alias="error-codes")


class TurnstileCaptchaVerifier(ICaptchaVerifier):
    """Cloudflare Turnstile: the site's widget makes a single-use token (~5 min), checked here."""

    def __init__(
        self, secret_key: str, url: str = SITEVERIFY_URL, transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._secret_key = secret_key
        self._url = url
        self._transport = transport  # tests only

    async def verify(self, token: str | None, client_ip: str | None) -> bool:
        if not token or len(token) > _MAX_TOKEN_LENGTH:
            return False
        form = {"secret": self._secret_key, "response": token}
        if client_ip:
            form["remoteip"] = client_ip
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, transport=self._transport) as client:
                response = await client.post(self._url, data=form)
                response.raise_for_status()
            reply = _SiteverifyReply.model_validate_json(response.content)
        except (httpx.HTTPError, ValidationError) as exc:
            raise ExternalServiceError(message=type(exc).__name__, service=_SERVICE, retryable=True) from exc
        if not reply.success:
            log.info("captcha.rejected", error_codes=reply.error_codes)
        return reply.success


class DisabledCaptchaVerifier(ICaptchaVerifier):
    """No secret key configured (development, tests): every token passes; the container logs a warning."""

    async def verify(self, token: str | None, client_ip: str | None) -> bool:
        return True
