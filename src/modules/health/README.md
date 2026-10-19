# health

## Propósito

O diagnóstico de saúde de uma planta do jardim a partir de uma foto: analisa os sintomas (Kindwise),
classifica a severidade (`healthy`, `low`, `moderate`, `high`, `critical`), sugere um plano de
recuperação (Gemini, quando a planta parece doente e o saldo permite) e grava duas coisas sem
ligação de volta entre elas:
- o **diagnóstico** (`HealthRecord`, histórico do usuário, dado pessoal, apagado com ele e com a
  planta), que recebe o feedback;
- a **amostra de treino de saúde** anônima, pelo `ITrainingRecorder` do training.

Fica de fora:
- a planta (garden, pelo `IPlantLookup`): só se diagnostica planta que está no jardim do usuário;
- a cota de tokens (subscription, pelo `ITokenWallet`);
- a região do usuário para o treino (identity, pelo `IUserDirectory`);
- o vocabulário do dataset (`HealthSeverity`, `HealthSource`, `HealthSignals`) e o feedback, que
  são do training.

## API pública

`src.modules.health` exporta só domínio: `HealthRecord`, `HealthRecordId` e
`HealthRecordNotFoundError`. Nenhum módulo usa o health hoje (está no topo das dependências, ao
lado do achievements).

A composição monta o módulo por:
- `container` (`HealthContainer`), que recebe da raiz o `KindwiseClient` e o breaker do Kindwise
  (os mesmos da identificação) e a chave do Gemini;
- `api` (rotas `POST /diagnose`, `POST /diagnose/{id}/feedback` e `GET /diagnose/history/{user_plant_id}`).

## Decisões

- **Diagnosticar** (`POST /diagnose`, `user_plant_id` e a foto; `latitude`/`longitude` opcionais):
  - Leitura curta antes dos provedores: a região do usuário, a planta (404 se não é dele) e o saldo
    (`ensure_can_diagnose`; sem tokens, nada é enviado aos provedores).
  - A foto vai sem metadados (`IImageSanitizer`) ao Kindwise (`/health_assessment`).
  - **Gemini complementar:** só quando a probabilidade de saúde do Kindwise fica abaixo de **0,5** e
    o saldo cobre o token extra (`can_enrich_diagnosis`). Se o Gemini falhar, o diagnóstico sai só
    com o Kindwise (log `diagnose.enrichment_unavailable`). O limiar é regra de saúde, não de plano.
  - A vitalidade vem do Gemini, se houve complemento; senão, é a probabilidade de saúde do
    Kindwise. A severidade sai da vitalidade: ≥ 0,85 `healthy`; ≥ 0,65 `low`; ≥ 0,45 `moderate`;
    ≥ 0,25 `high`; abaixo, `critical`. A `severity` que o Gemini devolve é ignorada.
  - Escrita curta no fim, sobre o saldo travado: 1 token pelo diagnóstico e mais 1 só se o
    complemento do Gemini foi entregue.
  - O diagnóstico grava `training_sample_id` (vínculo de mão única com a amostra). A amostra tem
    cópia própria da foto, os sinais tipados do Kindwise, o mês, a região e a grade aproximada do
    GPS, e as imagens de referência das doenças (do Kindwise, não do usuário) rehospedadas.
  - A resposta devolve as URLs de referência do Kindwise como vieram (`similar_images_urls`).
- **Feedback** (`POST /diagnose/{id}/feedback`): `correct | wrong | unsure`, a qualquer momento,
  vira um evento na amostra de treino (`HealthLabel`). Confere o dono com
  `health_records.get_for_user` (de outro usuário é 404, como inexistente).
- **Histórico** (`GET /diagnose/history/{user_plant_id}?limit=`): os diagnósticos da planta, do
  mais recente ao mais antigo (padrão 20, máximo 100); planta de outro usuário é 404.
- **Kindwise e Gemini divididos por porta (ISP):** o adapter de saúde do Kindwise mora aqui, com a
  cópia do contrato de resposta do endpoint dele, sobre o `KindwiseClient` do shared. Foto que não
  é planta (`is_plant.binary == false`) vira `NotAPlantError` (do identification, mesma regra do
  `/identify`); 400 do Kindwise só é imagem inválida com `Invalid image data`.
- **Um breaker por provedor:** o `CircuitBreakerHealthAnalyzer` usa o breaker do Kindwise da
  composição; Kindwise fora abre identificação e saúde juntas. O Gemini não tem breaker (já é
  complementar e degradável).
- **`IHealthEnricher.analyze_disease`** fica sem uso, de propósito: é a base da análise profunda
  (entrega futura).
- **Hoje:** a foto do diagnóstico é gravada com `upload_identification_image` (mesmo prefixo das
  fotos de identificação, com a vitalidade no lugar da confiança). Não muda o contrato; vale rever
  quando a política de imagens privadas (URL assinada) for desenhada.

## Erros

| Código | Erro | HTTP | Quando |
| :--- | :--- | :---: | :--- |
| `PLANTE_4630_HEALTH_RECORD_NOT_FOUND` | `HealthRecordNotFoundError` | 404 | Feedback de diagnóstico que não existe ou é de outro usuário. |

Também saem das rotas daqui, definidos em outros módulos: `PLANTE_4530_PLANT_NOT_FOUND` (garden:
planta inexistente, tirada do jardim ou de outro usuário), `PLANTE_4250_DAILY_QUOTA_EXCEEDED`
(subscription: sem tokens), `PLANTE_4001_INVALID_IMAGE` (shared), `PLANTE_4401_NOT_A_PLANT` (`NotAPlantError`, identification),
`PLANTE_4031_USER_NOT_FOUND` e `PLANTE_5010_EXTERNAL_SERVICE_ERROR` (Kindwise fora ou circuito
aberto; o Gemini fora não gera erro).
