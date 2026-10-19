"""Perfil: senha, e-mail, localização, plano e conquistas, de ponta a ponta."""

from tests.e2e.conftest import PASSWORD, Api

NEW_PASSWORD = "N3w!Passw0rd"


async def test_password_change_notifies_and_switches_credentials(api: Api) -> None:
    # Arrange
    headers = await api.signed_up("hugo@plante.org")

    # Act
    changed = await api.http.patch(
        "/profile/password", headers=headers, json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    old_login = await api.login("hugo@plante.org", PASSWORD)
    new_login = await api.login("hugo@plante.org", NEW_PASSWORD)

    # Assert
    assert changed.status_code == 200
    assert api.fakes.email.sent[-1].to == "hugo@plante.org"
    assert api.fakes.email.sent[-1].code is None  # aviso de troca, sem código
    assert old_login.status_code == 400
    assert new_login.status_code == 200


async def test_password_change_rejects_weak_or_wrong_current_password(api: Api) -> None:
    # Arrange
    headers = await api.signed_up("iris@plante.org")

    # Act
    weak = await api.http.patch(
        "/profile/password", headers=headers, json={"current_password": PASSWORD, "new_password": "short"},
    )
    wrong_current = await api.http.patch(
        "/profile/password", headers=headers, json={"current_password": "Wr0ng!Pass", "new_password": NEW_PASSWORD},
    )

    # Assert
    assert weak.json()["error"]["code"] == "PLANTE_4100_WEAK_PASSWORD"
    assert wrong_current.json()["error"]["code"] == "PLANTE_4102_WRONG_CREDENTIALS"


async def test_email_change_takes_effect_only_after_the_code(api: Api) -> None:
    # Arrange
    headers = await api.signed_up("joao@plante.org")

    # Act
    changed = await api.http.patch(
        "/profile/email", headers=headers, json={"current_password": PASSWORD, "new_email": "joao.novo@plante.org"},
    )
    old_email_before = await api.login("joao@plante.org")
    new_email_before = await api.login("joao.novo@plante.org")
    confirmed = await api.http.post("/auth/verify-email", json={
        "user_id": api.user_id_of(headers),
        "raw_code": api.fakes.email.last_code_to("joao.novo@plante.org"),
    })
    old_email_after = await api.login("joao@plante.org")
    new_email_after = await api.login("joao.novo@plante.org")

    # Assert: até o código, nada muda (um endereço digitado errado não tranca a conta)
    assert changed.status_code == 200
    assert old_email_before.status_code == 200
    assert new_email_before.status_code == 400
    assert confirmed.status_code == 200
    assert old_email_after.status_code == 400
    assert new_email_after.status_code == 200


async def test_location_update(api: Api) -> None:
    # Arrange
    headers = await api.signed_up()

    # Act
    response = await api.http.patch("/profile/location", headers=headers, json={"country": "BR", "state": "RJ"})

    # Assert
    assert response.status_code == 200


async def test_subscription_upgrade_route_is_gone(api: Api) -> None:
    # Arrange
    headers = await api.signed_up()

    # Act
    response = await api.http.post("/profile/subscription/upgrade", headers=headers, json={"plan_duration_days": 30})

    # Assert: any signed-in user could give themselves PRO for as long as they asked
    assert response.status_code == 404


async def test_achievements_start_empty(api: Api) -> None:
    # Arrange
    headers = await api.signed_up()
    await api.plant_in_garden(headers)

    # Act
    response = await api.http.get("/profile/achievements", headers=headers)

    # Assert
    # Hoje: nada concede conquistas (regra de concessão é da segunda entrega)
    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_deleting_the_account_frees_the_email_and_takes_the_photos(api: Api) -> None:
    # Arrange: an account with a photo, and the account next door
    headers = await api.signed_up("olga@plante.org")
    assert (await api.identify(headers)).status_code == 200
    neighbor = await api.signed_up("pedro@plante.org")
    assert (await api.identify(neighbor)).status_code == 200
    user_id = api.user_id_of(headers)

    # Act
    wrong = await api.http.request("DELETE", "/profile", headers=headers, json={"password": "Wr0ng!Password"})
    deleted = await api.http.request("DELETE", "/profile", headers=headers, json={"password": PASSWORD})
    login_after = await api.login("olga@plante.org")
    registered_again = await api.register("olga@plante.org")

    # Assert
    assert (wrong.status_code, wrong.json()["error"]["code"]) == (400, "PLANTE_4102_WRONG_CREDENTIALS")
    assert deleted.status_code == 200
    assert login_after.status_code == 400
    assert registered_again.status_code == 201  # the same email makes a brand-new account
    photos = [key for key in api.fakes.storage.uploads if key.startswith("identifications/")]
    assert photos and not any(user_id in key for key in photos)  # only the neighbor's photo is left
    assert any(key.startswith("training/") for key in api.fakes.storage.uploads)  # the dataset stays
