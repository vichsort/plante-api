from abc import ABC, abstractmethod

class IImageStorage(ABC):
    """
    Porta de saída para armazenamento permanente de imagens.
    Não faz compressão, apenas guarda o arquivo e retorna a URL permanente.
    """
    
    @abstractmethod
    async def upload_identification_image(
        self,
        image_b64: str,
        scientific_name: str,
        confidence_value: float,
        user_id: int,
    ) -> str:
        """Retorna o storage_key da imagem salva."""
        ...

    @abstractmethod
    async def download_and_rehost(
        self,
        external_url: str,
        scientific_name: str,
    ) -> str:
        """Baixa URL externa (Kindwise) e re-hospeda no bucket. Retorna storage_key."""
        ...