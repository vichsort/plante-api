from enum import Enum

_CODE_INDEX: dict[str, "AchievementBadge"] = {}

class AchievementBadge(Enum):
    """
    Catálogo central e imutável de conquistas.
    Cada membro do Enum encapsula seu código, título, descrição e ícone.
    """
    PREMIUM_USER = (
        "premium_user", 
        "Apoiador Premium", 
        "Obrigado por apoiar o desenvolvimento do Plante!", 
        "workspace_premium"
    )
    PREMIUM_3_MONTHS = (
        "premium_3_months", 
        "Apoiador Bronze", 
        "Assinante premium por 3 meses consecutivos.", 
        "military_tech"
    )
    PREMIUM_6_MONTHS = (
        "premium_6_months", 
        "Apoiador Prata", 
        "Assinante premium por 6 meses consecutivos.", 
        "military_tech"
    )
    PREMIUM_1_YEAR = (
        "premium_1_year", 
        "Apoiador Ouro", 
        "Assinante premium por 1 ano consecutivo. Você é incrível!", 
        "military_tech"
    )
    
    USER_3_MONTHS = (
        "user_3_months", 
        "Jardineiro Dedicado", 
        "3 meses desde a sua primeira planta.", 
        "calendar_month"
    )
    USER_6_MONTHS = (
        "user_6_months", 
        "Botânico Experiente", 
        "6 meses cuidando do seu jardim virtual.", 
        "calendar_month"
    )
    USER_1_YEAR = (
        "user_1_year", 
        "Aniversário Plante!", 
        "Parabéns pelo seu primeiro ano com a gente!", 
        "cake"
    )

    STREAK_1_MONTH = (
        "streak_1_month", 
        "Mão Verde", 
        "Manteve seus lembretes de rega em dia por 30 dias.", 
        "water_drop"
    )
    STREAK_3_MONTHS = (
        "streak_3_months", 
        "Mestre da Rega", 
        "Manteve seus lembretes de rega em dia por 90 dias.", 
        "water_drop"
    )
    STREAK_6_MONTHS = (
        "streak_6_months", 
        "Guardião do Oásis", 
        "Manteve seus lembretes de rega em dia por 6 meses.", 
        "local_florist"
    )
    STREAK_1_YEAR = (
        "streak_1_year", 
        "Lenda da Hidratação", 
        "Manteve seus lembretes de rega em dia por 1 ano!", 
        "spa"
    )
    
    FIRST_PLANT = (
        "first_plant", 
        "Primeira Folha", 
        "Identificou sua primeira planta.", 
        "psychology_alt"
    )
    TEN_PLANTS = (
        "ten_plants", 
        "Colecionador", 
        "Identificou 10 plantas diferentes.", 
        "yard"
    )
    FIRST_DEEP_ANALYSIS = (
        "first_deep_analysis", 
        "Cientista de Plantas", 
        "Realizou sua primeira análise profunda com IA.", 
        "auto_awesome"
    )

    def __init__(self, code: str, title: str, description: str, icon_name: str):
        self.code = code
        self.title = title
        self.description = description
        self.icon_name = icon_name

    @classmethod
    def from_code(cls, code: str) -> 'AchievementBadge | None':
        if not _CODE_INDEX:
            for badge in cls:
                _CODE_INDEX[badge.code] = badge
        return _CODE_INDEX.get(code)