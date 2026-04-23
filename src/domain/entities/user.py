from dataclasses import dataclass
from datetime import datetime
from src.domain.value_objects.subscription_tier import SubscriptionTier

@dataclass(frozen=True)
class User:
    id: int
    email: str
    hashed_password: str
    subscription: SubscriptionTier
    country: str
    state: str
    created_at: datetime
    fcm_token: str | None = None
    fcm_token_updated_at: datetime | None = None
    subscription_expires_at: datetime | None = None
    bio: str | None = None
    profile_picture_url: str | None = None

    def __post_init__(self):
        if not self.email or "@" not in self.email:
            raise ValueError("Invalid email adress.")
        if not self.country or len(self.country) != 2:
            raise ValueError("Invalid Country.")
        if not self.state or len(self.state) < 2:
            raise ValueError("Invalid State.")
        if self.subscription == SubscriptionTier.PRO and self.subscription_expires_at is None:
            raise ValueError("Pro user needs expiration date.")

    @property
    def is_pro(self) -> bool:
        """Verifica se a assinatura PRO ainda está ativa."""
        if self.subscription != SubscriptionTier.PRO:
            return False
        if self.subscription_expires_at is None:
            return False
        return datetime.utcnow() < self.subscription_expires_at

    @property
    def active_tier(self) -> SubscriptionTier:
        """Retorna o tier real considerando expiração."""
        return SubscriptionTier.PRO if self.is_pro else SubscriptionTier.FREE