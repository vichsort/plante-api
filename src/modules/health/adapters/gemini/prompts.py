class HealthPrompts:
    @staticmethod
    def health_diagnosis(scientific_name: str, issues: list[str]) -> str:
        issues_str = ", ".join(issues) if issues else "sintomas não especificados"
        return (
            f"A planta '{scientific_name}' apresenta: {issues_str}. "
            "Responda em português do Brasil com:\n"
            "1. Severidade: healthy | low | moderate | high | critical.\n"
            "2. Score de vitalidade de 0.0 a 1.0.\n"
            "3. Lista de problemas detectados.\n"
            "4. Plano de tratamento passo a passo.\n"
            "5. Estimativa de dias para recuperação."
        )