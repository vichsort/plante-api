from src.domain.value_objects.json_value import JsonObject


class PlantEError(Exception):
    """
    Erro base do PlantE. Todos os erros de domínio herdam desta classe.
    """
    code: str = "PLANTE_4000_DOMAIN_ERROR"
    status_code: int = 400

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        status_code: int | None = None,
        details: JsonObject | None = None,
    ) -> None:
        # Sem mensagem, a docstring da classe descreve o erro
        self.message = message or (type(self).__doc__ or self.code).strip()
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


DomainException = PlantEError
