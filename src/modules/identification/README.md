# identification

## Propósito

"Que planta é esta?" a partir de uma foto: consulta os provedores de visão (Kindwise e PlantNet),
resolve a espécie por consenso e grava duas coisas sem ligação de volta entre elas:
- a **identificação** (histórico do usuário, dado pessoal, apagada com ele), que recebe o feedback
  e é a origem de uma planta no jardim;
- a **amostra de treino** anônima, pelo `ITrainingRecorder` do training.

Fica de fora:
- a espécie e as imagens de referência (catalog, pelo `ISpeciesRegistry`);
- a cota de tokens e o limite diário do serviço (quota, pelo `ITokenWallet` e pelo `IProviderBudget`);
- a planta no jardim (garden): `POST /identify` **não cria planta**. Adicionar ao jardim é uma
  ação separada, que lê a identificação pelo `IIdentificationLookup`.

## API pública

`src.modules.identification` exporta só domínio:

- **`IIdentificationLookup`**: `get_for_user(identification_id, user_id)` devolve a
  `Identification` ou lança `IdentificationNotFoundError` (não existe ou é de outro usuário: a API
  não distingue). Lê dentro da transação de quem chama, se houver. O garden usa para criar a
  planta.
- **Tipos:** `Identification`, `IdentificationId`, o evento `PlantIdentifiedEvent` e os erros
  `IdentificationNotFoundError` e `NotAPlantError` (este também para o adapter de saúde do
  Kindwise).

A composição monta o módulo por:
- `container` (`IdentificationContainer`), que recebe da raiz o `KindwiseClient` e os breakers de
  Kindwise e PlantNet;
- `api` (rotas `POST /identify` e `POST /identify/{id}/feedback`).

O dublê do lookup para testes fica em `tests/fakes.py` (`FakeIdentificationLookup`), junto com as
portas em memória dos testes daqui.

## Decisões

- **Identificar:**
  - Confere só os tokens do dia; o limite do jardim vale ao adicionar ao jardim.
  - Answers `image_url`, a signed link to the photo that expires, never the stored key.
  - A foto é limpa antes de qualquer uso (`IImageSanitizer`, do shared): orientação aplicada,
    metadados removidos (EXIF, GPS, aparelho, data), regravada em JPEG. Aceita JPEG, PNG, WebP e
    HEIC (iPhone); outro formato, arquivo que não é imagem ou imagem acima de 60 MP → `PLANTE_4001`.
  - Nenhuma transação fica aberta durante as chamadas à IA e ao armazenamento. A escrita (espécie, amostra de
    treino, identificação e a cobrança do token) é uma transação só, aberta pela UoW daqui; os
    services dos outros módulos se juntam a ela.
  - Confiança abaixo de 60% (`ConfidenceScore.is_rejected`) → `PLANTE_4400`, sem gravar nem
    cobrar nada. De 60% a 84%, a resposta pede revisão (`needs_human_review`).
  - `PlantIdentifiedEvent` sai depois do commit. Ninguém consome ainda (conquistas, depois).
- **Feedback** (`POST /identify/{id}/feedback`): `correct | wrong | unsure` + sugestão opcional de
  espécie. A qualquer momento, quantas vezes o usuário quiser; cada resposta é um evento na amostra
  de treino, sem dizer de quem veio.
