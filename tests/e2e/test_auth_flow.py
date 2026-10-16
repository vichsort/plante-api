"""Cadastro, verificação de e-mail, login, refresh e logout, de ponta a ponta."""
from types import SimpleNamespace

import pytest

from src.api.middleware import rate_limit
from tests.e2e.conftest import PASSWORD, Api


async def test_signup_verification_and_login(api: Api) -> None:
    # Arrange
    email = "ana@plante.org"

    # Act
    registered = await api.register(email)
    before_verification = await api.login(email)
    await api.run_queued_tasks()  # o worker gera o código e manda o e-mail
    verified = await api.http.post("/auth/verify-email", json={
        "user_id": registered.json()["data"]["user_id"],
        "raw_code": api.fakes.email.last_code_to(email),
    })
    logged_in = await api.login(email)

    # Assert
    assert registered.status_code == 201
    assert registered.json()["data"]["status"] == "pending_verification"
    assert before_verification.status_code == 401
    assert before_verification.json()["error"]["message"] == "Email not verified."
    assert verified.status_code == 200
    assert logged_in.status_code == 200
    assert set(logged_in.json()["data"]) == {"access_token", "refresh_token", "token_type"}


async def test_email_is_unique_regardless_of_case(api: Api) -> None:
    # Arrange
    await api.register("bia@plante.org")

    # Act
    duplicate = await api.register("  BIA@Plante.org ")

    # Assert
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "PLANTE_4004_EMAIL_ALREADY_IN_USE"


async def test_wrong_password_and_unknown_email_look_the_same(api: Api) -> None:
    # Arrange
    await api.signed_up("caio@plante.org")

    # Act
    wrong_password = await api.login("caio@plante.org", "Wr0ng!Password")
    unknown_email = await api.login("ninguem@plante.org")

    # Assert
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["error"] == unknown_email.json()["error"]


async def test_wrong_verification_code_is_rejected(api: Api) -> None:
    # Arrange
    user_id = (await api.register("davi@plante.org")).json()["data"]["user_id"]
    await api.run_queued_tasks()

    # Act
    response = await api.http.post("/auth/verify-email", json={"user_id": user_id, "raw_code": "PLA0000000"})

    # Assert
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PLANTE_4003_INVALID_VERIFICATION_CODE"


async def test_signup_rejects_a_weak_password(api: Api) -> None:
    # Act
    response = await api.register("eva@plante.org", password="123")

    # Assert
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PLANTE_4008_WEAK_PASSWORD"


async def test_refresh_rotates_and_reuse_revokes_the_session(api: Api) -> None:
    # Arrange
    await api.signed_up("fabi@plante.org")
    tokens = (await api.login("fabi@plante.org")).json()["data"]

    # Act
    rotated = await api.http.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    reused = await api.http.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    newest_after_reuse = await api.http.post(
        "/auth/refresh", json={"refresh_token": rotated.json()["data"]["refresh_token"]},
    )

    # Assert
    assert rotated.status_code == 200
    assert rotated.json()["data"]["refresh_token"] != tokens["refresh_token"]
    assert reused.status_code == 401
    assert newest_after_reuse.status_code == 401  # reuso = sinal de roubo: a sessão inteira cai


async def test_logout_revokes_the_refresh_token_only(api: Api) -> None:
    # Arrange
    await api.signed_up("gabi@plante.org")
    tokens = (await api.login("gabi@plante.org")).json()["data"]
    access = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Act
    logout = await api.http.post("/auth/logout", headers=access)
    refresh_after_logout = await api.http.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    access_after_logout = await api.http.get("/garden", headers=access)

    # Assert
    assert logout.status_code == 200
    assert refresh_after_logout.status_code == 401
    # Decisão: o access token (JWT sem estado, 15 minutos) vale até expirar
    assert access_after_logout.status_code == 200


async def test_protected_routes_need_a_token(api: Api) -> None:
    # Act
    response = await api.http.get("/garden")

    # Assert
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "PLANTE_4006_UNAUTHORIZED"


async def test_login_is_rate_limited_per_ip(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange: rotas de auth contam por IP, 15 por minuto (somadas). Relógio do middleware parado
    # no meio de um minuto: a janela é fixa e virar o minuto no meio do teste zeraria a contagem
    monkeypatch.setattr(rate_limit, "time", SimpleNamespace(time=lambda: 1_800_000_030.0))
    for _ in range(15):
        await api.login("gil@plante.org", PASSWORD)

    # Act
    blocked = await api.login("gil@plante.org", PASSWORD)

    # Assert
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "PLANTE_4029_RATE_LIMIT_EXCEEDED"
    assert blocked.headers["X-RateLimit-Limit"] == "15"
