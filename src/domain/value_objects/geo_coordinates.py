from dataclasses import dataclass

@dataclass(frozen=True)
class GeoCoordinates:
    latitude: float
    longitude: float

    def __post_init__(self):
        """Garante que as coordenadas matematicamente existem no planeta Terra."""
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Latitude must be between -90 and 90. Got: {self.latitude}")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"Longitude must be between -180 and 180. Got: {self.longitude}")

    def __str__(self) -> str:
        return f"Lat: {self.latitude}, Lon: {self.longitude}"