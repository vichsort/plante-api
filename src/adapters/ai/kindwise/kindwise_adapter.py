import asyncio
import httpx
from src.domain.ports.plant_identifier import IPlantIdentifier

_BASE_URL = "https://plant.id/api/v3/"

class KindwiseAdapter(IPlantIdentifier):

    def __init__(self, api_key: str) -> None:
        self._headers = {"Api-Key": api_key, "Content-Type": "application/json"}

    async def identify(self, image_base64: str, latitude: float | None, longitude: float | None) -> dict:
        payload = {"images": [image_base64], "similar_images": True}
        if latitude and longitude:
            payload |= {"latitude": latitude, "longitude": longitude}
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{_BASE_URL}identification", headers=self._headers, json=payload)
            r.raise_for_status()
            return r.json()