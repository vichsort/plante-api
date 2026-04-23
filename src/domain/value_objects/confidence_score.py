from dataclasses import dataclass

@dataclass(frozen=True)
class ConfidenceScore:
    value: float

    def __post_init__(self):
        """Garante a invariante: o score nunca pode existir fora de 0.0 a 1.0"""
        if not isinstance(self.value, float):
            raise TypeError("Confidence score must be a float.")
        if not (0.0 <= self.value <= 1.0):
            raise ValueError(f"Confidence score must be between 0.0 and 1.0. Got: {self.value}")

    def is_highly_confident(self) -> bool:
        """Confiança suficiente para aceitação automática (>= 85%)."""
        return self.value >= 0.85

    def requires_human_review(self) -> bool:
        """Confiança média. A IA tem um palpite, mas o usuário deve confirmar (60% a 84%)."""
        return 0.60 <= self.value < 0.85

    def is_rejected(self) -> bool:
        """Abaixo da nota de corte. A foto deve ser descartada ou refeita (< 60%)."""
        return self.value < 0.60

    def as_percentage(self) -> str:
        """Para exibição na UI, se necessário."""
        return f"{self.value * 100:.1f}%"