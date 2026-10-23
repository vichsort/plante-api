# shared

## Propósito

Kernel e infraestrutura comuns a todos os módulos. **Não tem regra de negócio**: só tipos puros,
capacidades técnicas (banco, Redis, armazenamento de imagens, imagens, resiliência, clientes HTTP dos provedores) e a
borda HTTP do app inteiro (envelope, erros, middlewares).

Critério para algo entrar aqui: dois ou mais módulos precisam dele **e** nenhum módulo é o dono
natural. Se um módulo é o dono, mora no módulo e os outros importam o barrel dele.

## API pública

Importa-se pela camada, nunca pela raiz nem por dentro dela (`tests/architecture` confere):

| Camada | O que expõe |
| :--- | :--- |
| `src.shared.domain` | `UserId`, `LocalCalendar`, `JsonValue`/`JsonObject`, `DomainEvent`, `PlantEError` e os erros comuns, as portas `IImageStorage`, `IImageSanitizer`, `IDomainPublisher`, `IAccessTokenVerifier` |
| `src.shared.adapters` | `CeleryPublisher`/`TaskCall`/`EventRoute` (eventos → tasks), `Base`/`AuditMixin`/`enum_values` (SQLAlchemy), `build_engine`/`build_session_factory`, `RedisClient`, `LocalImageStorage`/`S3ImageStorage`, `PillowImageSanitizer`, `CircuitBreaker`, `GeminiClient`, `KindwiseClient`, `translate_provider_errors` e o parse de JSON dos provedores |
| `src.shared.api` | `ApiResponse`/`MessageResponse`, `register_exception_handlers`, `error_responses`/`COMMON_ERROR_RESPONSES`, `CurrentUserId`/`install_authentication`, `images_router`/`install_image_links` (the local storage's links), os middlewares (correlation, audit, rate limit, security headers) |
| `src.shared.workers` | `run_async` (task do Celery que chama código assíncrono) e `on_task_loop_end` (limpeza no fim da task, dentro do loop dela) |

O domínio de um módulo só pode usar `src.shared.domain` (o import-linter barra frameworks no
domínio, inclusive por caminho indireto).

## Decisões

- **Images: mechanism here, policy in the module.** Storing and signing links is technical and
  lives in `adapters/storage`; which photo goes out and to whom is each module's rule.
  - **The database keeps keys, never URLs** (`identifications/<user>/<species>/<uuid>.jpg`). The
    client gets a signed link that expires (`IImageStorage.signed_url`, lifetime in
    `IMAGE_LINK_TTL_SECONDS`): an `<img>` cannot send the token, so whoever holds the link sees the
    image until then. Keys are the same in every backend, so moving storage is copying files.
  - **Two backends, chosen in `.env` (`STORAGE_BACKEND`):** `local` (default) keeps the files in a
    folder of the server (`STORAGE_LOCAL_ROOT`) and the API serves them on `/images/<key>`, with
    links signed by HMAC under a key derived from `SECRET_KEY`; `s3` is any S3-compatible storage
    (AWS, or Cloudflare R2 with `S3_ENDPOINT_URL`), private objects and presigned links.
    - The local links last between one and two lifetimes: the deadline moves in steps, so the link
      of a photo stays the same for a while and the browser can cache it. The `/images` route
      follows the general rate limit, by IP.
    - With `local`, the API, the workers and the backups need the same folder (a volume in Docker);
      the training dataset lives there too.
  - **Foto do usuário sob o prefixo dele** (`identifications/{user_id}/…`, inclusive a do
    diagnóstico): a exclusão de conta apaga o prefixo inteiro (`delete_user_images`), sem precisar
    saber quais módulos guardaram chaves. As cópias de treino ficam em `training/…`, sem dono.
    Fotos gravadas antes dessa regra não têm o prefixo e ficam fora da limpeza.
  - **Vira um módulo `media`** quando a imagem ganhar regras próprias: dono, ciclo de vida,
    sessões de upload direto do app (PUT assinado), miniaturas.
  - Já mapeado para o app real: o cache do app precisa de chave estável (o ID da imagem), porque
    o link muda; a lista em cache expira; com CDN, quem assina é a CDN, não o armazenamento.
- **Clientes de provedor finos.** Kindwise e Gemini atendem mais de um módulo. Aqui fica só o
  comum (cliente HTTP, chave, timeout, erro HTTP → `ExternalServiceError`), sem tipos de botânica.
  Cada módulo tem o próprio adapter, com endpoint e parsing dele.
- **Um circuit breaker por provedor**, criado na composição (`src/bootstrap`) e entregue a todos
  os módulos que usam aquele provedor: Kindwise fora abre identificação e saúde juntas.
- **Autenticação das rotas aqui, emissão de tokens no identity.** Toda rota autenticada, de
  qualquer módulo, usa `CurrentUserId`; um módulo não pode importar a borda HTTP de outro, então a
  dependência não pode morar no identity. Ela pede o dono do token à porta `IAccessTokenVerifier`,
  que quem emite os tokens implementa; a composição liga os dois (`install_authentication`, com o
  provider do container, para um override nos testes valer aqui também). Por isso
  `UnauthorizedError` também é do kernel.
- **Rate limit sem conhecer o identity.** O middleware recebe um decodificador que devolve o dono
  do token ou `None` (token inválido conta pelo IP): o `IAccessTokenVerifier.owner_of`, ligado em
  `src/main.py`. As rotas sensíveis e anônimas ainda são uma lista de caminhos no middleware; se
  crescer, passa a vir de cada módulo na composição.
- **`UserNotFoundError` mora com o `UserId`.** Todo módulo guarda IDs de usuário, e um módulo base
  (ex.: quota) pode descobrir que a conta não existe sem poder importar o identity.
- **`LocalCalendar` (que dia é para o usuário)** serve à rega (garden) e à cota diária
  (quota); o fuso vem de `LOCAL_TIMEZONE`.
- **Eventos viram tasks pelas rotas dos módulos.** O `CeleryPublisher` não conhece evento nenhum:
  cada módulo com tasks entrega uma `EventRoute` (evento → `TaskCall`, pelo nome da task), e a
  composição as junta. Evento sem rota só é logado.
- **Probes ficam na composição** (`src/bootstrap/probes.py`), não aqui: o readiness precisa do
  container (engine e Redis montados).

## Erros

Base: `PlantEError`, abstrata (sem código; instanciá-la direto é bug e vira 500). Todo erro do
projeto herda dela; o handler HTTP (`register_exception_handlers`) a transforma no envelope. Erro
sem detalhes sai com `details: null`.

| Código | Erro | HTTP | Quando |
| :--- | :--- | :---: | :--- |
| `PLANTE_4000_VALIDATION_ERROR` | `InvalidRequestError` | 422 | Corpo/query/path inválidos (montado pelo handler; só `loc`/`msg`/`type` nos detalhes), ou outro 4xx do próprio framework (ex.: corpo ilegível). |
| `PLANTE_4001_INVALID_IMAGE` | `InvalidImageError` | 400 | Imagem ilegível, formato não aceito (só JPEG/PNG/WebP/HEIC) ou acima de 60 MP. Foto legível sem planta é o `PLANTE_4401_NOT_A_PLANT`, do identification. |
| `PLANTE_4002_METHOD_NOT_ALLOWED` | `MethodNotAllowedError` | 405 | A rota existe, mas não com esse método (montado pelo handler; mantém o header `Allow`). |
| `PLANTE_4010_UNAUTHORIZED` | `UnauthorizedError` | 401 | Token ausente, inválido ou expirado. Só isso: o app renova o token ou pede novo login. |
| `PLANTE_4030_ROUTE_NOT_FOUND` | `RouteNotFoundError` | 404 | Nenhuma rota com esse caminho (montado pelo handler). |
| `PLANTE_4031_USER_NOT_FOUND` | `UserNotFoundError` | 404 | O usuário do token não tem conta. |
| `PLANTE_4032_IMAGE_NOT_FOUND` | `ImageNotFoundError` | 404 | Link de imagem inválido, expirado ou para uma foto que não existe mais (sem dizer qual), ou o armazenamento não é o local. |
| `PLANTE_4050_RATE_LIMIT_EXCEEDED` | `RateLimitExceededError` | 429 | Limite por minuto: 60 nas rotas gerais, 15 nas de IA e auth. Anônimas contam por IP; autenticadas, por usuário. |
| `PLANTE_5000_INTERNAL_ERROR` | `InternalError` | 500 | Falha inesperada (montado pelo handler; detalhes só no log). |
| `PLANTE_5010_EXTERNAL_SERVICE_ERROR` | `ExternalServiceError` | 502 | Provedor externo falhou (Kindwise, PlantNet, Gemini, AWS). |
| `PLANTE_5030_SERVICE_UNAVAILABLE` | `ServiceUnavailableError` | 503 | Infra nossa sem responder: readiness (Postgres ou Redis) ou Redis inalcançável numa rota. Conta para o circuit breaker. Comando recusado pelo Redis (ex.: `WRONGTYPE`) é bug nosso: 5000. |

**`ExternalServiceError.retryable`:**
- `True`: falha transitória (rede, timeout, 5xx, 429). Só essas contam para abrir o circuit breaker.
- `False`: o provedor rejeitou a requisição (payload nosso inválido, 401/403 de chave mal
  configurada, logado como `provider.misconfigured`). Não abre o circuito.
- Circuito aberto também responde `PLANTE_5010`.
- Resposta fora do contrato do provedor é falha dele: `retryable=False` + log `provider.unexpected_response`.

**Envelope** de toda resposta, sucesso ou erro:

```json
{
  "ok": false,
  "data": null,
  "error": { "code": "PLANTE_4050_RATE_LIMIT_EXCEEDED", "message": "...", "details": { "limit": 15 } },
  "meta": { "timestamp": "2026-10-16T16:35:00Z" }
}
```
