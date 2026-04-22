class PlantEError(Exception):
    """Erro base do PlantE. Todos os erros de domínio herdam daqui."""
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


# Identificação 
class PlantIdentificationError(PlantEError):
    """A IA não conseguiu identificar a planta com confiança suficiente."""
    def __init__(self, message: str = "Não foi possível identificar a planta na imagem."):
        super().__init__(message=message, code="IDENTIFICATION_FAILED")


class LowConfidenceError(PlantEError):
    """A identificação retornou confiança abaixo do threshold aceitável."""
    def __init__(self, confidence: float):
        super().__init__(
            message=f"Confiança da identificação muito baixa ({confidence:.0%}). Tente uma foto mais nítida.",
            code="LOW_CONFIDENCE",
        )


class InvalidImageError(PlantEError):
    """A imagem enviada é inválida ou não contém uma planta."""
    def __init__(self, message: str = "Imagem inválida ou sem planta detectável."):
        super().__init__(message=message, code="INVALID_IMAGE")


# Plantas e Jardim
class PlantNotFoundError(PlantEError):
    """A planta solicitada não existe ou não pertence ao usuário."""
    def __init__(self, plant_id: int):
        super().__init__(
            message=f"Planta {plant_id} não encontrada.",
            code="PLANT_NOT_FOUND",
        )


class PlantLimitExceededError(PlantEError):
    """Usuário free atingiu o limite de plantas no jardim."""
    def __init__(self, limit: int):
        super().__init__(
            message=f"Limite de {limit} plantas atingido. Assine o Plano Pro para adicionar mais.",
            code="PLANT_LIMIT_EXCEEDED",
        )


# Subscription
class SubscriptionRequiredError(PlantEError):
    """Funcionalidade exclusiva do Plano Pro."""
    def __init__(self, feature: str):
        super().__init__(
            message=f'"{feature}" é exclusivo do Plano Pro (R$ 6,99/mês).',
            code="SUBSCRIPTION_REQUIRED",
        )


# Auth
class UnauthorizedError(PlantEError):
    """Token inválido, expirado ou ausente."""
    def __init__(self, message: str = "Autenticação necessária."):
        super().__init__(message=message, code="UNAUTHORIZED")


class ForbiddenError(PlantEError):
    """Usuário autenticado mas sem permissão para o recurso."""
    def __init__(self, message: str = "Você não tem permissão para acessar este recurso."):
        super().__init__(message=message, code="FORBIDDEN")


# Externos
class ExternalServiceError(PlantEError):
    """Uma API externa (Gemini, Firebase, clima) falhou."""
    def __init__(self, service: str, message: str = ""):
        super().__init__(
            message=f"Serviço externo '{service}' indisponível. {message}".strip(),
            code="EXTERNAL_SERVICE_ERROR",
        )