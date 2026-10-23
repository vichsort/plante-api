from abc import ABC, abstractmethod

from src.shared.domain.value_objects.ids import UserId


class IImageStorage(ABC):
    """
    Outbound port for permanent image storage. Does no compression: it stores the file and returns
    its key, a path relative to the storage (`identifications/<user>/<species>/<uuid>.jpg`). The
    database keeps only keys, so the backend can change without touching stored rows; the client
    gets a link from `signed_url`, never the key.
    """

    @abstractmethod
    async def upload_identification_image(
        self,
        image_bytes: bytes,
        scientific_name: str,
        confidence_value: float,
        user_id: UserId,
    ) -> str:
        """Returns the key of the stored image."""
        ...

    @abstractmethod
    async def download_and_rehost(
        self,
        external_url: str,
        scientific_name: str,
    ) -> str:
        """Downloads an external URL (Kindwise) and stores it. Returns the key."""
        ...

    @abstractmethod
    async def delete_user_images(self, user_id: UserId) -> int:
        """
        Deletes every photo the user sent (identifications and diagnoses); the training copies
        stay. Returns how many objects went. Raises `ExternalServiceError` if the storage fails.
        """
        ...

    @abstractmethod
    async def upload_training_image(self, image_bytes: bytes, scientific_name: str) -> str:
        """
        Cópia da foto para o dataset de treino: chave própria (aleatória, em prefixo separado),
        nunca devolvida ao cliente, para a amostra não compartilhar arquivo com o usuário.
        """
        ...

    @abstractmethod
    async def signed_url(self, key: str) -> str:
        """
        A link that opens the image without a token (an `<img>` cannot send one) and expires; the
        lifetime is the storage's setting. Whoever holds the link sees the image until then.
        """
        ...
