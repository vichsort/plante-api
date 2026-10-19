import pytest

from src.domain.value_objects.user_location import UserLocation


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("SP", "SP"),
        (" sp ", "SP"),
        ("Rio Grande do Sul", "Rio Grande do Sul"),
        ("RIO DE JANEIRO", "Rio de Janeiro"),
        ("  santa   catarina ", "Santa Catarina"),
        ("espírito santo", "Espírito Santo"),
    ],
)
def test_state_is_normalized_without_breaking_abbreviations_or_connectives(typed: str, stored: str) -> None:
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
