"""
identity: quem é o usuário e como ele entra (README.md). A API pública é só domínio; a composição
monta o módulo por `src.modules.identity.container`, `.api` e `.workers`.
"""
from src.modules.identity.domain.events import UserRegisteredEvent
from src.modules.identity.domain.exceptions import TermsNotAcceptedError
from src.modules.identity.domain.services.user_directory import IUserDirectory
from src.modules.identity.domain.value_objects.user_location import UserLocation

__all__ = ["IUserDirectory", "TermsNotAcceptedError", "UserLocation", "UserRegisteredEvent"]
