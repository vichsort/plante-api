from abc import ABC, abstractmethod


class ICaptchaVerifier(ABC):
    """
    Confirms that the token the browser's captcha widget produced is valid. The check has to happen
    here: a captcha only on the site does not stop a bot that calls the API directly.
    """

    @abstractmethod
    async def verify(self, token: str | None, client_ip: str | None) -> bool:
        """
        False for a missing, invalid, expired or reused token. Raises `ExternalServiceError` when the
        captcha service does not answer.
        """
        ...
