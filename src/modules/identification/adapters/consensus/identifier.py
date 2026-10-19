import asyncio

import structlog

from src.domain.exceptions import NotAPlantError
from src.domain.policies.consensus_policy import ConsensusPolicy
from src.domain.ports.plant_identifier import (
    IdentificationResult,
    IPlantIdentifier,
)
from src.shared.domain import ExternalServiceError, InvalidImageError

log = structlog.stdlib.get_logger()

_TIMEOUT_SECONDS = 10.0

class ConsensusIdentifier(IPlantIdentifier):
    """
    Consulta Kindwise e PlantNet em paralelo e resolve a espécie pela `ConsensusPolicy`.

    - `NotAPlantError` do Kindwise veta o PlantNet; outras falhas de um provedor deixam o outro decidir.
    - `similar_images` vêm do provedor cujos dados venceram (`ConsensusResult.provider`;
      Kindwise no acordo exato), cada uma com o próprio `ImageSource`.
    - `signals` junta o que cada provedor que respondeu disse (o que falhou fica de fora).
    """

    def __init__(
        self,
        kindwise: IPlantIdentifier,
        plantnet: IPlantIdentifier,
    ) -> None:
        self._kindwise = kindwise
        self._plantnet = plantnet

    async def identify(
        self,
        image_bytes: bytes,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> IdentificationResult:
        (kindwise_result, kindwise_error), (plantnet_result, plantnet_error) = await asyncio.gather(
            self._call_with_timeout(self._kindwise, image_bytes, latitude, longitude, "kindwise"),
            self._call_with_timeout(self._plantnet, image_bytes, latitude, longitude, "plantnet"),
        )

        if kindwise_result is None and plantnet_result is None:
            _raise_domain_failure(kindwise_error, plantnet_error)

        # Kindwise afirmando que não é planta veta o PlantNet, que sempre tenta achar uma espécie
        # (ex.: planta ao fundo da foto). Outras falhas do Kindwise deixam o PlantNet decidir.
        if isinstance(kindwise_error, NotAPlantError):
            log.info(
                "consensus.vetoed",
                source="kindwise",
                plantnet_species=plantnet_result.scientific_name if plantnet_result else None,
            )
            raise kindwise_error

        consensus = ConsensusPolicy.resolve(kindwise_result, plantnet_result)

        log.info(
            "consensus.resolved",
            scientific_name=consensus.scientific_name,
            reason=consensus.reason.value,
            source=consensus.source,
            confidence=consensus.confidence.value,
            low_confidence=consensus.low_confidence,
            provider=consensus.provider,
        )

        winner = kindwise_result if consensus.provider == "kindwise" else plantnet_result
        assert winner is not None

        return IdentificationResult(
            scientific_name=consensus.scientific_name,
            confidence=consensus.confidence,
            source=consensus.source,
            provider_entity_id=consensus.provider_entity_id,
            gbif_id=consensus.gbif_id,
            family=consensus.family,
            genus=consensus.genus,
            common_names=consensus.common_names,
            similar_images=winner.similar_images,
            low_confidence=consensus.low_confidence,
            signals=tuple(
                signal
                for result in (kindwise_result, plantnet_result)
                if result is not None
                for signal in result.signals
            ),
        )

    async def _call_with_timeout(
        self,
        identifier: IPlantIdentifier,
        image_bytes: bytes,
        latitude: float | None,
        longitude: float | None,
        source: str,
    ) -> tuple[IdentificationResult | None, Exception | None]:
        try:
            result = await asyncio.wait_for(
                identifier.identify(image_bytes, latitude=latitude, longitude=longitude),
                timeout=_TIMEOUT_SECONDS,
            )
            return result, None
        except TimeoutError:
            log.warning("consensus.timeout", source=source)
            return None, ExternalServiceError(message="Timed out.", service=source, retryable=True)
        except Exception as e:
            log.warning("consensus.failed", source=source, error=str(e))
            return None, e


def _raise_domain_failure(*errors: Exception | None) -> None:
    """
    Ambos os provedores falharam: propaga o erro de domínio mais informativo.
    Imagem inválida prevalece sobre indisponibilidade; erros desconhecidos seguem para a policy.
    """
    for error_type in (InvalidImageError, ExternalServiceError):
        for error in errors:
            if isinstance(error, error_type):
                raise error