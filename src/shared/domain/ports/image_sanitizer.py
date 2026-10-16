from abc import ABC, abstractmethod


class IImageSanitizer(ABC):
    """
    Limpa a foto enviada pelo usuário antes de qualquer uso (provedores de IA, armazenamento,
    dataset de treino): aplica a orientação e remove todos os metadados (EXIF, GPS, aparelho,
    data). A regra é do domínio porque nenhuma foto pode sair do processo com dado pessoal
    embutido; a biblioteca de imagem fica no adapter.
    """

    @abstractmethod
    def sanitize(self, image_bytes: bytes) -> bytes:
        """
        Devolve a imagem em JPEG, sem metadados. Lança `InvalidImageError` se os bytes não forem
        uma imagem suportada (JPEG, PNG, WebP) ou se a imagem for grande demais.
        """
        ...
