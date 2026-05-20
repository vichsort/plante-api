from dependency_injector import containers, providers

from src.domain.use_cases.change_email_use_case import ChangeEmailUseCase
from src.domain.use_cases.change_password_use_case import ChangePasswordUseCase
from src.domain.use_cases.register_user_use_case import RegisterUserUseCase
from src.domain.use_cases.verify_email_use_case import VerifyEmailUseCase
from src.domain.use_cases.upgrade_subscription_use_case import UpgradeSubscriptionUseCase
from src.domain.use_cases.update_location_fallback_use_case import UpdateLocationFallbackUseCase
from src.domain.use_cases.add_plant_to_garden_use_case import AddPlantToGardenUseCase
from src.domain.use_cases.delete_user_plant_use_case import DeleteUserPlantUseCase
from src.domain.use_cases.get_user_garden_use_case import GetUserGardenUseCase
from src.domain.use_cases.get_plant_details_use_case import GetPlantDetailsUseCase
from src.domain.use_cases.identify_plant_use_case import IdentifyPlantUseCase
from src.domain.use_cases.enrich_plant_species_use_case import EnrichPlantSpeciesUseCase
from src.domain.use_cases.water_plant_use_case import WaterPlantUseCase
from src.domain.use_cases.break_streak_cron_use_case import BreakStreakCronUseCase
from src.domain.use_cases.list_user_achievements_use_case import ListUserAchievementsUseCase
from src.domain.use_cases.login_use_case import LoginUseCase
from src.domain.use_cases.refresh_token_use_case import RefreshTokenUseCase
from src.domain.use_cases.logout_use_case import LogoutUseCase
from src.domain.use_cases.diagnose_health_use_case import DiagnoseHealthUseCase
from src.domain.use_cases.get_health_history_use_case import GetHealthHistoryUseCase
from src.domain.use_cases.confirm_plant_identification_use_case import ConfirmPlantIdentificationUseCase
from src.domain.use_cases.confirm_health_diagnosis_use_case import ConfirmHealthDiagnosisUseCase

class UseCasesContainer(containers.DeclarativeContainer):
    settings = providers.Dependency()

    user_repository = providers.Dependency()
    token_repository = providers.Dependency()
    otp_repository = providers.Dependency()
    user_plant_repository = providers.Dependency()
    plant_species_repository = providers.Dependency()
    identification_sample_repository = providers.Dependency()
    health_record_repository = providers.Dependency()
    health_identification_sample_repository = providers.Dependency()
    health_raw_response_repository = providers.Dependency()
    plant_nutritional_repository = providers.Dependency()
    achievement_repository = providers.Dependency()
    plant_reference_image_repository = providers.Dependency()

    password_hasher = providers.Dependency()
    email_sender = providers.Dependency()
    domain_publisher = providers.Dependency()
    plant_identifier = providers.Dependency()
    health_analyzer = providers.Dependency()
    plant_enricher = providers.Dependency()

    image_storage = providers.Dependency()

    login_use_case = providers.Factory(
        LoginUseCase,
        user_repo=user_repository,
        hasher=password_hasher,
        token_repo=token_repository,
        secret_key=settings.provided.secret_key,
        algorithm=settings.provided.jwt_algorithm,
    )

    refresh_token_use_case = providers.Factory(
        RefreshTokenUseCase,
        token_repo=token_repository,
        secret_key=settings.provided.secret_key,
        algorithm=settings.provided.jwt_algorithm,
    )

    logout_use_case = providers.Factory(
        LogoutUseCase,
        token_repo=token_repository,
    )

    change_email_use_case = providers.Factory(
        ChangeEmailUseCase,
        user_repo=user_repository,
        otp_repo=otp_repository,
        hasher=password_hasher,
        email_sender=email_sender,
    )

    change_password_use_case = providers.Factory(
        ChangePasswordUseCase,
        user_repo=user_repository,
        hasher=password_hasher,
    )

    register_user_use_case = providers.Factory(
        RegisterUserUseCase,
        user_repo=user_repository,
        hasher=password_hasher,
        email_sender=email_sender,
        otp_repo=otp_repository,
        publisher=domain_publisher,
    )

    verify_email_use_case = providers.Factory(
        VerifyEmailUseCase,
        user_repo=user_repository,
        otp_repo=otp_repository,
    )

    upgrade_subscription_use_case = providers.Factory(
        UpgradeSubscriptionUseCase,
        user_repo=user_repository,
        publisher=domain_publisher
    )

    update_location_fallback_use_case = providers.Factory(
        UpdateLocationFallbackUseCase,
        user_repo=user_repository,
    )

    add_plant_to_garden_use_case = providers.Factory(
        AddPlantToGardenUseCase,
        user_repo=user_repository,
        user_plant_repo=user_plant_repository,
        species_repo=plant_species_repository,
        sample_repo=identification_sample_repository,
    )

    confirm_plant_identification = providers.Factory(
        ConfirmPlantIdentificationUseCase,
        user_repo=user_repository,
        sample_repo=identification_sample_repository,
        publisher=domain_publisher,
    )

    confirm_health_diagnosis = providers.Factory(
        ConfirmHealthDiagnosisUseCase,
        user_repo=user_repository,
        health_record_repo=health_record_repository,
        health_sample_repo=health_identification_sample_repository,
        health_raw_repo=health_raw_response_repository,
        storage=image_storage,
        publisher=domain_publisher,
    )

    delete_user_plant_use_case = providers.Factory(
        DeleteUserPlantUseCase,
        user_repo=user_repository,
        user_plant_repo=user_plant_repository,
    )

    get_user_garden_use_case = providers.Factory(
        GetUserGardenUseCase,
        user_plant_repo=user_plant_repository,
    )

    get_plant_details_use_case = providers.Factory(
        GetPlantDetailsUseCase,
        user_plant_repo=user_plant_repository,
        species_repo=plant_species_repository,
        nutritional_repo=plant_nutritional_repository,
        health_repo=health_record_repository,
    )

    identify_plant_use_case = providers.Factory(
        IdentifyPlantUseCase,
        user_repo=user_repository,
        species_repo=plant_species_repository,
        sample_repo=identification_sample_repository,
        plant_identifier=plant_identifier,
        user_plant_repo=user_plant_repository,
        reference_image_repo=plant_reference_image_repository,
        storage=image_storage,
        publisher=domain_publisher,
    )

    enrich_plant_species_use_case = providers.Factory(
        EnrichPlantSpeciesUseCase,
        species_repo=plant_species_repository,
        nutritional_repo=plant_nutritional_repository,
        plant_enricher=plant_enricher,
    )

    water_plant_use_case = providers.Factory(
        WaterPlantUseCase,
        user_plant_repo=user_plant_repository,
    )

    break_streak_cron_use_case = providers.Factory(
        BreakStreakCronUseCase,
        user_plant_repo=user_plant_repository,
    )

    list_user_achievements_use_case = providers.Factory(
        ListUserAchievementsUseCase,
        achievement_repo=achievement_repository,
    )

    diagnose_health_use_case = providers.Factory(
        DiagnoseHealthUseCase,
        user_repo=user_repository,
        user_plant_repo=user_plant_repository,
        health_repo=health_record_repository,
        health_analyzer=health_analyzer,
        plant_enricher=plant_enricher,
        storage=image_storage,
        health_raw_repo=health_raw_response_repository,
    )

    get_health_history_use_case = providers.Factory(
        GetHealthHistoryUseCase,
        user_plant_repo=user_plant_repository,
        health_repo=health_record_repository,
    )