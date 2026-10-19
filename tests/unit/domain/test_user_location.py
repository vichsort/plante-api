import pytest

from src.domain.value_objects.user_location import UserLocation


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("SP", "SP"),
        (" sp ", "SP"),
        ("Rio Grande do Sul", "Rio Grande do Sul"),
        ("  Santa   Catarina ", "Santa Catarina"),
    ],
)
def test_state_keeps_the_typed_case_and_uppercases_abbreviations(typed: str, stored: str) -> None:
    # Arrange
    country = "br"

    # Act
    location = UserLocation(country=country, state=typed)

    # Assert: antes o title() transformava "SP" em "Sp", inclusive na região do treino
    assert location.state == stored
    assert location.country == "BR"


def test_state_shorter_than_two_characters_is_rejected() -> None:
    # Act & Assert
    with pytest.raises(ValueError):
        UserLocation(country="BR", state=" S ")
