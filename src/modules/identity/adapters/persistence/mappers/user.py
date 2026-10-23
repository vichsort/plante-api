from src.modules.identity.adapters.persistence.models.user import UserModel
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.user_location import UserLocation
from src.shared.domain import UserId


class UserMapper:
    @staticmethod
    def to_domain(model: UserModel) -> User:
        return User(
            id=UserId(model.id),
            email=model.email,
            pending_email=model.pending_email,
            hashed_password=model.hashed_password,
            location=UserLocation(
                country=model.location_country,
                state=model.location_state,
            ),
            is_verified=model.is_verified,
            bio=model.bio,
            profile_picture_url=model.profile_picture_url,
            terms_version=model.terms_version,
            terms_accepted_at=model.terms_accepted_at,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: User) -> UserModel:
        return UserModel(
            id=entity.id,
            email=entity.email,
            pending_email=entity.pending_email,
            hashed_password=entity.hashed_password,
            location_country=entity.location.country,
            location_state=entity.location.state,
            is_verified=entity.is_verified,
            bio=entity.bio,
            profile_picture_url=entity.profile_picture_url,
            terms_version=entity.terms_version,
            terms_accepted_at=entity.terms_accepted_at,
            created_at=entity.created_at,
        )