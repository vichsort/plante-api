# TODO — PlantE API

Pendências levantadas na revisão da Fase 6 (middlewares, probes, circuit breaker, OpenAPI).

## Estado e próximos passos (fim da sessão de 2026-10-15)

Leia esta seção primeiro. Ela substitui o "Próximo passo" antigo do fim da ordem de execução.

**Feito em 2026-10-15** (commits na `main`):
- import-linter com 3 contratos.
- Redis e Postgres reais nos testes (testcontainers).
- E-mail normalizado (minúsculas, CHECK no banco).
- Worker do Celery corrigido.
- Redis: comando recusado vira `retryable=False`.
- FastAPI 0.115.14.
- Teste migrations × modelos.
- **Item 13: Unit of Work.** Toda escrita passa por `IUnitOfWork` com commit explícito; antes disso nada era gravado.
- **Plano C implementado** (detalhes e decisões na seção abaixo; regras no `ARCHITECTURE.md`, seção 2.6): EXIF removido (Pillow), identificação × jardim × treino separados, sinais tipados no lugar do `raw_response`, feedback no lugar das confirmações, worker de anonimização removido. Migration `a3c9e1f4b7d2`.

- Teste de fumaça com API + worker reais (Postgres/Redis em contêiner) e correção dos achados: broker do Celery com a mesma URL do `Settings`, task de e-mail com `acks_late`/`reject_on_worker_lost` e reaproveitando o código ativo.
- **Release `v0.1.0`** (tag anotada na `main`, 2026-10-15). Primeiro push com CI no GitHub: verde (288 testes, inclusive Postgres/Redis via testcontainers).

Suíte: 288 testes. CI: `ruff`, `mypy`, `lint-imports`, `pytest`.

**Falta validar a `v0.1.0` (depende das credenciais do usuário):**
- [ ] Testes de contrato contra as APIs reais: `uv run pytest -m contract` no PC de casa (~2 créditos do Kindwise). Os adapters mudaram (sinais tipados) depois da última rodada.
- [ ] Um `/identify` real com as chaves e o S3 de verdade. Risco: bucket novo bloqueia `ACL="public-read"` por padrão, e o upload (inclusive a cópia de treino) pode falhar. Se falhar, corrigir numa `v0.1.1`.

**Manutenção do CI (avisos do GitHub no primeiro run):**
- [ ] `actions/checkout@v4` e `astral-sh/setup-uv@v6` usam Node 20 (descontinuado; hoje forçados para o Node 24). Atualizar as versões no `.github/workflows/ci.yml`.
- [ ] `ubuntu-latest` migra para Ubuntu 26 a partir de 2026-10-19: acompanhar o próximo run.

**Ordem combinada com o usuário:**
1. ~~**Plano C: separar dados do usuário e dados de treino + anonimização**~~ ✅ (2026-10-15). Pendências que sobraram, na seção do plano: HEIC, motivo da exclusão como sinal, engine de confiança, geocodificação reversa.
2. **Item 8: monólito modular** (seção "Item 8 — conceitos" abaixo), num branch próprio (`develop` ou `refactor/*`) a partir da `v0.1.0`, com mais testes garantindo o comportamento de ponta a ponta. **É o próximo passo** (depois das duas validações acima).
3. Depois:
   - fotos públicas no S3 (URLs assinadas);
   - engine de confiança do rótulo;
   - análise profunda pela metade (Gemini);
   - itens de "Antes de publicar";
   - `ANTIGRAVITY.md` (item 11);
   - reuso de e-mail de conta com soft delete.

**Princípio de desenho pedido pelo usuário — a balança:** nem tudo vira porta ou abstração. Para cada escolha, pese utilidade real, conforto, preguiça e boa prática, e diga qual lado justifica. Exceção deliberada se documenta (exemplo: o probe importa o `RedisClient` direto, registrado no import-linter).

---

## Plano C — dados do usuário × dados de treino (decidido e implementado em 2026-10-15)

**Implementado.** O que ficou como o plano previa e o que foi decidido durante a implementação:
- Nomes finais: tabelas `identifications`, `training_identification_samples`, `training_health_samples`, `training_feedback`; entidades `Identification`, `TrainingIdentificationSample`, `TrainingHealthSample`, `TrainingFeedback`; porta `ITrainingRepository` (só acrescenta) e `uow.training`.
- Rotas: `POST /identify` (devolve `identification_id`), `POST /identify/{id}/feedback`, `POST /garden` (`identification_id`, `nickname` opcional; idempotente), `DELETE /garden/{id}` (sem corpo), `POST /diagnose` (+ `latitude`/`longitude` opcionais), `POST /diagnose/{id}/feedback`. Coordenadas fora da faixa → 422.
- Erros aposentados: `PLANTE_4015_SAMPLE_NOT_FOUND` e `PLANTE_4018_RAW_RESPONSE_EXPIRED` (não reutilizar os números).
- Tabelas de treino sem `AuditMixin` (não têm `created_at`/`updated_at`): só `period` (mês). `health_records.user_id` passou a `CASCADE`.
- Valores dos provedores guardados sem arredondar (com o modelo de ameaça corrigido, arredondar só perderia informação útil).
- Rehospedagem das imagens de referência das doenças no próprio `/diagnose` (síncrona). Se a latência incomodar, passar a uma task do Celery.
- Guardas: `test_training_tables.py` (colunas em lista fechada), filtro dos sinais com as respostas reais dos provedores, fluxo completo até apagar o usuário (`test_user_and_training_flow.py`).
- **Ainda em aberto:** HEIC (hoje rejeitado com 4013; avaliar `pillow-heif`); motivo da exclusão da planta como sinal; engine de confiança do rótulo; geocodificação reversa (hoje o estado vem do perfil); fotos públicas no S3 (item próprio, mais abaixo).

---

**Desenho original (mantido como referência):**

**Requisito (do usuário, inegociável):** tudo o que treina a IA é anônimo, tanto identificação quanto saúde. A IA treinada não pode ser pessoalizada. Usuário apagar planta ou conta **nunca** remove dado de treino.

**Modelo de ameaça (corrigido pelo usuário):**
- Quem tem acesso a produção sempre acha um jeito de religar dados. Não complicar o código para impedir isso: nada de regravar em transação separada por causa do `xmin`, nem de esconder IDs dos logs.
- O que importa é o **dataset como artefato** (exportado, usado para treinar, compartilhado): ele não pode conter dado pessoal.
- Um vínculo **de mão única** do lado do usuário para a amostra de treino é aceito. Enquanto existe, a amostra no nosso banco é pseudônima; ele some quando os dados do usuário são apagados, e a exportação nunca o leva.

