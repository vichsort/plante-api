"""
Todas as tabelas no mesmo metadata, para o Alembic (autogenerate) e os testes de schema. Os
modelos de um módulo são registrados ao importar o container dele (container → UoW →
repositórios → modelos), a única entrada que a composição usa.
"""
import src.modules.achievements.container  # noqa: F401
import src.modules.catalog.container  # noqa: F401
import src.modules.garden.container  # noqa: F401
import src.modules.health.container  # noqa: F401
import src.modules.identification.container  # noqa: F401
import src.modules.identity.container  # noqa: F401
import src.modules.quota.container  # noqa: F401
import src.modules.training.container  # noqa: F401
from src.shared.adapters import Base

metadata = Base.metadata
