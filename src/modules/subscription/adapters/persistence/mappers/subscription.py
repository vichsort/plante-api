from src.modules.subscription.adapters.persistence.models.subscription import (
    SubscriptionModel,
)
from src.modules.subscription.domain.entities.subscription import Subscription
from src.shared.domain import UserId


class SubscriptionMapper:
    @staticmethod
    def to_domain(model: SubscriptionModel) -> Subscription:
        return Subscription(
            user_id=UserId(model.user_id),
            tier=model.tier,
            expires_at=model.expires_at,
            tokens_used_today=model.tokens_used_today,
            tokens_day=model.tokens_day,
        )

    @staticmethod
    def to_model(entity: Subscription) -> SubscriptionModel:
        return SubscriptionModel(
            user_id=entity.user_id,
            tier=entity.tier,
            expires_at=entity.expires_at,
            tokens_used_today=entity.tokens_used_today,
            tokens_day=entity.tokens_day,
        )
