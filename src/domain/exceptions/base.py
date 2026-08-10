from typing import Any


class PlantEError(Exception):
    """
    Erro base do PlantE. Todos os erros de domínio herdam desta classe.
    """
    code: str = "PLANTE_4000_DOMAIN_ERROR"
    status_code: int = 400

    def __init__(
        self,
        message: str,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


DomainException = PlantEError
