"""Origem dos dados de identificação e diagnóstico."""
from typing import Literal

# Provedor de IA que respondeu uma identificação
IdentificationProvider = Literal["kindwise", "plantnet"]

# Origem final de uma identificação: um provedor sozinho ou o consenso entre os dois
# ("consensus_partial" = só o gênero bateu)
IdentificationOrigin = Literal["kindwise", "plantnet", "consensus", "consensus_partial"]

# Origem de um diagnóstico de saúde: só Kindwise ou Kindwise complementado pelo Gemini
HealthSource = Literal["kindwise", "kindwise+gemini"]