### Três conceitos separados

Hoje o `user_plant` faz dois papéis, e isso é um bug:
- O `/identify` cria o `user_plant` e ele aparece no jardim na hora (`list_by_user` não filtra).
- "Adicionar ao jardim" só soma 1 ao `garden_count` e confirma a amostra.
- O limite do plano FREE conta o contador, não o que aparece no jardim.
- O `/identify` checa o limite do jardim, então um usuário FREE com 3 plantas não consegue nem identificar.

| Conceito | O que é | Criado quando | Dono / ciclo de vida |
| :--- | :--- | :--- | :--- |
| **Identificação** (a tabela `plant_identification_samples` atual, renomeada, ex.: `identifications`) | Histórico de "identifiquei esta foto": resultado, foto do usuário, `training_sample_id` (vínculo de mão única). Recebe o feedback. | `/identify` | Usuário. Pessoal, apagada com ele (FK `CASCADE` no `user_id`). |
| **Planta no jardim** (`user_plant`) | Planta que o usuário cultiva: rega, sequência, diagnósticos. Referencia a identificação de origem. | **Só** ao adicionar ao jardim, a partir de uma identificação. | Usuário. |
| **Amostra de treino** (tabelas novas, ex.: `training_identification_samples`, `training_health_samples`) | Dado anônimo para treino. Sem `user_id`, sem FK para dado do usuário. | `/identify` e `/diagnose`, **na hora** (sem esperar confirmação nem prazo). | Ninguém. Nunca apagada por ação do usuário. |

Saúde:
- `health_records` é o lado do usuário e ganha um `training_sample_id`.
- `health_identification_samples` vira a tabela de treino de saúde: sai o `user_id`, sai a FK para `health_records`.

### API (contrato muda — aprovado pelo usuário)

- `/identify` devolve a **identificação**, sem criar planta. Verifica só os tokens, não o limite do jardim (o limite fica para quando entra no jardim).
- **Feedback** substitui a "confirmação": `POST` na identificação com `acertou | errou | nao_sei` e uma sugestão opcional de espécie ("qual é, então?"). Pode chegar a qualquer momento, sem janela. Motivo: o usuário não tem como saber a espécie com certeza; "confirmar" pede uma certeza que ele não tem.
- **Adicionar ao jardim** recebe o ID da identificação, **cria** o `user_plant`, aplica o limite do FREE e registra um sinal implícito positivo no treino.
- **Apagar planta** só tira do jardim. **Não é rejeição** da identificação (a planta pode ter morrido). A identificação e o treino continuam. Futuro: perguntar o motivo da exclusão e usar como sinal na engine.
- **Saúde:** `/diagnose` cria o `health_record` (usuário) e a amostra de treino de saúde na hora. `/diagnose/confirm` vira feedback sobre o diagnóstico.
  - O Redis de "avaliação pendente" (`RedisHealthRawResponseRepository`) e o erro `PLANTE_4018_RAW_RESPONSE_EXPIRED` deixam de existir.
  - As imagens de referência do Kindwise são rehospedadas no `/diagnose`. Se a latência incomodar, passar a uma task do Celery.
- `garden_count` passa a ser **calculado** (contagem de plantas ativas): sai a coluna, que divergia.
- Atualizar o catálogo de erros do `ARCHITECTURE.md` (4015/4018 etc.) e os `raises` dos use cases.

### O que entra e o que nunca entra no treino

- **Entra:**
  - cópia da foto (chave aleatória em prefixo próprio, ex.: `training/…`, sem EXIF, nunca devolvida ao cliente);
  - rótulo (espécie, família, gênero, IDs públicos do GBIF/Kindwise);
  - **sinais dos provedores**: sugestões com probabilidade, por provedor, `is_plant`, tipo de consenso/`source`, versão do modelo do provedor;
  - no caso de saúde: doenças, vitalidade arredondada, severidade, plano de tratamento (gerado pelo Gemini);
  - **mês** (`YYYY-MM`);
  - **localização aproximada**: estado + grade de ~11 km (lat/long arredondados a 1 casa decimal). O usuário quer guiar por região: plantas são mais comuns em regiões específicas.
- **Nunca entra:**
  - `user_id` ou qualquer ID do lado do usuário;
  - GPS exato;
  - URL ou chave da foto do usuário;
  - EXIF;
  - do Kindwise: `access_token` (permite buscar a identificação com a foto na API deles), `input` (ecoa coordenadas, URL da imagem e data/hora), `custom_id`, `created`/`completed`;
  - do PlantNet: `query` (imagens) e `remainingIdentificationRequests`;
  - horários exatos.
- **Origem da localização:** GPS do `/identify` quando enviado (o form já aceita `latitude`/`longitude`); se não vier, só o estado do perfil (`UserLocation`), sem grade. O `NominatimGeocoder` só faz estado → coordenadas, não o contrário; para tirar o estado do GPS, seria preciso geocodificação reversa (decidir depois; não bloqueia).
- O `raw_response` bruto **não** fica do lado do usuário (ele não precisa); o treino guarda os sinais já filtrados.
- **Teste de guarda:** as colunas das tabelas de treino conferidas contra uma lista permitida (nenhum `user_id`, nenhuma FK para tabelas do usuário), e o filtro do `raw_response` testado com as fixtures reais de `tests/fixtures/providers/`.

### EXIF (Pillow aprovado)

- Remover o EXIF **antes** de mandar aos provedores e antes de gravar no S3.
- Aplicar a orientação do EXIF antes de removê-lo (`ImageOps.exif_transpose`) e regravar (JPEG qualidade ~90).
- Aceitar JPEG/PNG/WebP. **HEIC (iPhone) não abre no Pillow puro:** decidir entre `pillow-heif` e rejeitar com 4013. As rotas hoje não validam o tipo de arquivo.
- Recomendação pela balança: uma porta no domínio (ex.: `IImageSanitizer`) com adapter Pillow, chamada pelo use case. A regra "sanitizar antes de qualquer uso externo" é de negócio e vale para toda entrada (API e workers); a biblioteca fica no adapter.

### Feedback e sinais (o que coletar agora)

