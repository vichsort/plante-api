"""
Testes de caracterização ponta a ponta: requisição HTTP → app real (middlewares, rotas, use cases,
Unit of Work) → Postgres e Redis reais. Só as bordas externas são dublês (`doubles.py`).

Servem de rede de segurança para a refatoração do item 8: descrevem o comportamento atual, com
as esquisitices marcadas (`# Hoje:`), e precisam continuar passando com o código movido.
"""
import io
from collections.abc import AsyncIterator, Iterator
from contextlib import ExitStack
from dataclasses import dataclass, field
from uuid import uuid4

import httpx
import jwt
import pytest
import pytest_asyncio
from dependency_injector import providers
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bootstrap.container import Container
from src.bootstrap.wiring import wire
from src.main import app
from src.modules.identity.workers import (
    SEND_VERIFICATION_EMAIL_TASK,
    route_event,
    send_verification_email_task,
)
from src.shared.adapters import CeleryPublisher, RedisClient
from tests.e2e.doubles import (
    FakeEmailSender,
    FakeHealthAnalyzer,
    FakeHealthEnricher,
    FakeIdentifier,
    FakeStorage,
    RecordingQueue,
)

PASSWORD = "Str0ng!Passw0rd"


CAMERA_MAKE = "PhoneCo"


def jpeg(color: str = "green") -> bytes:
    """
    Foto mínima válida (o sanitizador real do Pillow precisa decodificar a imagem), com EXIF
    (fabricante da câmera) para conferir que nada além do app recebe os metadados.
    """
    image = Image.new("RGB", (32, 32), color)
    exif = image.getexif()
    exif[0x010F] = CAMERA_MAKE  # Make
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    return buffer.getvalue()


@dataclass
class Doubles:
    identifier: FakeIdentifier = field(default_factory=FakeIdentifier)
    health_analyzer: FakeHealthAnalyzer = field(default_factory=FakeHealthAnalyzer)
    health_enricher: FakeHealthEnricher = field(default_factory=FakeHealthEnricher)
    storage: FakeStorage = field(default_factory=FakeStorage)
    email: FakeEmailSender = field(default_factory=FakeEmailSender)
    queue: RecordingQueue = field(default_factory=RecordingQueue)


@pytest.fixture
def doubles(
    session_factory: async_sessionmaker[AsyncSession],
    redis_client: RedisClient,
) -> Iterator[Doubles]:
    """Liga o container do app ao Postgres/Redis dos testes e às bordas falsas; desfaz no fim."""
    fakes = Doubles()
    container: Container = app.state.container
    # A ligação das rotas é global: outro teste pode ter ligado outro container
    wire(container)
    overrides = {
        # Toda transação (de todos os módulos) na conexão do teste
        container.infra.session_factory: providers.Object(session_factory),
        container.adapters.redis: providers.Object(redis_client),
        container.identification.plant_identifier: providers.Object(fakes.identifier),
        container.health.analyzer: providers.Object(fakes.health_analyzer),
        container.health.enricher: providers.Object(fakes.health_enricher),
        container.adapters.image_storage: providers.Object(fakes.storage),
        container.identity.email_sender: providers.Object(fakes.email),
        container.adapters.domain_publisher: providers.Object(CeleryPublisher(fakes.queue, routes=[route_event])),
    }
    # Singletons (repositórios de OTP e de refresh token) guardam o Redis do teste anterior,
    # preso a um event loop já fechado
    container.reset_singletons()
    with ExitStack() as stack:
        for provider, replacement in overrides.items():
            stack.enter_context(provider.override(replacement))
        yield fakes
    container.reset_singletons()


class Api:
    """Cliente HTTP do app com atalhos para os passos que quase todo fluxo repete."""

    def __init__(self, http: httpx.AsyncClient, fakes: Doubles) -> None:
        self.http = http
        self.fakes = fakes

    async def run_queued_tasks(self) -> None:
        """Faz o papel do worker: executa as tasks que o publisher mandou para a fila."""
        # A task usa o container do app (ligado pelo `wire` da fixture `doubles`)
        while self.fakes.queue.tasks:
            task = self.fakes.queue.tasks.pop(0)
            assert task.name == SEND_VERIFICATION_EMAIL_TASK, f"unexpected task {task.name}"
            await send_verification_email_task(**task.kwargs)

    @staticmethod
    def user_id_of(headers: dict[str, str]) -> str:
        """O `sub` do access token (o app recebe o ID no cadastro; aqui é mais curto ler do token)."""
        token = headers["Authorization"].removeprefix("Bearer ")
        return str(jwt.decode(token, options={"verify_signature": False})["sub"])

    async def register(self, email: str, password: str = PASSWORD) -> httpx.Response:
        return await self.http.post(
            "/auth/register", json={"email": email, "password": password, "country": "BR", "state": "SP"},
        )

    async def login(self, email: str, password: str = PASSWORD) -> httpx.Response:
        return await self.http.post("/auth/login", json={"email": email, "password": password})

    async def signed_up(self, email: str | None = None) -> dict[str, str]:
        """Cadastro → e-mail com o código (worker) → verificação → login. Devolve o cabeçalho de auth."""
        email = email or f"user-{uuid4().hex[:8]}@plante.org"
        user_id = (await self.register(email)).json()["data"]["user_id"]
        await self.run_queued_tasks()
        verified = await self.http.post(
            "/auth/verify-email", json={"user_id": user_id, "raw_code": self.fakes.email.last_code_to(email)},
        )
        assert verified.status_code == 200, verified.text
        tokens = (await self.login(email)).json()["data"]
        return {"Authorization": f"Bearer {tokens['access_token']}"}

    async def identify(self, headers: dict[str, str], image: bytes | None = None) -> httpx.Response:
        return await self.http.post(
            "/identify", headers=headers, files={"image": ("plant.jpg", image or jpeg(), "image/jpeg")},
        )

    async def plant_in_garden(self, headers: dict[str, str]) -> str:
        """Identifica e adiciona ao jardim. Devolve o ID da planta."""
        identification_id = (await self.identify(headers)).json()["data"]["identification_id"]
        added = await self.http.post("/garden", headers=headers, json={"identification_id": identification_id})
        assert added.status_code == 201, added.text
        return str(added.json()["data"]["id"])


@pytest_asyncio.fixture
async def api(doubles: Doubles) -> AsyncIterator[Api]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://plante.test") as http:
        yield Api(http, doubles)
