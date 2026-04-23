from abc import ABC, abstractmethod

class IImageStorage(ABC):
    """
    Porta de saída para armazenamento permanente de imagens.
    Não faz compressão, apenas guarda o arquivo e retorna a URL permanente.
    """
    
    @abstractmethod
    def upload_identification_image(self, image_b64: str, scientific_name: str, confidence_value: float, user_id: int) -> str:
        """
        Salva a imagem organizando-a para o futuro dataset da IA própria.
        Retorna a URL pública/permanente do arquivo.
        """
        ...