- **Eventos acumulados**, não um status: tabela de feedback ligada à amostra de treino, sem `user_id`. Cada evento tem tipo (`acertou`/`errou`/`nao_sei`), sugestão opcional, origem (`explicito`, `jardim_adicionado`, futuramente `motivo_exclusao`, `cuidado_continuado`) e data.
- O usuário pode mudar de ideia; a engine decide como pesar a sequência.
- Coletar tudo agora, porque dado não coletado não volta. A engine vem depois.

### Engine de confiança do rótulo (tarefa separada, depois do plano C)

Pedido do usuário: no mesmo espírito da engine de consenso, especializada, com pesos, detalhes técnicos, exceções e hierarquia, bem explicada e estruturada (seção própria no `ARCHITECTURE.md`, como o consenso).

Rascunho da hierarquia:
1. **Vetos:** provedor diz que não é planta, ou usuário diz que não é planta → amostra fora do treino.
2. **Base, a evidência dos provedores:** acordo exato > acordo de gênero > um provedor só > desacordo, ponderado pela confiança de cada um (reaproveitar a `ConsensusPolicy`).
3. **Feedback explícito:** o negativo pesa mais que o positivo (quem não concorda costuma se dar ao trabalho de dizer, e quem concorda nem sempre). Feedbacks em conflito: vale o mais recente.
4. **Sinais implícitos:** jardim, cuidado continuado, motivo de exclusão. Peso baixo, nunca decidem sozinhos.
5. **Exceções:** confiança baixa dos provedores + feedback positivo → "revisar", não "confiável". Sugestão de espécie que diverge dos provedores → candidata, não rótulo.

Saída: rótulo + peso + motivos (auditável). **Calculada na exportação, a partir dos sinais brutos, e versionada**: os pesos mudam sem migrar dados. Entra aqui também o que fazer com `has_deep_analysis`/`has_nutritional_analysis`/`is_complete_for_training` (nunca marcados hoje).

### Também sai com o plano C

- **Worker de anonimização:** sai `workers.anonymize_confirmed_samples`, a entrada no `beat_schedule` e o `RETENTION_DAYS`. Deixa de existir a espera de 30 dias.
- **Cascata das FKs e exclusão de usuário que falhava:** resolvidas pelo desenho. O lado do usuário apaga em cascata; o treino não tem FK para o usuário.
- **Banco vazio:** o schema pode ser remodelado à vontade, mas sempre via migration do Alembic (o teste migrations × modelos confere).

---

## Item 8 — conceitos e recomendações (para quem for fazer)

O usuário combinou fazer o item 8 depois do plano C, num branch próprio. Estes são os conceitos e as recomendações discutidos.

**Recomendação geral:**
- **Não migrar tudo.** Fazer só o piloto (identificação) e avaliar se o ganho compensa. Para um projeto deste tamanho, com uma pessoa, o monólito modular completo tende a ser exagero, e o import-linter já protege as camadas.
- **Fazer depois do plano C**, porque o C redefine as fronteiras (identificação × jardim × treino).

**Módulos candidatos** (subdomínio por módulo, hexagonal dentro, testes junto, shared kernel mínimo):
- **identity:** usuário, autenticação, OTP, tokens JWT.
- **subscription/profile:** plano, tokens diários, conquistas.
- **identification:** identificações, espécies, imagens de referência, provedores de IA, consenso.
- **garden:** `user_plant`, cuidados, sequência.
- **health:** diagnóstico.
- **training:** novo, nasce do plano C. Amostras de treino, feedback, engine de confiança do rótulo, exportação.
- **shared kernel:** IDs (`NewType`), `JsonValue`, exceções base. Só o que é realmente comum.

**Acoplamentos difíceis**, que são a discussão real:
- **O `User` é tocado por todos:** tokens, plano, `garden_count`. O plano C já remove o `garden_count`, calculado a partir do jardim.
- **Tokens:** identificação e saúde gastam tokens de subscription. Recomendação: uma porta no módulo consumidor (ex.: `ITokenWallet`), implementada por subscription, chamada **na mesma transação**, porque cobrança precisa de consistência forte. Eventos assíncronos aqui abririam espaço para cobrar sem entregar, ou entregar sem cobrar.
- **Treino alimentado por identification/health:** recomendação: uma porta do módulo training (ex.: `ITrainingRecorder`) chamada na mesma transação, para a amostra não se perder se a publicação de um evento falhar. A porta mantém a fronteira.
- **Unit of Work por módulo:** com um Postgres só, manter **uma transação física**; cada módulo vê só os próprios repositórios (UoW do módulo como uma visão sobre a mesma sessão). A fronteira é garantida pelo import-linter, não por sessões separadas.

**Mecânica:**
- **Layout sugerido:** `src/modules/<nome>/{domain,adapters,api}`, `src/shared/` (kernel), `src/infrastructure/` (composição: containers, settings, Celery), `src/main.py`. Testes junto do módulo ou em `tests/modules/<nome>/`; ajustar `testpaths` e o `pyproject`.
- **import-linter:** um contrato de independência entre módulos, um contrato de camadas dentro de cada módulo e um contrato de shared kernel (ninguém importa módulo pelo kernel).
- **Antes de mover código:** escrever **testes de caracterização de ponta a ponta** (rotas HTTP contra Postgres/Redis reais via testcontainers). Hoje os testes de rota mocam os use cases, então não garantem o comportamento de A a B durante a refatoração. É o "aumentar testes para garantir consistência" que o usuário pediu.
- **Branch:** fechar a `main`, abrir `develop` e fazer o piloto em `refactor/modular-identification` (ou similar).

---

## Ordem de execução (revisada em 2026-10-14)

Substitui a ordem anterior (Bloco 1 → 2 → 3). Prioridade por impacto real; os blocos abaixo continuam como detalhamento dos itens.

**Crítico — fazer agora, nesta ordem:**
1. ~~**Kindwise: confirmar contrato de erro e `is_plant`**~~ ✅ (Bloco 1) — bug visível ao usuário: foto que não é planta vira identificação.
2. ~~**Rate limit: chave por usuário em vez de IP + `--proxy-headers`**~~ ✅ (Bloco 2) — atrás de load balancer o limite vira global e bloqueia todos.
3. ~~**Redis: timeouts curtos + backoff quando cai**~~ ✅ (Bloco 2) — Redis lento hoje deixa todas as rotas lentas.
3a. ~~**PlantNet: adapter nunca funcionou**~~ ✅ (achado nos testes reais) — mandava JSON e a API só aceita multipart (415); parser lia campos inexistentes.

