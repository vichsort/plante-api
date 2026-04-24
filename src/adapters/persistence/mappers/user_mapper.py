from src.domain.entities.user import User
from src.domain.value_objects.user_location import UserLocation
from src.domain.value_objects.subscription_tier import SubscriptionTier
from src.adapters.persistence.models.user_model import UserModel

class UserMapper:
    @staticmethod
    def to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            hashed_password=model.hashed_password,
            location=UserLocation(
                country=model.location_country,
                state=model.location_state,
            ),
            is_verified=model.is_verified,
            subscription=SubscriptionTier(model.subscription),
            tokens_used_today=model.tokens_used_today,
            garden_count=model.garden_count,
            fcm_token=model.fcm_token,
            fcm_token_updated_at=model.fcm_token_updated_at,
            subscription_expires_at=model.subscription_expires_at,
            bio=model.bio,
            profile_picture_url=model.profile_picture_url,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: User) -> UserModel:
        return UserModel(
            id=entity.id,
            email=entity.email,
            hashed_password=entity.hashed_password,
            location_country=entity.location.country,
            location_state=entity.location.state,
            is_verified=entity.is_verified,
            subscription=entity.subscription.value,
            tokens_used_today=entity.tokens_used_today,
            garden_count=entity.garden_count,
            fcm_token=entity.fcm_token,
            fcm_token_updated_at=entity.fcm_token_updated_at,
            subscription_expires_at=entity.subscription_expires_at,
            bio=entity.bio,
            profile_picture_url=entity.profile_picture_url,
            created_at=entity.created_at,
        )