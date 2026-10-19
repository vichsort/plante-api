import pytest

from src.shared.domain import InvalidRequestError, PlantEError


def test_the_base_error_cannot_be_raised_by_itself() -> None:
    # Act & Assert: without a code it would reach the client as a made-up error
    with pytest.raises(TypeError, match="has no error code"):
        PlantEError("boom")


def test_a_subclass_falls_back_to_its_default_message() -> None:
    # Act
    error = InvalidRequestError(details={"errors": []})

    # Assert
    assert (error.code, error.status_code) == ("PLANTE_4000_VALIDATION_ERROR", 422)
    assert error.message == "Invalid request data."
    assert error.details == {"errors": []}
