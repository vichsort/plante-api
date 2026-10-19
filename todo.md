# TODO — PlantE API

O que falta fazer. O histórico está no git e nos PRs; as regras, no `ARCHITECTURE.md` e nos
READMEs dos módulos.

## Próxima release (`v0.2.0`, `develop` → `main`)

- [ ] Revisar os erros (catálogo, códigos, HTTP, quando cada um sai).
- [ ] Ok do usuário de que está "redondinho". Só então a release.

## Validar com as chaves reais

- [ ] Testes de contrato: `uv run --env-file .env pytest -m contract` (~2 créditos do Kindwise).
- [ ] Um `/identify` real com o S3 de verdade. Risco: bucket novo bloqueia `ACL="public-read"` por
  padrão, e o upload (inclusive a cópia de treino) pode falhar.
- A `main` (`v0.1.x`) lê a chave do Kindwise de `PLANT_ID_API_KEY`; a `develop` lê
  `KINDWISE_API_KEY` (com `PLANT_ID_API_KEY` como nome antigo).

## Manutenção

- [ ] CI: `actions/checkout@v4` e `astral-sh/setup-uv@v6` usam Node 20 (descontinuado). Atualizar
  as versões no `.github/workflows/ci.yml`.

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
- [ ] **Conquistas:** regra de concessão (consumir os eventos que hoje ninguém consome) e ordem da
  lista (hoje a consulta não ordena).
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
