# TODO — PlantE API

Pendências levantadas na revisão da Fase 6 (middlewares, probes, circuit breaker, OpenAPI).

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
7. ~~**Postgres nos testes de integração** via `testcontainers`~~ ✅ (schema via Alembic; cada teste em transação desfeita no fim; sem Docker pula localmente e falha no CI). Ainda faltam testes que aproveitem os ganhos (FK `ondelete`, fuso) (decidido; mesmo mecanismo local e no CI). Ganhos: FKs com `ondelete` hoje não testadas (SQLite não aplica), `DateTime(timezone=True)` perde fuso no SQLite, migrations do Alembic nunca rodam (testes usam `create_all`).
8. **Arquitetura**: `import-linter` no CI validando as regras atuais → módulo piloto (identificação) em monólito modular (subdomínio por módulo, hexagonal dentro, testes junto, shared kernel mínimo) → resto. Usuário vai detalhar.
9. ~~Use cases declaram seus erros~~ ✅ (`raises`) + catálogo de erros do `ARCHITECTURE.md` (inclui a regra de marcador do `PLANTE_4013`).
10. ~~Propagar Correlation ID para Celery e chamadas HTTP aos provedores~~ ✅ Celery via sinais (cabeçalho `plante_correlation_id`: `correlation_id` já é do Celery). HTTP: decidido **não** mandar o cabeçalho aos provedores (não usam e repassaria a terceiros um ID que pode vir do cliente); os logs dessas chamadas já levam o ID.
11. `ANTIGRAVITY.md`: desmembrar (trechos úteis → todo / `ARCHITECTURE.md` / `CLAUDE.md`) e excluir. **Não é versionado**: guardar cópia até confirmar.

**Achado em 2026-10-15:** `/identify` nunca resolvia pelo container (`plant_reference_image_repository` não ligado desde o split do container em 2026-05-19; `Selector` do consenso comparava `"True"` com `"true"`). Corrigido e coberto em `tests/test_container_wiring.py`. Logo, o consenso nunca tinha rodado de ponta a ponta — a nota "consenso ativo em produção pela primeira vez" no Bloco 1 estava errada.

**Crítico — achado em 2026-10-15 (decisão pendente, conversar junto com o item 8):**
13. **Nenhuma escrita no banco é persistida.** Não existe `commit()` em `src`: cada repositório recebe uma sessão nova (`providers.Factory` em `InfraContainer.session`) e nenhuma é confirmada — o `flush` grava numa transação desfeita quando a sessão é descartada. Os repositórios de um mesmo use case nem compartilham transação. Afeta API e workers (a anonimização também nunca persistiu). Os testes de integração não pegam porque fazem `commit` à mão.
    - Decidir: Unit of Work (port no domínio, sessão por requisição/task, commit no fim do use case ou num middleware). Cruza com o desenho de módulos do item 8.

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
- `EnrichPlantSpeciesUseCase` chama o Gemini e descarta o resultado (salva a espécie sem alterar). Sem rota hoje.
- `FirebaseAdapter` agora implementa a porta, mas nada envia notificação ainda.

Próximo passo: item 13 (persistência/Unit of Work) junto com o item 8 (arquitetura) — discutir com cautela antes.

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

- [ ] **Redis e Postgres como services do job**
  - Postgres resolvido de outro jeito: `testcontainers` (local e CI). Falta o Redis — usar `testcontainers` também, pelo mesmo motivo.
  - Testes dependentes marcados (`@pytest.mark.redis`, `@pytest.mark.postgres`), pulados localmente quando a infra não estiver de pé, obrigatórios no CI.
  - Substituir o `_FakeRedis` de `tests/unit/api/test_middlewares.py` por teste de integração contra Redis real (pipeline `INCR` + `EXPIRE`).
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