**Próximos — decididos em 2026-10-14 (4–7, 9, 10 feitos em 2026-10-15):**
4. ~~**Consenso: veto do `is_plant` + campos descartados**~~ ✅ (ver Bloco 1). Veto via `NotAPlantError` (subclasse de `InvalidImageError`, mesmo `PLANTE_4013`); novo `ImageSource.PLANTNET_SIMILAR` (migration `6669c3cc2c4a`). Pendente: publicar o comentário na issue #1. Decidido: `raw_response` guarda as duas respostas (`{"kindwise": ..., "plantnet": ...}`); imagens similares vêm do provedor vencedor, com `ImageSource` correto; `is_plant == false` do Kindwise veta o PlantNet. Documentar a regra no `ARCHITECTURE.md`, no `ConsensusIdentifier` e na issue #1.
5. ~~**CI (GitHub Actions)** + **testes de contrato**~~ ✅ (contrato ainda não rodado contra as APIs reais; CI roda no primeiro push) (`pytest -m contract`, fora do CI e do padrão: chamam Kindwise/PlantNet reais com as imagens de `tests/fixtures/providers/README.md`, baixadas na hora; ~2 créditos Kindwise por rodada). CI: `ruff`, `mypy`, `pytest` em push e PR de qualquer branch (hoje roda na `main`; com `develop` + PRs, só adicionar proteção de branch). Decidido: instalar stubs (`types-*`) e ligar `strict = true` — medido: 115 erros em 62 arquivos, 87 deles `type-arg` (mecânicos).
6. ~~**Código do checklist de deploy**~~ ✅ (uvicorn 0.54.0; `AI_BREAKER_FAILURE_THRESHOLD` / `AI_BREAKER_RECOVERY_TIMEOUT_SECONDS`): atualizar uvicorn (CIDR em `FORWARDED_ALLOW_IPS`); thresholds do circuit breaker em `Settings` (manter 5 falhas / 30s).
7. ~~**Postgres nos testes de integração** via `testcontainers`~~ ✅ (schema via Alembic; cada teste em transação desfeita no fim; sem Docker pula localmente e falha no CI). Testes que aproveitam os ganhos feitos em 2026-10-15 (`tests/integration/persistence/test_postgres_schema.py`: fuso, enums nativos × modelos, unicidade, mapa das FKs e seus efeitos) (decidido; mesmo mecanismo local e no CI). Ganhos: FKs com `ondelete` hoje não testadas (SQLite não aplica), `DateTime(timezone=True)` perde fuso no SQLite, migrations do Alembic nunca rodam (testes usam `create_all`).
8. **Arquitetura**: ~~`import-linter` no CI validando as regras atuais~~ ✅ (2026-10-15; 3 contratos: camadas, entradas sem adapters com a exceção do probe, domínio sem frameworks — ver `ARCHITECTURE.md` seção 1) → módulo piloto (identificação) em monólito modular (subdomínio por módulo, hexagonal dentro, testes junto, shared kernel mínimo) → resto. **Conceitos e recomendações registrados na seção "Item 8 — conceitos" no topo; fazer depois do plano C.**
9. ~~Use cases declaram seus erros~~ ✅ (`raises`) + catálogo de erros do `ARCHITECTURE.md` (inclui a regra de marcador do `PLANTE_4013`).
10. ~~Propagar Correlation ID para Celery e chamadas HTTP aos provedores~~ ✅ Celery via sinais (cabeçalho `plante_correlation_id`: `correlation_id` já é do Celery). HTTP: decidido **não** mandar o cabeçalho aos provedores (não usam e repassaria a terceiros um ID que pode vir do cliente); os logs dessas chamadas já levam o ID.
11. `ANTIGRAVITY.md`: desmembrar (trechos úteis → todo / `ARCHITECTURE.md`; sem `CLAUDE.md`, decidido em 2026-10-15) e excluir. **Não é versionado**: guardar cópia até confirmar.

**Achado em 2026-10-15:** `/identify` nunca resolvia pelo container (`plant_reference_image_repository` não ligado desde o split do container em 2026-05-19; `Selector` do consenso comparava `"True"` com `"true"`). Corrigido e coberto em `tests/test_container_wiring.py`. Logo, o consenso nunca tinha rodado de ponta a ponta — a nota "consenso ativo em produção pela primeira vez" no Bloco 1 estava errada.

**Crítico — achado em 2026-10-15 (decisão pendente, conversar junto com o item 8):**
13. ~~**Nenhuma escrita no banco é persistida.**~~ ✅ (2026-10-15) `IUnitOfWork` + `SqlAlchemyUnitOfWork` (uma sessão por `async with`, rollback do que não foi confirmado); 20 use cases e o worker de anonimização migrados; eventos depois do commit; `/identify`, `/diagnose` e confirmação de diagnóstico em duas transações (IA/S3 fora). `RepositoriesContainer` removido. Regras no `ARCHITECTURE.md` (seção 1, item 3). Desenhado para virar um UoW por módulo no item 8. Não existe `commit()` em `src`: cada repositório recebe uma sessão nova (`providers.Factory` em `InfraContainer.session`) e nenhuma é confirmada — o `flush` grava numa transação desfeita quando a sessão é descartada. Os repositórios de um mesmo use case nem compartilham transação. Afeta API e workers (a anonimização também nunca persistiu). Os testes de integração não pegam porque fazem `commit` à mão.
    - **Decidido (2026-10-15): Unit of Work no domínio** — porta `IUnitOfWork` (`async with uow:` … `await uow.commit()`) que dá acesso aos repositórios; o use case define a fronteira da transação; eventos publicados só depois do commit (hoje o `/identify` publica antes, e o e-mail de verificação pode sair para usuário não gravado). Mesmo mecanismo na API e nos workers. Rejeitado: sessão por requisição com commit na borda HTTP (transação implícita, não resolve workers nem a ordem dos eventos).
    - Desenhar junto com o item 8: no monólito modular o UoW tende a ser um por módulo.

