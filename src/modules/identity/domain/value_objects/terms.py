from dataclasses import dataclass


@dataclass(frozen=True)
class Terms:
    """
    The terms in force: what the user accepts on sign-up (the photos go to the identification
    providers and become an anonymous training dataset). The text lives on the site (`url`); a new
    `version` makes everyone accept again before using the AI.
    """
    version: str
    url: str | None = None

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("The terms need a version.")