- **Consenso** (`ConsensusIdentifier`, com `CONSENSUS_ENABLED=true`; desligado, só o Kindwise).
  Kindwise e PlantNet em paralelo (timeout de 10s cada), e a `ConsensusPolicy` escolhe:
  - acordo exato → média ponderada (Kindwise 60%, PlantNet 40%), `source="consensus"`;
  - acordo de gênero → vence o maior score, `source="consensus_partial"`, sempre `low_confidence`;
  - desacordo total → vence o Kindwise, salvo se o PlantNet tiver 20 pontos percentuais a mais;
    sempre `low_confidence`;
  - um provedor falha → o outro decide sozinho (`source` = nome dele). Os dois falham →
    `NotAPlantError` prevalece sobre `InvalidImageError`, que prevalece sobre `ExternalServiceError`.
  - **Veto:** se o Kindwise afirmar que a imagem não é planta (`is_plant.binary == false` →
    `NotAPlantError`), a requisição falha com `PLANTE_4401` mesmo que o PlantNet tenha devolvido
    uma espécie. Outras falhas do Kindwise (sugestões vazias, imagem ilegível) não vetam.
  - As imagens de referência vêm do provedor cujos dados venceram (Kindwise no acordo exato), com
    a origem correta (`kindwise_similar` / `plantnet_similar`).
  - Os sinais de treino juntam o que cada provedor que respondeu disse (o que falhou fica de fora).
- **Quando um provedor gera `PLANTE_4001` ou `PLANTE_4401`:**
  - Kindwise: `is_plant.binary == false` explícito → `NotAPlantError` (campo ausente segue o fluxo
    normal); lista de sugestões vazia → `InvalidImageError`; HTTP 400 → `InvalidImageError` **só**
    se o corpo contiver `Invalid image` (outros 400 são payload nosso malformado →
    `ExternalServiceError(retryable=False)` + log `provider.request_rejected`).
  - PlantNet: HTTP 400 com `Unsupported file type` ou 404 com `Species not found` →
    `InvalidImageError`; outros 400/404 → `ExternalServiceError(retryable=False)`. Só aceita
    multipart (JSON → 415).
- **Kindwise dividido por porta.** O `KindwiseClient` (shared) tem URL, chave e tradução de erros;
  o `KindwiseIdentifier` daqui só fala com `/identification`, e a saúde tem o próprio adapter para
  `/health_assessment`. O contrato de resposta (Pydantic) de cada endpoint fica com o adapter dele.
- **Um circuit breaker por provedor**, criado na raiz e entregue aqui: Kindwise fora abre
  identificação e saúde juntas.
- **Escolha do identificador por `Callable` tipado** (`_pick_identifier`), não `Selector`: o
  `Selector` do dependency-injector tipa como `Any` e comparava o bool como texto.
- **Testes:**
  - As respostas reais dos provedores continuam em `tests/fixtures/providers` (catálogo único,
    com as de saúde, documentado num README só); os testes daqui leem de lá.
  - Contrato contra as APIs reais (`tests/contract`, fora da execução padrão):
    `uv run --env-file .env pytest -m contract`. As chaves (`KINDWISE_API_KEY`,
    `PLANTNET_API_KEY`) vêm do ambiente, porque o módulo não lê o `Settings` da composição.

### Como adicionar um provedor de identificação

1. Um adapter em `adapters/<provedor>/identifier.py` que implementa `IPlantIdentifier`, com o
   contrato da resposta em Pydantic e só os campos usados (o resto pode ecoar dado do usuário).
2. Os sinais do provedor (`IdentificationSignals`, do training) sem nada que identifique o usuário.
3. O breaker do provedor na raiz (`src/bootstrap/containers/adapters.py`) e o adapter no
   `IdentificationContainer`.
4. Testes em `tests/unit/`, com a resposta real em `tests/fixtures/providers`.

## Erros

| Código | Erro | HTTP | Quando |
| :--- | :--- | :---: | :--- |
| `PLANTE_4400_LOW_CONFIDENCE` | `LowConfidenceError` | 422 | Confiança da identificação abaixo de 60%. |
| `PLANTE_4401_NOT_A_PLANT` | `NotAPlantError` | 422 | O Kindwise afirmou que a foto não é planta (a imagem em si é legível). Também no diagnóstico. |
| `PLANTE_4430_IDENTIFICATION_NOT_FOUND` | `IdentificationNotFoundError` | 404 | Identificação não existe ou não pertence ao usuário (feedback, adicionar ao jardim). |