**Urgente — decidido em 2026-10-15:**
12. ~~**Tipagem estrita: acabar com o `Any`.**~~ ✅ (2026-10-15) `Any` é erro; `object`, `cast` e `# type: ignore` não são usados para silenciar o checker. Regras no `ARCHITECTURE.md` (seção 6).
    - **Regra do Pydantic:** dado que vem de fora do processo entra por Pydantic; dado criado dentro dele é dataclass, tipada sem `Any`.
      - Pydantic (bordas): JSON dos provedores (Kindwise, PlantNet, Gemini, Open-Meteo, Nominatim), claims do JWT, valores do Redis, argumentos das tasks do Celery, schemas dos routers.
      - Dataclass (domínio): entidades, value objects, DTOs dos ports (`IdentificationResult` etc.), eventos e saídas dos use cases. Ajuste em relação à proposta: os DTOs dos ports e os eventos ficaram dataclass — são criados dentro do processo (pelo adapter, depois de validar a resposta com Pydantic) e são tipos do domínio, que segue sem depender do Pydantic. A borda do Celery valida o payload da task no worker.
      - Motivo: o ganho do Pydantic é validar em execução dados não confiáveis; dentro do domínio, com mypy estrito, revalidar é custo e o modo lax converte valores em silêncio.
    - Feito: IDs `NewType` sobre `UUID`, gerados pelo domínio (sem `id=None`); `JsonValue`/`JsonObject` para JSON opaco; `Literal` nas origens e `StrEnum` nos enums de texto; saídas dos use cases tipadas e routers com `from_domain` (sem `Schema(**dict)`); porta `ITokenService` + `JwtTokenService` (domínio não importa mais `jwt`); `RedisClient` tipado; stubs do `firebase_admin` em `typings/`; `ANN401` no ruff.
    - Rigor do mypy: `disallow_any_explicit`, `disallow_any_decorated` e `disallow_any_expr` globais. **Descoberta:** o `disallow_any_expr` literal é inviável — o typeshed tipa toda corrotina como `Coroutine[Any, Any, T]` e SQLAlchemy ORM, decorators do FastAPI/dependency_injector/Celery, redis-py, google-genai e PyJWT tipam a própria API com `Any`. Solução: lista fechada de módulos de cola no `pyproject.toml`, com o motivo de cada um; neles só expressões/decorators são liberados (`Any` escrito continua proibido). Única exceção a `disallow_any_explicit`: `settings.py` (o `BaseSettings` sintetiza `**values: Any`). Revisitar a lista quando as bibliotecas melhorarem os tipos.
    - Bugs encontrados pela tipagem (todos corrigidos e cobertos por teste):
      - `save` de todo repositório fazia INSERT mesmo para entidade existente (PK duplicada): verificar e-mail, trocar senha, regar, consumir token… quebravam. Agora `merge`.
      - `health_records.user_id` existia no modelo mas não no banco: todo `/diagnose` falhava ao gravar. Migration `d44a59cc8835`. `HealthIdentificationSampleModel` não estava registrado no metadata (o autogenerate geraria `DROP TABLE`).
      - `PlantSpeciesMapper` passava `provider_entity_id` (coluna inexistente; é `kindwise_entity_id`): gravar espécie nova quebrava todo `/identify` de espécie inédita.
      - Respostas montadas com `Schema(**dict)` não batiam com o que os use cases devolviam (UUID em campo `str`, campos ausentes): `/auth/register`, `/identify`, `/garden/{id}/water`, `/profile/subscription/upgrade` e `/profile/achievements` quebravam na resposta. Os testes de rota usavam mocks no formato do schema, não do use case.
      - Gemini sem saída estruturada: o prompt não definia as chaves, o parser caía nos padrões e o diagnóstico complementar dizia vitalidade 1.0 (saudável) para planta doente. Agora `response_schema` com o modelo Pydantic.
      - `/identify` gravava `CONSENSUS` quando só o PlantNet respondeu.
      - `/diagnose/confirm` aceitava diagnóstico de outro usuário (o erro `PLANTE_4017` promete "não pertence ao usuário").
      - `FirebaseAdapter` não implementava a porta (`send`/`send_batch` ausentes); geocodificação usava uma cópia local de `GeocodingError` em vez da do domínio (`PLANTE_5002`).
    - Mudanças visíveis na API: IDs em rota/corpo validados como UUID (inválido → 422, antes 500 no banco); datas serializadas pelo Pydantic (`...Z` em vez de `+00:00`); respostas antes genéricas (`/plants/{id}`, `/garden` POST/DELETE, probes) ganharam schema; `details` do 422 traz só `loc`/`msg`/`type` (sem o valor enviado); `POST /auth/register` devolve `status` (`pending_verification`).
    - Avaliações de saúde pendentes no Redis gravadas antes do deploy (formato antigo) contam como expiradas (410, refazer o diagnóstico).

**Achados para decidir depois (2026-10-15):**
- **Achados do teste de fumaça (2026-10-15, API + worker reais contra Postgres/Redis em contêiner):**
  - ~~`REDIS_ENDPOINT` tinha dois significados~~ ✅ o broker usa `Settings.redis_url` (conferido contra Redis com senha). Histórico: o `celery_config` aceita URL completa (`redis://…`) ou host, o `Settings` só host (monta `redis://{endpoint}:{port}`). Com URL, o broker funciona e o `RedisClient` do worker quebra (OTP não é gravado). Unificar (o `celery_config` ler do `Settings`).
  - ~~Task perdida quando o worker é encerrado~~ ✅ `acks_late` + `reject_on_worker_lost`. Histórico: perdida quando o worker é encerrado durante o retry (ack antecipado, padrão do Celery). Avaliar `acks_late=True` + `task_reject_on_worker_lost=True` na `send_verification_email`.
  - ~~Cada retry gerava um OTP novo~~ ✅ a task reaproveita o código ainda válido. Histórico: cada retry da `send_verification_email` gerava um OTP novo e sobrescreve o anterior. Inofensivo hoje (só repete se o envio falhou), mas o código do e-mail que chegar é o da última tentativa.
  - ~~Aviso do Celery 6~~ ✅ `broker_connection_retry_on_startup = True`.
  - Funcionou: migrations do zero, readiness, cadastro gravado (UoW), task na fila, worker grava o OTP e chama o SES (falha esperada: credenciais falsas), verificação, login, rotas autenticadas, `/identify` com 4013 para não-imagem e 5001 sem chave dos provedores.
