"""
Formato das respostas do Gemini. Os modelos são enviados como `response_schema` (saída
estruturada): o Gemini é obrigado a responder nesse formato, e a resposta é validada com eles.
Sem restrições numéricas (`ge`/`le`) no schema: o Gemini não as suporta; a faixa é conferida
na conversão para o domínio.
"""
from pydantic import BaseModel, ConfigDict

from src.modules.training import HealthSeverity


class _Schema(BaseModel):
    model_config = ConfigDict(frozen=True)


class HealthDiagnosisSchema(_Schema):
    severity: HealthSeverity
    vitality_score: float
    issues_detected: list[str]
    treatment_plan: list[str]
    recovery_estimate_days: int | None
    notes: str | None
