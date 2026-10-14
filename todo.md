# TODO — PlantE API

Pendências levantadas na revisão da Fase 6 (middlewares, probes, circuit breaker, OpenAPI).
Ordem decidida: Bloco 1 → Bloco 2 → Bloco 3 (CI e Postgres nos testes por último).
Próximo passo: **Use cases declaram seus erros (`raises`)** — último item de código do Bloco 1.

---

## Bloco 1 — Decidido, em aplicação

- [x] **Validar Correlation ID** (`src/api/middleware/correlation.py`)
  - Aceitar o `X-Correlation-ID` do cliente só se tiver ≤ 128 caracteres de `[A-Za-z0-9._-]`; caso contrário gerar um UUID novo.
  - Não exigir UUID: gateways (AWS, Cloudflare) usam formatos próprios.
  - Motivo: hoje qualquer valor de qualquer tamanho vai para todos os logs; um ID fixo enviado pelo cliente mistura traces.
  - Se o risco aumentar (API aberta a terceiros): sempre gerar o ID e logar o do cliente em `client_request_id`.

- [ ] **Use cases declaram seus erros (`raises`)**
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

- [ ] **Kindwise: confirmar contrato de erro e `is_plant`**
  - Conferir numa resposta real (`raw_response` no banco ou chamada manual — gasta créditos) o formato de `result.is_plant` e mapear `is_plant.binary == false` → `InvalidImageError`.
  - Confirmar que 400 do Kindwise significa imagem inválida, e não payload nosso malformado (premissa do helper, não documentada publicamente).
  - Motivo: hoje foto que não é planta passa como identificação de baixa confiança.

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
  - [ ] Atualizar catálogo de erros do `ARCHITECTURE.md`: nomes divergentes do código (4003, 4004, 4007), faltam 4008–4019 e 5002, e o 5001 não cita Gemini nem `retryable`.
  - [ ] `ANTIGRAVITY.md`: não existe no repositório — localizar ou descartar o item.

---

## Bloco 2 — Endurecimento do Rate Limiter

- [ ] **Chave por usuário em vez de IP**
  - Rotas autenticadas contam por `user_id` (claim `sub` do JWT, validado com a mesma lógica de `src/api/deps.py`); IP só para rotas anônimas (`/auth/login`, `/auth/register`, `/auth/verify-email`).
  - Em produção, rodar uvicorn com `--proxy-headers --forwarded-allow-ips`.
  - Decisão: `FORWARDED_ALLOW_IPS` configurável por env (ainda sem deploy definido).
  - Motivo: CGNAT das operadoras móveis brasileiras coloca centenas de usuários no mesmo IP; atrás de load balancer todos aparecem com o IP dele.

- [ ] **Backoff quando o Redis cai**
  - Após uma falha, usar só o contador em memória por ~30s antes de tentar o Redis de novo (reaproveitar `CircuitBreaker`).
  - Decisão: adicionar `socket_timeout`/`socket_connect_timeout` curtos (~0,5s) ao cliente Redis — o backoff só cobre falha, não lentidão.
  - Motivo: hoje cada requisição tenta conectar, falha e loga; Redis lento adiciona latência a toda rota e Redis oscilando divide a contagem (limite efetivo dobra).

---

## Bloco 3 — CI e testes contra infraestrutura real

- [ ] **Pipeline básico (GitHub Actions)**: `ruff`, `mypy`, `pytest`.
  - Antes: zerar os 6 erros de `mypy` por falta de stubs (celery, boto3, aioboto3, firebase_admin) — pacotes `types-*` ou `ignore_missing_imports` por módulo.

- [ ] **Redis e Postgres como services do job**
  - Testes dependentes marcados (`@pytest.mark.redis`, `@pytest.mark.postgres`), pulados localmente quando a infra não estiver de pé, obrigatórios no CI.
  - Substituir o `_FakeRedis` de `tests/unit/api/test_middlewares.py` por teste de integração contra Redis real (pipeline `INCR` + `EXPIRE`).
  - Decisão: sem `fakeredis` — com Redis real no CI ele não se paga.

- [ ] **Trocar SQLite por Postgres nos testes de integração**
  - Hoje rodam em SQLite em memória, que diverge do Postgres em UUID, JSONB, timezone e constraints.
  - Investigar antes de estimar: quanto os testes dependem de comportamento do SQLite.

- [ ] **Propagar Correlation ID** para tasks Celery e chamadas HTTP aos provedores.

---

## Fora do código

- [ ] Restringir `/health/readiness` à rede interna no deploy (ingress/compose). O código já faz cache de 5s com single-flight.
- [ ] (Opcional) Levar thresholds do circuit breaker (5 falhas / 30s) para `Settings`.