- **Fotos dos usuários públicas no S3:** `S3ImageStorage._put_object` grava tudo com `ACL="public-read"` (fotos de identificação/diagnóstico e imagens de referência); quem tiver a URL vê a foto. No código é um ponto só, mas fechar exige servir URLs assinadas (com validade) onde a API devolve imagem: `image_url` do `/identify`, `primary_image_url` do jardim/planta, `image_key` do diagnóstico. Imagens de referência (do Kindwise/PlantNet) podem continuar públicas. Também conferir se o bucket bloqueia ACL pública (padrão da AWS desde 2023 — então o upload pode até falhar em bucket novo).
- ~~**Dataset de treino não era anônimo**~~ ✅ resolvido pelo plano C (2026-10-15). Histórico: (requisito do usuário em 2026-10-15: identificação **e saúde** anonimizadas, a IA treinada não pode ser pessoalizada). O que ainda identifica alguém depois do `anonymize()`:
  - Amostra de saúde: nunca anonimizada (o worker só cobre identificação) e, mesmo com `user_id = NULL`, o `health_record_id` leva ao `health_records` → `user_id` / `user_plant_id`. Precisa cortar o vínculo (cruza com a cascata abaixo).
  - `raw_response` do Kindwise ecoa a entrada: `input.latitude/longitude` (GPS enviado pelo cliente no `/identify`, potencialmente a casa do usuário) e `input.images` (URL da foto no Kindwise). O anonimizador não mexe no JSON.
  - Fotos vão ao S3 como chegaram, com `ACL=public-read`: EXIF intacto (GPS, aparelho, data/hora). A chave não tem `user_id` (bom). Conteúdo da foto (rostos, casa) não se resolve por código — termo de uso/consentimento.
  - Worker de anonimização: até 2026-10-15 nem subia (worker sem app/tasks, corrigido); hoje roda, mas o `save` não persiste (item 13). Precisa de `beat` rodando.
  - Proposta a discutir: remover EXIF no upload (antes de gravar e de mandar aos provedores); anonimização das duas amostras tirando `user_id`, coordenadas e imagens do `raw_response` (e arredondando datas?); amostra de saúde sem FK para `health_records` (copia o que precisa, como já faz). Depende do item 13 para persistir.
- ~~**Cascata das FKs apagava o dataset de saúde**~~ ✅ resolvido pelo plano C (2026-10-15): o treino não tem FK para o usuário; apagar o usuário funciona e preserva o treino (`test_deleting_user_removes_personal_data_and_keeps_training_data`). Histórico: (documentado em `test_postgres_schema.py`, schema não mudado): `health_records.user_plant_id` e `health_identification_samples.health_record_id` são `CASCADE`, então apagar de verdade uma planta apaga os diagnósticos e as amostras de saúde (dataset de treino). As amostras de identificação, ao contrário, sobrevivem ao usuário (`SET NULL`). Hoje plantas e usuários só têm soft delete, mas qualquer limpeza/LGPD com `DELETE` real perde as amostras.
  - Pior: **apagar de verdade um usuário com amostra de saúde falha.** O mesmo `DELETE` faz `SET NULL` em `health_identification_samples.user_id` e apaga o `health_record` pela cascata `users → user_plants → health_records`; o `UPDATE` do `SET NULL` viola a FK `health_record_id`. Ou seja, nenhum usuário que já diagnosticou uma planta pode ser excluído.
  - Não existe limpeza que dispare isso: nenhum fluxo apaga usuário ou planta de verdade (só soft delete). O worker de anonimização (`workers.anonymize_confirmed_samples`) só cobre amostras de **identificação** (tira o `user_id` após 30 dias, sem persistir por causa do item 13); as de saúde nunca são anonimizadas.
  - Decidir: amostras de saúde guardando os dados sem depender do `health_record` (como as de identificação, com `SET NULL`) ou anonimizar antes de apagar.
- ~~**E-mail diferencia maiúsculas**~~ ✅ (2026-10-15) `normalize_email` no domínio (entidade `User` + buscas de cadastro, login e troca de e-mail) e CHECK `ck_users_email_normalized` (migration `db7647f0acac`; banco vazio, sem duplicatas a resolver).
  - Em aberto: o índice único vale também para usuários com soft delete — o e-mail de conta excluída não pode ser reusado (hoje não existe exclusão de conta).
- ~~**Worker do Celery não subia**~~ ✅ (2026-10-15) `celery -A src.workers worker` não achava o app e nenhuma task era registrada (sem `include`). Agora `src.workers` expõe o `celery_app` e o `include` lista os módulos; conferido subindo um worker real (registra as 2 tasks) e coberto em `tests/unit/workers/test_celery_app.py`.
- ~~`RedisClient` tratava erro de uso como retryable~~ ✅ `ResponseError` (ex.: `WRONGTYPE`) → `retryable=False`; o rate limit loga `rate_limit.redis_rejected` (o breaker não abre nesse caso).
- ~~Aviso do starlette no pytest~~ ✅ FastAPI 0.115.0 → 0.115.14 (starlette 0.38.6 → 0.46.2); suíte sem avisos. Atenção: starlette ≥ 0.40 limita campos de formulário que não são arquivo a 1 MB (imagens vêm como arquivo, sem efeito hoje).
- Teste novo: schema das migrations × modelos (`test_migrations_match_models.py`, autogenerate vazio) — teria pegado o `health_records.user_id` ausente.
- **Análise profunda existe pela metade:** `EnrichPlantSpeciesUseCase` não tem rota e descarta o resultado do Gemini; o enriquecimento nutricional (`enrich_nutritional`, `PlantNutritional`) nunca é usado; `has_deep_analysis`/`has_nutritional_analysis`/`is_complete_for_training` nunca eram marcados (saíram com o plano C; se a análise profunda virar sinal do treino, entra na engine de confiança); o `CeleryPublisher` só trata `UserRegisteredEvent` (os demais eventos são descartados).
  - Regra proposta, aceita em princípio mas **a avaliar com calma**: `PlantSpecies.apply_enrichment(result, at)` só preenche campos vazios (Gemini nunca sobrescreve dado dos provedores de identificação); nomes populares unidos, provedores primeiro; `ENRICHED` + `enriched_at` + `enrichment_source=GEMINI`; falha → `FAILED` e sem cobrança.
  - Em aberto: cobrar de novo quem consulta espécie já enriquecida (hoje cobra 2 tokens sempre)? Ligar a feature completa (rota, nutricional, marcações do dataset) ou só corrigir o use case?
- **Testes de contrato:** o usuário roda no PC de casa (onde estão as chaves).
- `FirebaseAdapter` agora implementa a porta, mas nada envia notificação ainda.

~~Próximo passo: item 13 junto com o item 8~~ — superado: ver "Estado e próximos passos" no topo (13 feito; plano C; depois 8).

---

## Bloco 1 — Decidido, em aplicação

