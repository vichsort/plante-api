from src.modules.achievements.domain.ports.achievement_repository import (
    IAchievementRepository,
)
from src.shared.domain import IUnitOfWork


class IAchievementsUnitOfWork(IUnitOfWork):
    """As conquistas dentro da transação (regras em `src.shared.domain.IUnitOfWork`)."""

    achievements: IAchievementRepository
