"""Diagnóstico de saúde: diagnóstico, histórico, feedback e custo em tokens, de ponta a ponta."""
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.conftest import Api, jpeg


async def _diagnose(api: Api, headers: dict[str, str], plant_id: str) -> httpx.Response:
    return await api.http.post(
        "/diagnose", headers=headers, data={"user_plant_id": plant_id},
        files={"image": ("leaf.jpg", jpeg("brown"), "image/jpeg")},
    )


async def test_unhealthy_plant_gets_enriched_diagnosis(api: Api, db_session: AsyncSession) -> None:
    # Arrange
    headers = await api.signed_up()
    plant_id = await api.plant_in_garden(headers)

    # Act
    response = await _diagnose(api, headers, plant_id)

    # Assert
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_healthy"] is False
    assert data["severity"] == "high"
    assert data["issues_detected"] == ["leaf_spots"]
    # Saúde abaixo de 0.5 aciona o Gemini: vitalidade e plano de tratamento vêm dele
    assert data["vitality_score"] == 0.4
    assert data["treatment_plan"] == ["Remover folhas manchadas"]
    assert data["recovery_estimate_days"] == 14
    assert data["similar_images_urls"] == ["https://provider.test/disease.jpg"]
    count = await db_session.execute(text("SELECT count(*) FROM training_health_samples"))
    assert count.scalar_one() == 1


async def test_enriched_diagnosis_costs_two_tokens(api: Api) -> None:
    # Arrange: FREE tem 3 tokens; identificar gastou 1
    headers = await api.signed_up()
    plant_id = await api.plant_in_garden(headers)
    await _diagnose(api, headers, plant_id)

    # Act
    response = await api.identify(headers)

    # Assert
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PLANTE_4220_SUBSCRIPTION_REQUIRED"


async def test_diagnosis_without_tokens_never_reaches_the_providers(api: Api) -> None:
    # Arrange: identificar 3 vezes esgota a cota do FREE
    headers = await api.signed_up()
    plant_id = await api.plant_in_garden(headers)
    for _ in range(2):
        await api.identify(headers)
    uploads_before = len(api.fakes.storage.uploads)

    # Act
    response = await _diagnose(api, headers, plant_id)

    # Assert: antes o /diagnose não conferia o saldo e gastava créditos dos provedores
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PLANTE_4220_SUBSCRIPTION_REQUIRED"
    assert len(api.fakes.storage.uploads) == uploads_before


async def test_last_token_diagnoses_without_gemini(api: Api) -> None:
    # Arrange: sobra 1 token; o complemento do Gemini custaria mais 1
    headers = await api.signed_up()
    plant_id = await api.plant_in_garden(headers)
    await api.identify(headers)

    # Act
    response = await _diagnose(api, headers, plant_id)

    # Assert: sai só com o Kindwise (vitalidade = probabilidade de saúde, sem plano de tratamento)
    assert response.status_code == 200
    assert response.json()["data"]["vitality_score"] == 0.3
    assert response.json()["data"]["treatment_plan"] == []


async def test_history_and_feedback(api: Api) -> None:
    # Arrange
    headers = await api.signed_up()
    plant_id = await api.plant_in_garden(headers)
    record_id = (await _diagnose(api, headers, plant_id)).json()["data"]["health_record_id"]

    # Act
    history = await api.http.get(f"/diagnose/history/{plant_id}", headers=headers)
    feedback = await api.http.post(f"/diagnose/{record_id}/feedback", headers=headers, json={"verdict": "correct"})

    # Assert
    assert [item["health_record_id"] for item in history.json()["data"]] == [record_id]
    assert feedback.status_code == 200


async def test_diagnoses_of_another_user_are_not_found(api: Api) -> None:
    # Arrange
    owner = await api.signed_up()
    stranger = await api.signed_up()
    plant_id = await api.plant_in_garden(owner)
    record_id = (await _diagnose(api, owner, plant_id)).json()["data"]["health_record_id"]

    # Act
    diagnose = await _diagnose(api, stranger, plant_id)
    history = await api.http.get(f"/diagnose/history/{plant_id}", headers=stranger)
    feedback = await api.http.post(f"/diagnose/{record_id}/feedback", headers=stranger, json={"verdict": "wrong"})

    # Assert
    assert diagnose.json()["error"]["code"] == "PLANTE_4530_PLANT_NOT_FOUND"
    assert history.json()["error"]["code"] == "PLANTE_4530_PLANT_NOT_FOUND"
    assert feedback.json()["error"]["code"] == "PLANTE_4630_HEALTH_RECORD_NOT_FOUND"
