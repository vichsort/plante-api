from src.modules.quota.adapters.persistence.models.quota import (
    QuotaModel,
)
from src.modules.quota.domain.entities.quota import Quota
from src.shared.domain import UserId


class QuotaMapper:
    @staticmethod
    def to_domain(model: QuotaModel) -> Quota:
        return Quota(
            user_id=UserId(model.user_id),
            tier=model.tier,
            expires_at=model.expires_at,
            tokens_used_today=model.tokens_used_today,
            tokens_day=model.tokens_day,
        )

    @staticmethod
    def to_model(entity: Quota) -> QuotaModel:
        return QuotaModel(
            user_id=entity.user_id,
            tier=entity.tier,
            expires_at=entity.expires_at,
            tokens_used_today=entity.tokens_used_today,
            tokens_day=entity.tokens_day,
        )
