from dataclasses import dataclass

# Ficam em minúsculas no meio do nome ("Rio Grande do Sul", "Rio de Janeiro")
_CONNECTIVES = frozenset({"de", "da", "do", "das", "dos", "e"})


@dataclass(frozen=True)
class UserLocation:
    country: str  # ISO 3166-1 alpha-2, ex: "BR"
    state: str    # ex: "Santa Catarina"

    def __post_init__(self) -> None:
        country = self.country.strip().upper()
        state = _normalize_state(self.state)

        object.__setattr__(self, "country", country)
        object.__setattr__(self, "state", state)

        if len(self.country) != 2:
            raise ValueError(
                f"Invalid country '{self.country}'. Expected ISO 3166-1 alpha-2 (e.g., 'BR')."
            )
        if len(self.state) < 2:
            raise ValueError(f"Invalid state '{self.state}'. Minimum 2 characters.")

    def __str__(self) -> str:
        return f"{self.state}, {self.country}"


def _normalize_state(typed: str) -> str:
    """
    Sigla em maiúsculas ("sp" → "SP"); nome com inicial maiúscula, menos os conectivos. Antes o
    `title()` fazia "SP" virar "Sp" e "Rio Grande do Sul" virar "Rio Grande Do Sul".
    """
    words = typed.split()
    if len(words) == 1 and len(words[0]) == 2:
        return words[0].upper()
    return " ".join(
        word.lower() if index > 0 and word.lower() in _CONNECTIVES else word.capitalize()
        for index, word in enumerate(words)
    )
