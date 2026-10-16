from dependency_injector import containers, providers

from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.email_sender import IEmailSender
from src.domain.ports.health_analyzer import IHealthAnalyzer
from src.domain.ports.image_sanitizer import IImageSanitizer
from src.domain.ports.image_storage import IImageStorage
from src.domain.ports.otp_repository import IOtpRepository
from src.domain.ports.password_hasher import IPasswordHasher
from src.domain.ports.plant_enricher import IPlantEnricher
from src.domain.ports.plant_identifier import IPlantIdentifier
from src.domain.ports.token_repository import ITokenRepository
from src.domain.ports.token_service import ITokenService
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.use_cases.add_plant_to_garden_use_case import AddPlantToGardenUseCase
from src.domain.use_cases.break_streak_cron_use_case import BreakStreakCronUseCase
from src.domain.use_cases.change_email_use_case import ChangeEmailUseCase
from src.domain.use_cases.change_password_use_case import ChangePasswordUseCase
from src.domain.use_cases.delete_user_plant_use_case import DeleteUserPlantUseCase
from src.domain.use_cases.diagnose_health_use_case import DiagnoseHealthUseCase
from src.domain.use_cases.enrich_plant_species_use_case import EnrichPlantSpeciesUseCase
from src.domain.use_cases.get_health_history_use_case import GetHealthHistoryUseCase
from src.domain.use_cases.get_plant_details_use_case import GetPlantDetailsUseCase
from src.domain.use_cases.get_user_garden_use_case import GetUserGardenUseCase
from src.domain.use_cases.give_health_feedback_use_case import GiveHealthFeedbackUseCase
from src.domain.use_cases.give_identification_feedback_use_case import (
    GiveIdentificationFeedbackUseCase,
)
from src.domain.use_cases.identify_plant_use_case import IdentifyPlantUseCase
from src.domain.use_cases.list_user_achievements_use_case import (
    ListUserAchievementsUseCase,
)
from src.domain.use_cases.login_use_case import LoginUseCase
from src.domain.use_cases.logout_use_case import LogoutUseCase
from src.domain.use_cases.refresh_token_use_case import RefreshTokenUseCase
from src.domain.use_cases.register_user_use_case import RegisterUserUseCase
from src.domain.use_cases.update_location_fallback_use_case import (
    UpdateLocationFallbackUseCase,
)
from src.domain.use_cases.upgrade_subscription_use_case import (
    UpgradeSubscriptionUseCase,
)
from src.domain.use_cases.verify_email_use_case import VerifyEmailUseCase
from src.domain.use_cases.water_plant_use_case import WaterPlantUseCase
from src.domain.value_objects.garden_calendar import GardenCalendar
from src.infrastructure.settings import Settings


class UseCasesContainer(containers.DeclarativeContainer):
    settings: providers.Dependency[Settings] = providers.Dependency()

    unit_of_work: providers.Dependency[IUnitOfWork] = providers.Dependency()
    token_repository: providers.Dependency[ITokenRepository] = providers.Dependency()
    otp_repository: providers.Dependency[IOtpRepository] = providers.Dependency()

    password_hasher: providers.Dependency[IPasswordHasher] = providers.Dependency()
    email_sender: providers.Dependency[IEmailSender] = providers.Dependency()
    domain_publisher: providers.Dependency[IDomainPublisher] = providers.Dependency()
    plant_identifier: providers.Dependency[IPlantIdentifier] = providers.Dependency()
    health_analyzer: providers.Dependency[IHealthAnalyzer] = providers.Dependency()
    plant_enricher: providers.Dependency[IPlantEnricher] = providers.Dependency()

    image_storage: providers.Dependency[IImageStorage] = providers.Dependency()
    image_sanitizer: providers.Dependency[IImageSanitizer] = providers.Dependency()
    token_service: providers.Dependency[ITokenService] = providers.Dependency()

    garden_calendar = providers.Singleton(
        GardenCalendar.from_name,
        settings.provided.garden_timezone,
    )

    login_use_case = providers.Factory(
        LoginUseCase,
        uow=unit_of_work,
        hasher=password_hasher,
        token_repo=token_repository,
        token_service=token_service,
    )

    refresh_token_use_case = providers.Factory(
        RefreshTokenUseCase,
        token_repo=token_repository,
        token_service=token_service,
    )

    logout_use_case = providers.Factory(
        LogoutUseCase,
        token_repo=token_repository,
    )

    change_email_use_case = providers.Factory(
        ChangeEmailUseCase,
        uow=unit_of_work,
        otp_repo=otp_repository,
        hasher=password_hasher,
        email_sender=email_sender,
    )

    change_password_use_case = providers.Factory(
        ChangePasswordUseCase,
        uow=unit_of_work,
        hasher=password_hasher,
        email_sender=email_sender,
    )

    register_user_use_case = providers.Factory(
        RegisterUserUseCase,
        uow=unit_of_work,
        hasher=password_hasher,
        publisher=domain_publisher,
    )

    verify_email_use_case = providers.Factory(
        VerifyEmailUseCase,
        uow=unit_of_work,
        otp_repo=otp_repository,
    )

    upgrade_subscription_use_case = providers.Factory(
        UpgradeSubscriptionUseCase,
        uow=unit_of_work,
        publisher=domain_publisher,
    )

    update_location_fallback_use_case = providers.Factory(
        UpdateLocationFallbackUseCase,
        uow=unit_of_work,
    )

    add_plant_to_garden_use_case = providers.Factory(
        AddPlantToGardenUseCase,
        uow=unit_of_work,
        publisher=domain_publisher,
        calendar=garden_calendar,
    )

    give_identification_feedback_use_case = providers.Factory(
        GiveIdentificationFeedbackUseCase,
        uow=unit_of_work,
    )

    give_health_feedback_use_case = providers.Factory(
        GiveHealthFeedbackUseCase,
        uow=unit_of_work,
    )

    delete_user_plant_use_case = providers.Factory(
        DeleteUserPlantUseCase,
        uow=unit_of_work,
    )

    get_user_garden_use_case = providers.Factory(
        GetUserGardenUseCase,
        uow=unit_of_work,
        calendar=garden_calendar,
    )

    get_plant_details_use_case = providers.Factory(
        GetPlantDetailsUseCase,
        uow=unit_of_work,
        calendar=garden_calendar,
    )

    identify_plant_use_case = providers.Factory(
        IdentifyPlantUseCase,
        uow=unit_of_work,
        sanitizer=image_sanitizer,
        plant_identifier=plant_identifier,
        storage=image_storage,
        publisher=domain_publisher,
    )

    enrich_plant_species_use_case = providers.Factory(
        EnrichPlantSpeciesUseCase,
        uow=unit_of_work,
        enricher=plant_enricher,
    )

    water_plant_use_case = providers.Factory(
        WaterPlantUseCase,
        uow=unit_of_work,
        publisher=domain_publisher,
        calendar=garden_calendar,
    )

    break_streak_cron_use_case = providers.Factory(
        BreakStreakCronUseCase,
        uow=unit_of_work,
        publisher=domain_publisher,
        calendar=garden_calendar,
    )

    list_user_achievements_use_case = providers.Factory(
        ListUserAchievementsUseCase,
        uow=unit_of_work,
    )

    diagnose_health_use_case = providers.Factory(
        DiagnoseHealthUseCase,
        uow=unit_of_work,
        sanitizer=image_sanitizer,
        health_analyzer=health_analyzer,
        plant_enricher=plant_enricher,
        storage=image_storage,
    )

    get_health_history_use_case = providers.Factory(
        GetHealthHistoryUseCase,
        uow=unit_of_work,
    )