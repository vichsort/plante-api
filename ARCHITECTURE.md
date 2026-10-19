# ARCHITECTURE.md — Regras de arquitetura (PlantE API)

> **PlantE API** é uma plataforma *open source* de identificação e gestão botânica para cultivo
> residencial. Este documento diz **o que todo código precisa seguir**. O que é específico de um
> módulo (propósito, decisões, erros) fica no `README.md` do módulo. O kernel comum está em
> `src/shared/README.md`.
>
> Quase toda regra daqui quebra o CI quando violada: import-linter, mypy, ruff e
> `tests/architecture/`. As que dependem de revisão estão marcadas como tal.

---

## 1. Princípios

1. **Monólito modular, hexagonal por dentro.** Um subdomínio por módulo (`src/modules/<nome>`).
   Dentro de cada módulo, o domínio é puro e as dependências apontam para dentro: entradas (rotas,
   tasks) → use cases → entidades/portas ← adapters. O que é muito parecido fica junto: módulo não
   é um use case.
2. **Domínio puro.** Só biblioteca padrão, `typing_extensions` e `structlog`. Nada de FastAPI,
   SQLAlchemy, Pydantic, Celery, redis, httpx, PyJWT… (import-linter, inclusive por caminho indireto).
3. **Injeção de dependências** (`dependency-injector`). Use case não instancia repositório nem
   serviço: recebe portas. Cada módulo tem o próprio `container.py`; a composição
   (`src/bootstrap`) junta os containers. Adapters não leem `Settings`: recebem valores primitivos
   do container.
4. **Transação pelo use case (Unit of Work).** O use case recebe um `uow` e trabalha dentro de
   `async with self.uow as uow:`. Nada é gravado sem `await uow.commit()`, e o que não foi
   confirmado é desfeito ao sair do bloco (inclusive com exceção).
   - Eventos, e-mail, OTP e Redis acontecem **depois** do commit.
   - Chamadas lentas (IA, S3) ficam **fora** da transação: leitura curta → serviços externos →
     escrita curta, relendo o que precisa (ex.: saldo de tokens).
   - Um Postgres só, então uma transação física: o UoW de cada módulo é uma visão da mesma sessão,
     e a fronteira entre módulos é garantida pelo import-linter, não por sessões separadas.
   - Chamada de outro módulo que precisa de consistência forte (cobrar tokens, gravar a amostra
     de treino) vai por um `service` dele, **na mesma transação** de quem chama. Evento assíncrono
     só para o que pode chegar depois.
5. **A balança.** Nem tudo vira porta ou abstração. Cada escolha pesa utilidade real, conforto,
   preguiça e boa prática. A exceção deliberada é documentada no README do módulo, ou no
   `pyproject.toml` quando é exceção de linter (*revisão*).
6. **Extensão por adapter.** Integração nova (provedor de IA, e-mail…) entra como adapter de uma
   porta existente, sem mexer na regra de negócio.

---

## 2. Layout

### 2.1. Geral

```
src/
  main.py          # cria o app
  bootstrap/       # composição: settings, container raiz, Celery, app FastAPI, probes
  shared/          # kernel e infraestrutura comuns (src/shared/README.md)
  modules/<nome>/  # um subdomínio por pasta
  workers/         # entrada do Celery (`celery -A src.workers`): só expõe o `celery_app`
tests/
  testbed/         # fixtures de infraestrutura (Postgres, Redis, ambiente), plugin do pytest
  e2e/             # caracterização ponta a ponta, atravessa módulos
  architecture/    # as regras deste documento como testes
  integration/ unit/ test_*.py  # da composição: schema e migrations, container, app, worker
migrations/        # Alembic, único (um Postgres)
```

Módulos e kernel **nunca** importam a composição (`main`, `bootstrap`, `workers`): ela é quem os
monta (import-linter).

### 2.2. Template de módulo

```
src/modules/<nome>/
  __init__.py        # barrel: a API pública do módulo (só domínio: tipos, services, portas, eventos)
  README.md          # seções fixas, ver 2.3
  container.py       # DI do módulo
  domain/
    entities/  value_objects/  policies/  ports/
    services/        # chamados por outros módulos, dentro da transação de quem chama (sem commit)
    use_cases/       # entradas com transação própria (commit)
    events.py  exceptions.py
  adapters/
    persistence/{models,mappers,repositories}/
    <tecnologia>/    # kindwise/, gemini/, redis/…
  api/   router.py  schemas.py  [deps.py]
  workers/ tasks.py
  tests/ unit/  integration/  [contract/]  fakes.py  [conftest.py]
```

