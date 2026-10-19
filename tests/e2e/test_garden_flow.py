"""Jardim: adicionar, listar, detalhar, regar e remover, de ponta a ponta."""
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.conftest import Api
from tests.factories import CALENDAR


async def test_add_plant_from_identification(api: Api) -> None:
    # Arrange
    headers = await api.signed_up()
    identified = (await api.identify(headers)).json()["data"]
    body = {"identification_id": identified["identification_id"], "nickname": "Clotilde"}

    # Act
    added = await api.http.post("/garden", headers=headers, json=body)
    again = await api.http.post("/garden", headers=headers, json=body)
    garden = await api.http.get("/garden", headers=headers)

    # Assert
    assert added.status_code == again.status_code == 201
    plant = added.json()["data"]
    assert again.json()["data"]["id"] == plant["id"]  # idempotente
    assert plant["display_name"] == "Clotilde"
    assert plant["primary_image_url"] == identified["image_url"]  # a foto da identificação
    assert (plant["streak_count"], plant["next_due_on"], plant["needs_watering"]) == (0, None, False)
    assert [item["id"] for item in garden.json()["data"]] == [plant["id"]]


async def test_plant_details_include_species(api: Api) -> None:
    # Arrange
    headers = await api.signed_up()
    plant_id = await api.plant_in_garden(headers)

    # Act
    response = await api.http.get(f"/plants/{plant_id}", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["identification_source"] == "consensus"
    assert data["care_schedule"] == {"care_type": "water", "interval_days": 7, "is_active": True, "next_due_on": None}
    assert data["species_info"]["family"] == "Araceae"
    assert data["species_info"]["common_names"] == ["costela-de-adão"]


async def test_watering_sets_next_due_day_and_blocks_a_second_watering(api: Api) -> None:
    # Arrange
    headers = await api.signed_up()
    plant_id = await api.plant_in_garden(headers)
    today = CALENDAR.date_of(datetime.now(UTC))

    # Act
    watered = await api.http.post(f"/garden/{plant_id}/water", headers=headers)
    again = await api.http.post(f"/garden/{plant_id}/water", headers=headers)

    # Assert
    assert watered.status_code == 200
    assert watered.json()["data"]["current_streak"] == 1
    assert watered.json()["data"]["next_due_on"] == (today + timedelta(days=7)).isoformat()
    assert again.status_code == 400
    assert again.json()["error"]["code"] == "PLANTE_4016_NOT_READY_FOR_WATERING"
    window_opens = (today + timedelta(days=6)).strftime("%d/%m/%Y")
    assert window_opens in again.json()["error"]["message"]


async def test_removing_a_plant_keeps_the_identification(api: Api) -> None:
    # Arrange
    headers = await api.signed_up()
    identification_id = (await api.identify(headers)).json()["data"]["identification_id"]
    plant_id = (await api.http.post("/garden", headers=headers, json={"identification_id": identification_id})).json()["data"]["id"]

    # Act
    removed = await api.http.delete(f"/garden/{plant_id}", headers=headers)
    removed_again = await api.http.delete(f"/garden/{plant_id}", headers=headers)
    garden = await api.http.get("/garden", headers=headers)
    readded = await api.http.post("/garden", headers=headers, json={"identification_id": identification_id})

    # Assert
    assert removed.status_code == 200
    assert removed_again.status_code == 404
    assert garden.json()["data"] == []
    # A identificação continua: dá para adicionar de novo (vira outra planta)
    assert readded.status_code == 201
    assert readded.json()["data"]["id"] != plant_id


async def test_free_plan_garden_limit(api: Api, db_session: AsyncSession) -> None:
    # Arrange: 3 plantas; os tokens são devolvidos direto no banco para a 4ª identificação
    headers = await api.signed_up("limite@plante.org")
    for _ in range(3):
        await api.plant_in_garden(headers)
    await db_session.execute(text(
        "UPDATE subscriptions SET tokens_used_today = 0"
        " WHERE user_id = (SELECT id FROM users WHERE email = 'limite@plante.org')"
    ))
    await db_session.commit()
    identification_id = (await api.identify(headers)).json()["data"]["identification_id"]

    # Act
    response = await api.http.post("/garden", headers=headers, json={"identification_id": identification_id})

    # Assert
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PLANTE_4005_FREE_TIER_PLANT_LIMIT"


async def test_plants_of_another_user_are_not_found(api: Api) -> None:
    # Arrange
    owner = await api.signed_up()
    stranger = await api.signed_up()
    plant_id = await api.plant_in_garden(owner)

    # Act
    responses = [
        await api.http.get(f"/plants/{plant_id}", headers=stranger),
        await api.http.post(f"/garden/{plant_id}/water", headers=stranger),
        await api.http.delete(f"/garden/{plant_id}", headers=stranger),
    ]

    # Assert
    assert [r.status_code for r in responses] == [404, 404, 404]
    assert {r.json()["error"]["code"] for r in responses} == {"PLANTE_4001_PLANT_NOT_FOUND"}
    assert len((await api.http.get("/garden", headers=owner)).json()["data"]) == 1
