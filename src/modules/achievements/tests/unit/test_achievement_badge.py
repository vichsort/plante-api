from src.modules.achievements.domain.value_objects.achievement_badge import (
    AchievementBadge,
)


def test_badge_is_found_by_its_code() -> None:
    # Act
    badge = AchievementBadge.from_code("first_plant")

    # Assert
    assert badge is AchievementBadge.FIRST_PLANT
    assert (badge.title, badge.icon_name) == ("Primeira Folha", "psychology_alt")


def test_unknown_code_has_no_badge() -> None:
    # Act
    badge = AchievementBadge.from_code("FIRST_PLANT_ADDED")

    # Assert
    assert badge is None


def test_badge_codes_are_unique() -> None:
    # Act
    codes = [badge.code for badge in AchievementBadge]

    # Assert
    assert len(codes) == len(set(codes))
