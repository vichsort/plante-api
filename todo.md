# TODO — PlantE API

O que falta fazer. O histórico está no git e nos PRs; as regras, no `ARCHITECTURE.md` e nos
READMEs dos módulos.

## Próxima release (`v0.2.0`, `develop` → `main`)

- [ ] **Refazer os erros.** Revisão feita em 2026-10-19. Tudo abaixo está aprovado e espera o
  sinal verde para virar código, exceto o que está marcado como aberto. Os erros são refeitos do
  zero: não há contrato antes da `v0.2.0` (nenhum cliente externo). A partir dela, código
  publicado não muda nem é reaproveitado.

  **Bugs**
  - [ ] País/estado inválido devolve 500: `country`/`state` são `str` livre em
    `src/modules/identity/api/schemas.py` (register e update location), e o `ValueError` do
    `UserLocation` não é tratado. Validar no schema (`min_length`/`max_length`) para sair 422.
    Teste: `POST /auth/register` com `country: "BRA"` → 422.
  - [ ] 404 de rota e 405 saem como `{"detail": ...}`, fora do envelope. Adicionar handler do
    `StarletteHTTPException` em `src/shared/api/exception_handlers.py` (4030 rota não encontrada,
    4002 método não permitido). Teste: rota inexistente → envelope com `ok: false`.

  **Esquema novo: `PLANTE_ABCD_NAME`**
  - A: `4` = erro do cliente, `5` = erro do servidor ou de serviço externo.
  - B: módulo. `0` shared, `1` identity, `2` subscription, `3` catalog, `4` identification,
    `5` garden, `6` health, `7` achievements, `8` training.
  - C (`4xxx`): `0` requisição inválida (400/405/422), `1` autenticação (401), `2` permissão/plano
    (403), `3` não encontrado (404), `4` conflito/estado (409), `5` limite (429).
  - C (`5xxx`): `0` interno (500), `1` provedor externo (502), `3` indisponível (503).
  - D: sequencial (0–9) dentro de cada par (B, C), na ordem de criação, sem significado próprio.
  - Teste de arquitetura: A bate com a família do HTTP, C com o status da tabela, B com o módulo
    onde a classe mora; código único.
  - Teste de arquitetura: todo erro definido aparece no `raises` de algum use case ou é lançado
    por algum adapter (pega erro morto, como o 4014 hoje).

  **Tabela nova**

  | Novo | Hoje | Erro | HTTP |
  | :--- | :--- | :--- | :---: |
  | 4000 | 4220 | validação do corpo/query/path | 422 |
  | 4001 | 4013 | imagem inválida (`InvalidImageError`) | 400 |
  | 4002 | — | método não permitido (novo) | 405 |
  | 4010 | 4006 | token ausente, inválido ou expirado (só isso) | 401 |
  | 4030 | — | rota não encontrada (novo) | 404 |
  | 4031 | 4002 | usuário não encontrado | 404 |
  | 4050 | 4029 | rate limit | 429 |
  | 4100 | 4008 | senha fraca | 400 |
  | 4101 | 4003 | código OTP inválido ou expirado | 400 |
  | 4102 | 4007 | senha errada (login **e** troca de senha/e-mail) | 400 |
  | 4120 | 4006 | e-mail não verificado no login (novo erro, hoje sai como 401) | 403 |
  | 4140 | 4004 | e-mail em uso | 409 |
  | 4220 | 4019 | funcionalidade do Pro | 403 |
  | 4221 | 4005 | limite de plantas do free | 403 |
  | 4330 | 4014 | espécie não encontrada (ver ponto aberto) | 404 |
  | 4400 | 4011 | confiança baixa | 422 |
  | 4401 | 4013 | não é uma planta (`NotAPlantError`, ganha código próprio) | 422 |
  | 4430 | 4012 | identificação não encontrada | 404 |
  | 4530 | 4001 | planta não encontrada | 404 |
  | 4540 | 4016 | ainda não é hora de regar | 409 (hoje 400) |
  | 4630 | 4017 | registro de saúde não encontrado | 404 |
  | 5000 | 5000 | erro interno | 500 |
  | 5010 | 5001 | provedor externo (Kindwise, PlantNet, Gemini, AWS) | 502 |
  | 5030 | 5003 | serviço indisponível: readiness e Redis fora do ar (Redis é infra nossa) | 503 |

  Sai: `PLANTE_4000_DOMAIN_ERROR` da base `PlantEError` (a base não chega ao cliente; ver se
  ganha código ou fica abstrata). Sai a lista de aposentados (4015, 4018, 5002) da
  `ARCHITECTURE.md`.

  **Ajustes**
  - [ ] Login: senha errada vira 4102 (hoje `UnauthorizedError`, em
    `src/modules/identity/domain/use_cases/login.py:46`); e-mail não verificado vira 4120
    (linha 49). Motivo: 4010 significa só "renove o token ou entre de novo"; o app decide pelo
    código, sem ler a mensagem. A troca de senha/e-mail continua 400: a sessão é válida, só a senha
    digitada está errada (401 faria o app deslogar).
  - [ ] 4221 (limite de plantas): `details` com `current_count` e `max_allowed` como inteiros e
    distintos (hoje os dois recebem `str(limit)`).
  - [ ] 4220 (Pro): tirar o preço "R$ 6,99/month" da mensagem (não existe preço fixo).
  - [ ] Erros de digitação: "hydrataded" (regar cedo), "unindentifiable" (imagem inválida).
  - [ ] **Tudo em inglês**, sem exceção, cliente ou servidor: mensagens do handler (4220/5000
    hoje em português, em `exception_handlers.py` e `openapi.py`), docstrings das exceções (viram
    a mensagem padrão e o resumo no OpenAPI) e os `ValueError` em português de
    `src/modules/identity/domain/value_objects/verification_code.py`.

  **Documentação**
  - [ ] Recomendação (confirmar): a regra (formato `ABCD`, tabela do C, código único, `raises`
    por use case) fica na `ARCHITECTURE.md` §4, curta e sem nenhum código listado, porque é regra
    que todo módulo segue, como camadas e workers. O catálogo fica nos READMEs: erros comuns e os do
    handler no `src/shared/README.md`; os de cada módulo no README dele. A docstring do
    `PlantEError` resume o esquema em três linhas e aponta para a regra. Alternativa (se preferir a
    ARCHITECTURE sem erros): a regra vai para o README do shared, com uma linha de índice na
    ARCHITECTURE.
  - [ ] Atualizar a seção `## Erros` de todos os READMEs com os códigos novos.

  **Aberto (discutir depois)**
  - [ ] **`SpeciesNotFoundError` (4330, hoje 4014) nunca sai.** O catalog não tem rota;
    `/identify` cria a espécie e o detalhe da planta tolera espécie ausente. O certo seria sair
    quando o provedor não encontra a planta, mas o PlantNet sempre devolve algo, mesmo sem
    certeza; falta ver o Kindwise. Decidir quando sai e cobrir com teste.
