from enum import StrEnum


class RemovalReason(StrEnum):
    """
    Why the user took the plant out of the garden. Only `misidentified` says something about the
    identification; the others are recorded for the dataset without a vote on the label.
    """
    DIED = "died"
    GAVE_AWAY = "gave_away"
    MISIDENTIFIED = "misidentified"
    OTHER = "other"