- Nomes fixos. Pasta só existe se tiver conteúdo (nada de pasta só com `__init__.py`).
  Conferido por `tests/architecture` (`test_module_layout`).
- `shared` segue o mesmo esqueleto, com uma diferença: a borda HTTP dele é a do app inteiro.
- Os fakes de uma porta ficam no módulo dono da porta, em `tests/fakes.py`, e os testes de quem usa
  a porta os importam de lá (regra 3 de imports).
- Todo pacote em `src` precisa de `__init__.py` (o import-linter não enxerga namespace packages;
  `tests/test_packages.py` confere).

### 2.3. README de módulo

Seções obrigatórias (`tests/architecture` confere):

```markdown
# <nome>

## Propósito
O que o módulo resolve e o que fica de fora.

## API pública
O que o barrel expõe e para quem (services, portas, tipos, eventos).

## Decisões
Escolhas específicas do módulo e o motivo, inclusive as exceções deliberadas (a balança).

## Erros
Todo código de erro que o módulo define, com quando ocorre e o status HTTP.
```

---

## 3. Imports

Conferidos pelo import-linter (`[tool.importlinter]` no `pyproject.toml`, `uv run lint-imports`)
e por `tests/architecture` (`test_imports_go_through_barrels`).

1. **Entre módulos, só a raiz:** `from src.modules.garden import GardenPlant`, nunca
   `src.modules.garden.domain…`. A raiz exporta só o domínio público, para o domínio de quem
   importa continuar puro.
2. **A composição** (`src/main.py`, `src/bootstrap`) também pode importar `container`, `api` e
   `workers` de cada módulo, para montar o app. Nunca `adapters` ou `domain` direto.
   Os **testes** de um módulo também podem importar os dublês publicados por outro
   (`src.modules.<x>.tests.fakes`), e nada mais do interior dele.
3. **O shared se importa pela camada:** `src.shared.domain`, `src.shared.adapters`,
   `src.shared.api`, `src.shared.workers`. O domínio de um módulo só usa `src.shared.domain`. Os
   testes também podem importar os dublês das portas do shared (`src.shared.tests.fakes`).
4. **Ninguém importa o barrel de um pacote que o contém** (ex.: um arquivo de
   `src/modules/garden/domain/` importando `src.modules.garden`). Em Python isso gera import
   circular e carrega tudo antes da hora. Dentro do módulo, importa-se o arquivo ou o barrel de uma
   pasta irmã.
5. **Barrels exportam explicitamente** (`__all__` ou reexport com `as`): o mypy estrito
   (`no_implicit_reexport`) recusa o resto.
6. **Camadas:**
   - **Globais:** `main` → `workers` → `bootstrap` → `modules` → `shared`. Uma camada só importa
     as de baixo.
   - **Dentro de cada módulo:** `tests` → `api` | `workers` → `container` → `adapters` → `domain`.
   - **Dentro do shared:** `tests` → `api` | `workers` → `adapters` → `domain`.
   - As entradas (`api`, `workers`) recebem adapters pelo container, nunca importando-os direto.
7. **Dependências entre módulos** (sem ciclo; contrato "Dependências entre módulos" do
   import-linter):

   ```
   health · achievements
   garden
   identification
   identity · subscription · catalog · training      (base: não importam módulo)
   ```

---

## 4. Erros

- Todo erro de domínio herda de `PlantEError` (`src.shared.domain`) e tem `code`
  (`PLANTE_<NNNN>_<NOME>`) e `status_code`. O handler HTTP do shared o transforma no envelope
  `ApiResponse`.
- **Código único no projeto inteiro**, e todo código que um módulo define aparece em `## Erros`
  do README dele (`tests/architecture`). Subclasse que não redefine `code` herda o da base (ex.:
  `NotAPlantError` usa o de `InvalidImageError`).
- Os códigos atuais são contrato da API e **não mudam ao migrar**. Faixas numéricas por módulo
  foram descartadas por isso.
- **Aposentados (não reutilizar):** `PLANTE_4015_SAMPLE_NOT_FOUND`,
  `PLANTE_4018_RAW_RESPONSE_EXPIRED`, `PLANTE_5002_GEOCODING_ERROR`.
- **Erros declarados por use case:** cada use case lista em `raises` os erros que pode lançar:
  - os `raise` do próprio arquivo são conferidos por teste;
  - os que vêm de policies, entidades e portas são listados à mão (*revisão*).

  As rotas documentam o OpenAPI com `error_responses(*UseCase.raises)`.

---

