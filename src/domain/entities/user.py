from dataclasses import dataclass
from datetime import datetime
from src.domain.value_objects.subscription_tier import SubscriptionTier

@dataclass
class User:
    """
    Agregado Principal do usuário. 
    """
    id: int | None
    email: str
    is_verified: bool
    hashed_password: str
    subscription: SubscriptionTier
    country: str
    state: str
    created_at: datetime
    
    # Atributos operacionais cruciais para as Políticas de Domínio
    tokens_used_today: int = 0
    garden_count: int = 0

    fcm_token: str | None = None
    fcm_token_updated_at: datetime | None = None
    subscription_expires_at: datetime | None = None
    bio: str | None = None
    profile_picture_url: str | None = None

    def __post_init__(self):
        if not self.email or "@" not in self.email:
            raise ValueError("Invalid email address.")
        if not self.country or len(self.country) != 2:
            raise ValueError("Invalid Country. Must be ISO 3166-1 alpha-2 (e.g., BR).")
        if not self.state or len(self.state) < 2:
            raise ValueError("Invalid State.")
        if self.subscription == SubscriptionTier.PRO and self.subscription_expires_at is None:
            raise ValueError("Pro user needs expiration date.")

    @classmethod
    def create_new(cls, email: str, hashed_password: str, country: str, state: str, current_time: datetime) -> 'User':
        """Fábrica de criação: define como o usuário nasce."""
        return cls(
            id=None,
            email=email,
            is_verified=False,
            hashed_password=hashed_password,
            subscription=SubscriptionTier.FREE,
            country=country,
            state=state,
            created_at=current_time,
            tokens_used_today=0,
            garden_count=0
        )

    def verify_email(self) -> None:
        """Desbloqueia a conta após a validação do OTP."""
        self.is_verified = True

    def add_plant_to_garden(self) -> None:
        """Realiza uma identificação e salva no jardim virtual"""
        self.garden_count += 1

    def remove_plant_from_garden(self) -> None:
        """Retira planta do jardim virtual, sem remover a planta do db (treino da IA)"""
        if self.garden_count > 0:
            self.garden_count -= 1

    def consume_identify_token(self) -> None:
        """Consumo de um token para identificação (1 token por planta)"""
        self.tokens_used_today += 1

    def consume_deep_analysis_token(self) -> None:
        """Consumo de um token para análise profunda (2 tokens por planta)"""
        self.tokens_used_today += 2

    def update_location(self, country: str, state: str) -> None:
        """Atualiza o fallback de localização do usuário com validação."""
        if not country or len(country) != 2:
            raise ValueError("Invalid Country. Must be ISO 3166-1 alpha-2 (e.g., BR).")
        if not state or len(state) < 2:
            raise ValueError("Invalid State.")
            
        self.country = country.upper()
        self.state = state.title() # Ex: "santa catarina" vira "Santa Catarina"

    def upgrade_to_pro(self, expires_at: datetime) -> None:
        """Preparando o terreno para o nosso futuro Use Case de Monetização."""
        self.subscription = SubscriptionTier.PRO
        self.subscription_expires_at = expires_at
        self.tokens_used_today = 0

    def is_pro(self, current_time: datetime) -> bool:
        """
        Verifica se a assinatura PRO ainda está ativa.
        Recebe current_time para garantir testes determinísticos (sem utcnow!).
        """
        if self.subscription != SubscriptionTier.PRO:
            return False
        if self.subscription_expires_at is None:
            return False
        return current_time < self.subscription_expires_at

    def get_active_tier(self, current_time: datetime) -> SubscriptionTier:
        """Retorna o plano real considerando uma possível expiração do PRO."""
        return SubscriptionTier.PRO if self.is_pro(current_time) else SubscriptionTier.FREE