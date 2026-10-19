"""Identificação: foto → espécie, feedback, cota de tokens e dado de treino, de ponta a ponta."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.conftest import CAMERA_MAKE, Api, jpeg


async def _count(db_session: AsyncSession, table: str) -> int:
    return int((await db_session.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one())


async def test_identify_returns_species_and_strips_metadata(api: Api, db_session: AsyncSession) -> None:
    # Arrange
    headers = await api.signed_up()
    photo = jpeg()
    assert CAMERA_MAKE.encode() in photo

    # Act
    response = await api.identify(headers, photo)

    # Assert
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["scientific_name"] == "Monstera deliciosa"
    assert data["confidence"] == "90.0%"
    assert data["needs_human_review"] is False
    assert data["image_url"] in api.fakes.storage.uploads
    # Provedor, foto do usuário e cópia de treino recebem a imagem sem EXIF
    sent = [*api.fakes.identifier.received, *api.fakes.storage.uploads.values()]
    assert len(sent) == 3
    assert all(CAMERA_MAKE.encode() not in image for image in sent)
    # Imagem de referência do provedor rehospedada; amostra de treino gravada na hora
    assert api.fakes.storage.rehosted == ["https://provider.test/ref.jpg"]
    assert await _count(db_session, "training_identification_samples") == 1
    assert await _count(db_session, "identifications") == 1


async def test_file_that_is_not_an_image_is_rejected(api: Api) -> None:
    # Arrange
    headers = await api.signed_up()

    # Act
    response = await api.identify(headers, b"not an image")

    # Assert
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PLANTE_4001_INVALID_IMAGE"
    assert api.fakes.identifier.received == []


async def test_feedback_is_recorded_only_for_the_owner(api: Api, db_session: AsyncSession) -> None:
    # Arrange
    owner = await api.signed_up()
    stranger = await api.signed_up()
    identification_id = (await api.identify(owner)).json()["data"]["identification_id"]
    path = f"/identify/{identification_id}/feedback"

    # Act
    by_owner = await api.http.post(path, headers=owner, json={"verdict": "wrong", "suggested_name": "Monstera adansonii"})
    again = await api.http.post(path, headers=owner, json={"verdict": "correct"})
    by_stranger = await api.http.post(path, headers=stranger, json={"verdict": "correct"})

    # Assert
    assert by_owner.status_code == again.status_code == 200
    assert by_stranger.status_code == 404
    assert by_stranger.json()["error"]["code"] == "PLANTE_4430_IDENTIFICATION_NOT_FOUND"
    # Cada resposta é um evento (o usuário pode mudar de ideia)
    assert await _count(db_session, "training_feedback") == 2


async def test_free_plan_allows_three_identifications(api: Api) -> None:
    # Arrange
    headers = await api.signed_up()
    for _ in range(3):
        assert (await api.identify(headers)).status_code == 200

    # Act
    fourth = await api.identify(headers)

    # Assert
    assert fourth.status_code == 403
    assert fourth.json()["error"]["code"] == "PLANTE_4220_SUBSCRIPTION_REQUIRED"


async def test_quota_is_full_again_on_the_next_day(api: Api, db_session: AsyncSession) -> None:
    # Arrange: cota gasta ontem (o contador guarda o dia a que se refere)
    headers = await api.signed_up("ontem@plante.org")
    for _ in range(3):
        await api.identify(headers)
    await db_session.execute(text(
        "UPDATE subscriptions SET tokens_day = tokens_day - 1"
        " WHERE user_id = (SELECT id FROM users WHERE email = 'ontem@plante.org')"
    ))
    await db_session.commit()

    # Act
    response = await api.identify(headers)

    # Assert: antes nada zerava o contador e o FREE ficava sem tokens para sempre
    assert response.status_code == 200
    used = await db_session.execute(text(
        "SELECT tokens_used_today FROM subscriptions"
        " WHERE user_id = (SELECT id FROM users WHERE email = 'ontem@plante.org')"
    ))
    assert used.scalar_one() == 1


async def test_identify_is_rate_limited_per_user(api: Api) -> None:
    # Arrange
    headers = await api.signed_up()

    # Act
    response = await api.identify(headers)

    # Assert: rotas de IA têm o limite sensível (15/min), contado por usuário
    assert response.headers["X-RateLimit-Limit"] == "15"
