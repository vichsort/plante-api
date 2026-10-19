"""
Rega e sequência: janela de ±1 dia em volta do vencimento, em dias do calendário local.

Vencimento no dia 10: até o dia 8 é cedo demais; 9, 10 e 11 contam como no prazo; do dia 12 em
diante a rega é aceita, mas atrasada (a sequência recomeça em 1).
"""
from dataclasses import replace
from datetime import date, datetime, timedelta

import pytest

from src.modules.garden.domain.entities.user_plant import UserPlant
from src.modules.garden.domain.exceptions import PlantNotReadyForWateringError
from src.modules.garden.domain.value_objects.care_interval import CareInterval
from src.modules.garden.domain.value_objects.streak import Streak
from src.modules.garden.tests.fakes import CALENDAR, make_care_schedule, make_user_plant

DUE = date(2026, 10, 10)


def _at(day: date, hour: int = 12) -> datetime:
    return datetime(day.year, day.month, day.day, hour, 0, tzinfo=CALENDAR.timezone)


def _plant_with_streak(count: int, due: date | None = DUE) -> UserPlant:
    plant = make_user_plant(care_schedule=make_care_schedule(next_due_on=due))
    if due is not None:
        plant.last_watered_at = _at(due - timedelta(days=7))
    plant.watering_streak = Streak(current_count=count, last_action_time=plant.last_watered_at)
    return plant


@pytest.mark.parametrize("day, expected_streak", [
    (date(2026, 10, 9), 4),   # um dia antes
    (date(2026, 10, 10), 4),  # no dia
    (date(2026, 10, 11), 4),  # um dia depois
    (date(2026, 10, 12), 1),  # atrasada: recomeça
    (date(2026, 10, 20), 1),
])
def test_watering_on_time_extends_streak_and_late_restarts_it(day: date, expected_streak: int) -> None:
    # Arrange
    plant = _plant_with_streak(3)

    # Act
    plant.water(_at(day), CALENDAR)

    # Assert
    assert plant.watering_streak.current_count == expected_streak
    assert plant.care_schedule.next_due_on == day + timedelta(days=7)


def test_watering_before_the_window_is_rejected() -> None:
    # Arrange
    plant = _plant_with_streak(3)

    # Act & Assert
    with pytest.raises(PlantNotReadyForWateringError, match="2026-10-09"):
        plant.water(_at(date(2026, 10, 8)), CALENDAR)
    assert plant.watering_streak.current_count == 3


def test_regular_schedule_builds_a_streak() -> None:
    # Arrange: o bug antigo só somava com regas em dias seguidos, e o intervalo é de 7 dias
    plant = make_user_plant()
    first = date(2026, 10, 1)

    # Act
    for week in range(4):
        plant.water(_at(first + timedelta(days=7 * week)), CALENDAR)

    # Assert
    assert plant.watering_streak.current_count == 4


def test_first_watering_is_accepted_any_day_and_starts_the_streak() -> None:
    # Arrange
    plant = make_user_plant()

    # Act
    plant.water(_at(date(2026, 10, 1)), CALENDAR)

    # Assert
    assert plant.watering_streak.current_count == 1
    assert plant.care_schedule.next_due_on == date(2026, 10, 8)


def test_only_one_watering_per_day_even_with_daily_interval() -> None:
    # Arrange: com intervalo de 1 dia, a janela da próxima rega abre no mesmo dia
    plant = make_user_plant()
    plant.care_schedule = replace(plant.care_schedule, interval=CareInterval(days=1))
    plant.water(_at(date(2026, 10, 1), hour=8), CALENDAR)

    # Act & Assert
    with pytest.raises(PlantNotReadyForWateringError, match="2026-10-02"):
        plant.water(_at(date(2026, 10, 1), hour=20), CALENDAR)


def test_day_follows_the_garden_time_zone_not_utc() -> None:
    # Arrange: 22h de 11/10 em Brasília já é 12/10 em UTC
    plant = _plant_with_streak(3)
    late_evening = _at(date(2026, 10, 11), hour=22)

    # Act
    plant.water(late_evening, CALENDAR)

    # Assert
    assert plant.watering_streak.current_count == 4


@pytest.mark.parametrize("today, broken", [
    (date(2026, 10, 10), False),
    (date(2026, 10, 11), False),  # ainda dá para regar hoje
    (date(2026, 10, 12), True),   # a janela inteira passou
])
def test_streak_breaks_only_after_the_whole_window(today: date, broken: bool) -> None:
    # Arrange
    plant = _plant_with_streak(3)

    # Act
    result = plant.break_streak_if_missed(today)

    # Assert
    assert result is broken
    assert plant.watering_streak.current_count == (0 if broken else 3)


def test_broken_streak_is_not_broken_again() -> None:
    # Arrange
    plant = _plant_with_streak(3)
    plant.break_streak_if_missed(date(2026, 10, 12))

    # Act
    result = plant.break_streak_if_missed(date(2026, 10, 13))

    # Assert
    assert result is False


@pytest.mark.parametrize("today, needs", [
    (date(2026, 10, 8), False),
    (date(2026, 10, 9), True),
    (date(2026, 10, 15), True),
])
def test_needs_watering_once_the_window_opens(today: date, needs: bool) -> None:
    # Arrange
    plant = _plant_with_streak(3)

    # Act & Assert
    assert plant.needs_watering(today) is needs


def test_plant_never_watered_does_not_need_watering() -> None:
    # Arrange
    plant = make_user_plant()

    # Act & Assert
    assert plant.needs_watering(date(2026, 10, 15)) is False
