class GeminiPromptBuilder:
    @staticmethod
    def enrich_species(scientific_name: str) -> str:
        return (
            f"A planta de nome científico '{scientific_name}' está saudável. "
            "Responda em português do Brasil com:\n"
            "1. Lista de nomes populares.\n"
            "2. Se é comestível (true/false).\n"
            "3. Frequência de rega por semana (número inteiro).\n"
            "4. Nível de luz: low | indirect | direct | full_sun.\n"
            "5. Tipo de solo: sandy | clay | loamy | well_draining.\n"
            "6. Melhor estação para plantio.\n"
            "7. País de origem.\n"
            "8. Habitat natural."
        )

    @staticmethod
    def nutritional_analysis(scientific_name: str) -> str:
        return (
            f"A planta de nome científico '{scientific_name}' está saudável. "
            "Responda em português do Brasil com:\n"
            "1. É possível fazer chá? Se sim, como preparar e quais os benefícios.\n"
            "2. Uma receita (nome e lista de ingredientes) usando a planta.\n"
            "3. Usos medicinais, se houver.\n"
            "4. Se usada como tempero, em quais pratos combina."
        )

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