- [x] **Validar Correlation ID** (`src/api/middleware/correlation.py`)
  - Aceitar o `X-Correlation-ID` do cliente só se tiver ≤ 128 caracteres de `[A-Za-z0-9._-]`; caso contrário gerar um UUID novo.
  - Não exigir UUID: gateways (AWS, Cloudflare) usam formatos próprios.
  - Motivo: hoje qualquer valor de qualquer tamanho vai para todos os logs; um ID fixo enviado pelo cliente mistura traces.
  - Se o risco aumentar (API aberta a terceiros): sempre gerar o ID e logar o do cliente em `client_request_id`.

- [x] **Use cases declaram seus erros (`raises`)**
  - Cada use case ganha `raises = (PlantNotFoundError, ...)`; routers usam `error_responses(*UseCase.raises)`.
  - Teste que lê o código de cada use case e falha se algum `raise X` não estiver em `raises`.
  - Erros vindos de policies/entidades (`SubscriptionPolicy`, `UserPlant.water()`) continuam sendo listados à mão.
  - Motivo: hoje a lista de erros no Swagger fica no decorator da rota e desatualiza em silêncio.

- [x] **Adapters de IA traduzem os próprios erros**
  - Helper comum para Kindwise e PlantNet: falha de infraestrutura (rede, timeout, 5xx, 429) → `ExternalServiceError(retryable=True)`; 400 do provedor → `InvalidImageError` (`PLANTE_4013`, hoje sem uso).
  - `CircuitBreaker` passa a classificar pelo `retryable` em vez de conhecer `httpx`.
  - Rotas `/identify` e `/diagnose` passam a documentar `PLANTE_4013`.
  - Antes: conferir todos os usos de `ExternalServiceError` (enrich use case, Gemini) para não quebrar a assinatura.
  - Motivo: hoje exceções `httpx` vazam até o use case (viola o ARCHITECTURE.md) e viram 500 genérico com o circuito fechado.
  - Decisão: estado do breaker continua em memória por worker (Redis compartilhado não compensa na escala atual).
  - Feito além do previsto:
    - PlantNet: 404 "Species not found" (imagem que não é planta / sem espécie prevista) → `InvalidImageError`.
    - Resultado vazio de Kindwise/PlantNet → `InvalidImageError` (antes `ValueError` → 500).
    - `ConsensusIdentifier` propaga `InvalidImageError`/`ExternalServiceError` quando os dois provedores falham (antes `ValueError` → 500).
    - 401/403 do provedor logam `provider.misconfigured` (nível error); circuito não abre.
    - Gemini traduz erros do SDK, de rede e JSON inválido; `/diagnose` degrada para só Kindwise se o Gemini falhar, e o token extra só é cobrado quando ele responde.

- [x] **Kindwise: confirmar contrato de erro e `is_plant`**
  - Conferir numa resposta real (`raw_response` no banco ou chamada manual — gasta créditos) o formato de `result.is_plant` e mapear `is_plant.binary == false` → `InvalidImageError`.
  - Confirmar que 400 do Kindwise significa imagem inválida, e não payload nosso malformado (premissa do helper, não documentada publicamente).
  - Motivo: hoje foto que não é planta passa como identificação de baixa confiança.
  - Verificado contra a API real em 2026-10-14 (~3 créditos):
    - `identification` e `health_assessment` devolvem `result.is_plant = {probability, threshold, binary}`. Gato: 201, `binary: false`, sugestão "Magnolia kobus" 6% / doença "Lepidoptera".
    - 400 é ambíguo: `Invalid image data` (bytes que não são imagem) **e** `Images have to be list of base64 strings` (payload nosso sem `images`). `images` com tipo errado → 500 HTML.
  - Regra aplicada: `is_plant.binary == false` explícito → `InvalidImageError` nos dois endpoints (campo ausente segue normal). 400 só vira `InvalidImageError` se o corpo contiver `Invalid image`; outro 400 → `ExternalServiceError(retryable=False)` + log `provider.request_rejected` (error).
  - Pendente: documentar essa regra no `PLANTE_4013` quando o catálogo do `ARCHITECTURE.md` for atualizado (item 9).

- [x] **Security headers** (`src/api/middleware/security.py`)
  - Remover `X-XSS-Protection` (obsoleto; já causou vulnerabilidades em navegadores antigos).
  - Adicionar `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`, exceto em `/docs`, `/docs/oauth2-redirect` e `/redoc` (Swagger carrega scripts de CDN).

- [x] **Erros comuns por router**
  - Mover 422/429/500 de `FastAPI(responses=...)` para o `include_router(...)` de cada router de domínio, para os probes não documentarem 429.

- [x] **Remover `/healthz`**
  - Duplica `/health/liveness`; nenhum cliente, Dockerfile ou compose usa. Remover rota, teste e entrada em `_EXEMPT_PATHS` do rate limit.

- [ ] **Docs e limpeza**
  - [x] Corrigir docstring do `CorrelationIdMiddleware` (não é "tracing distribuído" ainda).
  - [x] Remover `src/domain/exceptions.py` (código morto, sombreado pelo pacote `src/domain/exceptions/`).
  - [x] Atualizar catálogo de erros do `ARCHITECTURE.md`: nomes divergentes do código (4003, 4004, 4007), faltam 4008–4019 e 5002, e o 5001 não cita Gemini nem `retryable`.
  - [ ] `ANTIGRAVITY.md`: existe localmente, mas está no `.gitignore` (linha 56) — decidir se continua só local (descartar o item) ou passa a ser versionado.

- [x] **PlantNet: corrigir formato da requisição e parser** (achado em 2026-10-14)
  - Requisição ia como JSON com base64; a API só aceita `multipart/form-data` → toda chamada voltava 415 (não retryable, só `consensus.failed` em warning). Na prática o `/identify` sempre rodou só com Kindwise e a `ConsensusPolicy` nunca rodou com dados reais.
  - Parser lia `species.taxonomy` (não existe): família/gênero vêm em `species.family/genus.scientificNameWithoutAuthor`, GBIF em `results[0].gbif.id`, `images[].url` é `{o, m, s}`.
  - Verificado contra a API real: Monstera → 200 (85,8%, Araceae); gato → 404 `Species not found`; bytes que não são imagem → 400 `Unsupported file type`; `organs` inválido/desbalanceado → 400 (erro nosso). Regra aplicada igual ao Kindwise: só `Unsupported file type`/`Species not found` viram `InvalidImageError`.
  - Efeito: ~~consenso ativo em produção pela primeira vez~~ (errado: `/identify` não resolvia pelo container até 2026-10-15); cada `/identify` consome também a cota do PlantNet (500/dia no plano atual).