## 5. Workers (Celery)

- Task que chama código assíncrono usa `@run_async` (`src.shared.workers`).
- **Task de módulo** (`workers/tasks.py`): `@shared_task`, e as dependências entram por wiring
  (`Provide[<Modulo>Container.x]` com `@inject`), porque o módulo não pode importar o container raiz.
  - A composição liga os containers às tasks em `src/bootstrap/wiring.py` (o mesmo `wire` do app).
  - O worker carrega `src/bootstrap/worker.py`, que zera os singletons depois de cada task: cada
    task roda num event loop novo, e o cliente do Redis fica preso ao loop em que nasceu.
  - Os testes passam as dependências direto na chamada.
- **Evento → task:** cada módulo entrega uma `EventRoute` (em `workers`), e a composição as passa
  ao `CeleryPublisher` (`src.shared.adapters`). O publisher manda pelo nome da task, sem importar o
  worker.
- Payload da task entra por um modelo Pydantic (vem da fila, de fora do processo).
- Subir: `celery -A src.workers worker` e, para as agendadas, `celery -A src.workers beat`
  (**uma instância só**). Todo módulo com tasks entra no `include` do `celery_app`
  (`src/bootstrap/celery_config.py`); um teste confere que as tasks publicadas e agendadas estão
  registradas.

---

## 6. Tipagem estrita

`Any` é proibido: nem escrito (`disallow_any_explicit` + ruff `ANN401`), nem vindo de expressões
ou decorators (`disallow_any_expr`, `disallow_any_decorated`). `cast` e `# type: ignore` não
silenciam o checker.

- **Pydantic nas bordas, dataclasses no domínio.**
  - Pydantic: o que vem de fora do processo (respostas dos provedores, claims do JWT, valores do
    Redis, argumentos de tasks, corpo das requisições).
  - Dataclass tipada: o que nasce dentro dele (entidades, value objects, DTOs das portas, saídas
    dos use cases).
  - O domínio não depende do Pydantic.
- **IDs:** um `NewType` sobre `UUID` por entidade, gerado pelo domínio na criação (nunca pelo
  banco). `UserId` fica no kernel; os outros, no módulo dono.
- **JSON opaco:** `JsonValue` / `JsonObject` (`src.shared.domain`). Quem precisa ler um campo usa
  um modelo próprio na borda, não navega no JSON.
- **Origens** são `Literal`; enums de texto são `StrEnum`.
- **Cola de biblioteca:** módulos que falam com bibliotecas tipadas com `Any` (SQLAlchemy ORM,
  decorators do FastAPI/dependency_injector/Celery, redis-py, google-genai, PyJWT) ficam numa lista
  fechada no `pyproject.toml`, com o motivo de cada um.
  - Neles só a checagem de expressões/decorators é desligada (`Any` escrito continua proibido).
  - Cada biblioteca fica isolada no menor módulo possível (ex.: `RedisClient`, `GeminiClient`,
    `JwtTokenService`).
- Testes (`src/**/tests`, `tests/`) ficam fora do mypy estrito; o ruff vale para todos.

---

## 7. Testes

- **Onde:**
  - os de um módulo, em `src/modules/<nome>/tests/` (fora da imagem Docker);
  - os que atravessam módulos, em `tests/e2e/`;
  - as regras de arquitetura, em `tests/architecture/`.
- **Testbed** (`tests/testbed`, carregado pelo `conftest.py` da raiz):
  - Postgres real com o schema das migrations e transação desfeita por teste; Redis real, limpo
    por teste;
  - variáveis de ambiente falsas;
  - sem Docker, esses testes são pulados localmente e falham no CI.
- **AAA obrigatório** nos testes dos módulos e nos ponta a ponta:
  - `# Arrange` (opcional), `# Act` e `# Assert`, nessa ordem;
  - `# Act & Assert` vale pelos dois (ex.: `pytest.raises`);
  - conferido por `tests/architecture`;
  - os da composição em `tests/` (fora do `e2e/`) ainda ficam de fora.
- **Prefira infraestrutura real** (testcontainers) a mock quando o comportamento depende de banco
  ou Redis. Todo bug corrigido ganha um teste que falharia antes (*revisão*).
- **Contrato com os provedores reais:** fora do padrão e do CI, porque gasta créditos
  (`uv run pytest -m contract`).

---

## 8. Checklist (o CI roda os quatro em todo push e PR)

```bash
uv run pytest                          # inclui tests/architecture; Postgres e Redis via Docker
uv run ruff check src tests migrations conftest.py
uv run mypy
uv run lint-imports
```