- [ ] Ok do usuário de que está "redondinho". Só então a release.

## Validar com as chaves reais

- [ ] Testes de contrato: `uv run --env-file .env pytest -m contract` (~2 créditos do Kindwise).
- [ ] Um `/identify` real com o S3 de verdade. Risco: bucket novo bloqueia `ACL="public-read"` por
  padrão, e o upload (inclusive a cópia de treino) pode falhar.
- A `main` (`v0.1.x`) lê a chave do Kindwise de `PLANT_ID_API_KEY`; a `develop` lê
  `KINDWISE_API_KEY` (com `PLANT_ID_API_KEY` como nome antigo).

## Até a `v1.0.0`

- [ ] **Inglês em tudo:** comentários, docstrings, READMEs, `ARCHITECTURE.md`. Aos poucos, sem
  mutirão: texto novo já sai em inglês; o existente migra quando fizer sentido.

## Produto e dados

- [ ] **Fotos privadas no S3:** hoje tudo é gravado com `ACL="public-read"` e quem tem a URL vê a
  foto. Servir URLs assinadas (com validade) onde a API devolve imagem (`image_url` do `/identify`,
  `primary_image_url` do jardim, foto do diagnóstico); imagens de referência podem continuar
  públicas. Política por módulo, mecanismo no shared (critério do módulo `media` no
  `src/shared/README.md`). Junto: a foto do diagnóstico é gravada com `upload_identification_image`
  (prefixo das fotos de identificação; ver o README do health).
- [ ] **Engine de confiança do rótulo:** rascunho no README do training.
- [ ] **Análise profunda pela metade:** `ISpeciesEnricher.enrich_nutritional`, `PlantNutritional` e
  `IHealthEnricher.analyze_disease` existem sem uso. Decidir se a feature entra (rota, use case no
  módulo da tela, cobrança) ou se sai.
  - Regra proposta, a avaliar: `PlantSpecies.apply_enrichment` só preenche campos vazios (o Gemini
    nunca sobrescreve dado dos provedores); nomes populares unidos, provedores primeiro; falha →
    `FAILED` e sem cobrança.
- [ ] **Conquistas:** regra de concessão (consumir os eventos que hoje ninguém consome).
- [ ] **HEIC (iPhone):** hoje rejeitado com 4013; avaliar `pillow-heif`.
- [ ] **Motivo da exclusão da planta** como sinal de treino.
- [ ] **Geocodificação reversa** (estado a partir do GPS; hoje vem do perfil). Sem serviço que mande
  o GPS do usuário a terceiros (ver "Descartado").
- [ ] **Reuso do e-mail de conta excluída:** o índice único vale também com soft delete (hoje não
  existe exclusão de conta).
- [ ] **Sessões por aparelho:** hoje um refresh por usuário (login em outro aparelho derruba o
  primeiro). Quando houver app.

## Antes de publicar

Contexto: primeiro num servidor caseiro (PC antigo), API usada pelo site pessoal com captcha,
pouquíssimas requisições por mês; AWS no futuro; possível projeto de pesquisa para a Latinoware.

- [ ] **Créditos do Kindwise:** a chave tem limite de 10 identificações por mês. Comprar créditos
  (menor pacote ~€50 / 1000) e ajustar o limite no painel. Cada `/identify` e `/diagnose` gasta 1.
- [ ] **Captcha validado na API** (ao menos em `/auth/register`): captcha só no site não protege a
  API se o navegador a chama direto.
- [ ] Restringir `/health/*` no proxy reverso (Caddy/nginx).
- [ ] `FORWARDED_ALLOW_IPS` = IP/faixa do proxy reverso ou do `cloudflared`, se usar Cloudflare
  Tunnel (recomendado: não abre portas nem expõe o IP de casa).

## Descartado (não propor de novo sem motivo novo)

Código recuperável pelo commit `6f2b3e3` (pai: `8107105`).

- **Firebase (FCM), push:** futuro distante. Se voltar, é um módulo `notifications` (tokens por
  aparelho, opt-in) reagindo a eventos do garden.
- **OpenMeteo, clima para o Gemini:** utilidade duvidosa e difícil de medir.
- **Nominatim, geocodificação:** manda o GPS do usuário a terceiros, e o servidor público limita a
  1 req/s.
