from abc import ABC, abstractmethod

from src.domain.value_objects.ids import UserId


class IImageStorage(ABC):
    """
    Porta de saída para armazenamento permanente de imagens.
    Não faz compressão, apenas guarda o arquivo e retorna a URL permanente.
    """
    
    @abstractmethod
    async def upload_identification_image(
        self,
        image_bytes: bytes,
        scientific_name: str,
        confidence_value: float,
        user_id: UserId,
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

    @abstractmethod
    async def upload_training_image(self, image_bytes: bytes, scientific_name: str) -> str:
        """
        Cópia da foto para o dataset de treino: chave própria (aleatória, em prefixo separado),
        nunca devolvida ao cliente, para a amostra não compartilhar arquivo com o usuário.
        """
        ...