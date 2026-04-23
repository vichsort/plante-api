class PlantEError(Exception):
    """Erro base do PlantE. Todos os erros de domínio herdam daqui."""
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)

# Identificação 
class PlantIdentificationError(PlantEError):
    """A IA não conseguiu identificar a planta com confiança suficiente."""
    def __init__(self, message: str = "Could not identify any plant in this image."):
        super().__init__(message=message, code="IDENTIFICATION_FAILED")

class LowConfidenceError(PlantEError):
    """A identificação retornou confiança abaixo do threshold aceitável."""
    def __init__(self, confidence: float):
        super().__init__(
            message=f"Confidence too low on this image ({confidence:.0%}). Try one more clear image.",
            code="LOW_CONFIDENCE",
        )

class InvalidImageError(PlantEError):
    """A imagem enviada é inválida ou não contém uma planta."""
    def __init__(self, message: str = "Invalid image or unindentifiable plant."):
        super().__init__(message=message, code="INVALID_IMAGE")

# Plantas e Jardim
class PlantNotFoundError(PlantEError):
    """A planta solicitada não existe ou não pertence ao usuário."""
    def __init__(self, plant_id: int):
        super().__init__(
            message=f"Plant {plant_id} not found.",
            code="PLANT_NOT_FOUND",
        )

class SpeciesNotFoundError(PlantEError):
    """A espécie solicitada não existe."""
    def __init__(self, species_id: int):
        super().__init__(
            message=f"Species {species_id} not found.",
            code="SPECIES_NOT_FOUND",
        )

class SampleNotFoundError(PlantEError):
    """A amostra solicitada não existe."""
    def __init__(self, sample_id: int):
        super().__init__(
            message=f"Sample {sample_id} not found.",
            code="SAMPLE_NOT_FOUND",
        )

class PlantLimitExceededError(PlantEError):
    """Usuário free atingiu o limite de plantas no jardim."""
    def __init__(self, limit: int):
        super().__init__(
            message=f"Limit of {limit} plants reached. Subscribe to the Pro Plan to add more.",
            code="PLANT_LIMIT_EXCEEDED",
        )

class PlantNotReadyForWateringError(PlantEError):
    """Usuário tentou regar a planta antes do tempo ou no mesmo dia."""
    def __init__(self, next_date: str):
        super().__init__(
            message=f"Your plant is well hydrataded! Your next watering date is: {next_date}.",
            code="PLANT_NOT_READY_FOR_WATERING"
        )

# Subscription
class SubscriptionRequiredError(PlantEError):
    """Funcionalidade exclusiva do Plano Pro."""
    def __init__(self, feature: str):
        super().__init__(
            message=f'"{feature}" is exclusive to the Pro Plan (R$ 6,99/month).',
            code="SUBSCRIPTION_REQUIRED",
        )

# Auth
class UnauthorizedError(PlantEError):
    """Token inválido, expirado ou ausente."""
    def __init__(self, message: str = "Authentication required."):
        super().__init__(message=message, code="UNAUTHORIZED")

class EmailAlreadyInUseError(PlantEError):
    """O email já está em uso por outro usuário."""
    def __init__(self, message: str = "Email already in use."):
        super().__init__(message=message, code="EMAIL_ALREADY_IN_USE")

class WeakPasswordError(PlantEError):
    """Senha fraca ou inválida."""
    def __init__(self, message: str = "Weak password."):
        super().__init__(message=message, code="WEAK_PASSWORD")

class ForbiddenError(PlantEError):
    """Usuário autenticado mas sem permissão para o recurso."""
    def __init__(self, message: str = "You do not have permission to access this resource."):
        super().__init__(message=message, code="FORBIDDEN")

class InvalidVerificationCodeError(PlantEError):
    def __init__(self, message: str = "Invalid verification code."):
        super().__init__(message=message, code="INVALID_VERIFICATION_CODE")

# Externos
class ExternalServiceError(PlantEError):
    """Uma API externa (Gemini, Firebase, clima) falhou."""
    def __init__(self, service: str, message: str = ""):
        super().__init__(
            message=f"External service '{service}' unavailable. {message}".strip(),
            code="EXTERNAL_SERVICE_ERROR",
        )