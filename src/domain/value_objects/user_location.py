from dataclasses import dataclass


@dataclass(frozen=True)
class UserLocation:
    country: str  # ISO 3166-1 alpha-2, ex: "BR"
    state: str    # ex: "Santa Catarina"

    def __post_init__(self) -> None:
        country = self.country.strip().upper()
        # Sem title(): "SP" virava "Sp" e "Rio Grande do Sul" virava "Rio Grande Do Sul"
        state = " ".join(self.state.split())
        if len(state) == 2:
            state = state.upper()  # sigla da UF

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