- [x] **Consenso: veto do `is_plant` do Kindwise**
  - Hoje, se o Kindwise rejeita (`is_plant == false`) e o PlantNet devolve uma espécie, vale o PlantNet. No teste real o gato foi rejeitado pelos dois, então é caso de borda (ex.: planta ao fundo da foto).
  - Proposta: `InvalidImageError` do Kindwise por `is_plant` vetar o resultado do PlantNet. Decisão pendente.

- [x] **Consenso descarta `similar_images` e `raw_response`**
  - `ConsensusIdentifier` monta o `IdentificationResult` final sem esses campos. Com `consensus_enabled=True` (padrão), o `IdentifyPlantUseCase` nunca rehospeda imagens de referência (`for similar in result.similar_images` fica vazio) e salva `raw_response={}` em toda amostra.
  - Bug anterior às correções de 2026-10-14 (existe desde que o consenso entrou); a correção do PlantNet não o causou.
  - Ao corrigir: o use case grava `ImageSource.KINDWISE_SIMILAR` fixo — imagens do PlantNet ficariam com origem errada. Decidir de qual provedor vêm as imagens/`raw_response` quando o consenso combina os dois.

---

## Bloco 2 — Endurecimento do Rate Limiter

- [x] **Chave por usuário em vez de IP**
  - Rotas autenticadas contam por `user_id` (claim `sub` do JWT, validado com a mesma lógica de `src/api/deps.py`); IP só para rotas anônimas (`/auth/login`, `/auth/register`, `/auth/verify-email`).
  - Em produção, rodar uvicorn com `--proxy-headers --forwarded-allow-ips`.
  - Decisão: `FORWARDED_ALLOW_IPS` configurável por env (ainda sem deploy definido).
  - Motivo: CGNAT das operadoras móveis brasileiras coloca centenas de usuários no mesmo IP; atrás de load balancer todos aparecem com o IP dele.
  - Feito: access token válido → `user:{sub}`; sem token ou inválido → `ip:{ip}`; as 3 rotas anônimas sempre por IP. `Dockerfile` com `--proxy-headers`; `FORWARDED_ALLOW_IPS` lido pelo próprio uvicorn do ambiente (documentado no `.env.example`).
  - Atenção no deploy: uvicorn 0.30.6 aceita só IPs exatos ou `*` em `FORWARDED_ALLOW_IPS` (sem CIDR). Se o balanceador tiver IP dinâmico, avaliar atualizar o uvicorn ou usar `*` com a API inacessível por fora do balanceador.

- [x] **Backoff quando o Redis cai**
  - Após uma falha, usar só o contador em memória por ~30s antes de tentar o Redis de novo (reaproveitar `CircuitBreaker`).
  - Decisão: adicionar `socket_timeout`/`socket_connect_timeout` curtos (~0,5s) ao cliente Redis — o backoff só cobre falha, não lentidão.
  - Motivo: hoje cada requisição tenta conectar, falha e loga; Redis lento adiciona latência a toda rota e Redis oscilando divide a contagem (limite efetivo dobra).
  - Feito: `CircuitBreaker("Redis", failure_threshold=1, 30s)` no rate limit; erros `RedisError`/`OSError` viram `ExternalServiceError(retryable=True)`; erro inesperado ainda cai para a memória. Timeouts em `Settings` (`REDIS_SOCKET_TIMEOUT_SECONDS`/`REDIS_CONNECT_TIMEOUT_SECONDS`, padrão 0,5s).
  - Atenção: os timeouts valem para o cliente Redis **compartilhado** (tokens, OTP, raw_response do diagnóstico, readiness). Se o Redis de produção for remoto, medir a latência e ajustar por env.

---

## Bloco 3 — CI e testes contra infraestrutura real

- [x] **Pipeline básico (GitHub Actions)**: `ruff`, `mypy`, `pytest`.
  - Antes: zerar os 6 erros de `mypy` por falta de stubs (celery, boto3, aioboto3, firebase_admin) — pacotes `types-*` ou `ignore_missing_imports` por módulo.

- [x] **Redis e Postgres como services do job**
  - Os dois via `testcontainers` (local e CI). Redis com `DockerContainer` genérico: o extra `testcontainers[redis]` exige redis-py ≥ 7 e o projeto usa 5.0.8. Testes em `tests/integration/cache/` (contrato do `RedisClient` e repositórios de OTP, refresh token e avaliação de saúde); o rate limit segue com fake tipado pelo protocolo `WindowCounter`.
  - ~~Marcadores por teste~~: sem marcadores — a fixture pula sem Docker localmente e falha no CI (`_start_or_skip`).
  - ~~Substituir o `_FakeRedis`~~: mantido para a lógica do rate limit; o pipeline `INCR` + `EXPIRE` real está coberto no contrato do `RedisClient`.
  - Decisão: sem `fakeredis` — com Redis real no CI ele não se paga.

- [x] **Trocar SQLite por Postgres nos testes de integração**
  - Hoje rodam em SQLite em memória, que diverge do Postgres em UUID, JSONB, timezone e constraints.
  - Investigar antes de estimar: quanto os testes dependem de comportamento do SQLite.

- [x] **Propagar Correlation ID** para tasks Celery e chamadas HTTP aos provedores.

---

## Fora do código

Contexto do deploy (2026-10-14): primeiro num servidor caseiro (PC antigo), API usada pelo site pessoal com captcha, pouquíssimas requisições por mês; AWS no futuro; possível projeto de pesquisa para a Latinoware.

**Antes de publicar:**
- [ ] **Créditos do Kindwise**: restam 3,5 e a chave tem limite de 10 identificações/mês — o site para após ~3 usos. Comprar créditos (menor pacote ~€50 / 1000) e ajustar o limite no painel. Cada `/identify` e `/diagnose` gasta 1 crédito.
- [ ] **Captcha validado na API** (ao menos em `/auth/register`): captcha só no site não protege a API se o navegador a chama direto. Decidir depois.
- [ ] Restringir `/health/*` no proxy reverso (Caddy/nginx). O código já faz cache de 5s com single-flight.
- [ ] `FORWARDED_ALLOW_IPS` = IP/faixa do proxy reverso (rede Docker) ou do `cloudflared`, se usar Cloudflare Tunnel (recomendado: não abre portas nem expõe o IP de casa).

**Resolvido pelo contexto:**
- [x] Latência do Redis: no mesmo host, timeouts de 0,5s são folgados.
- [x] Cota do PlantNet: 500/dia sobra para o volume esperado.
