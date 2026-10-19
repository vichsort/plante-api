# TODO — PlantE API

O que falta fazer. O histórico está no git e nos PRs; as regras, no `ARCHITECTURE.md` e nos
READMEs dos módulos.

## Próxima release (`v0.2.0`, `develop` → `main`)

- [ ] **`SpeciesNotFoundError` (4330) nunca sai.** O catalog não tem rota; `/identify` cria a
  espécie e o detalhe da planta tolera espécie ausente. O certo seria sair quando o provedor não
  encontra a planta, mas o PlantNet sempre devolve algo, mesmo sem certeza; falta ver o Kindwise.
  Decidir quando sai e cobrir com teste; hoje está na lista de pendentes do teste de erro morto
  (`tests/architecture/test_codebase.py`).
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
- [ ] **Engine de confiança do rótulo**, junto com a exportação do dataset e um relatório por
  exportação (rascunho e proteções no README do training). Depois dos itens aprovados abaixo.
- [ ] **Análise profunda pela metade:** `ISpeciesEnricher.enrich_nutritional`, `PlantNutritional` e
  `IHealthEnricher.analyze_disease` existem sem uso. Decidir se a feature entra (rota, use case no
  módulo da tela, cobrança) ou se sai.
  - Regra proposta, a avaliar: `PlantSpecies.apply_enrichment` só preenche campos vazios (o Gemini
    nunca sobrescreve dado dos provedores); nomes populares unidos, provedores primeiro; falha →
    `FAILED` e sem cobrança.
- [ ] **Conquistas:** regra de concessão (consumir os eventos que hoje ninguém consome).
- [ ] **Exclusão de conta** (aprovado): `DELETE /profile` confirmado com a senha; exclusão definitiva
  (as FKs `CASCADE` levam jardim, identificações e diagnósticos), fotos do usuário apagadas do S3,
  treino intacto. O e-mail fica livre na hora (resolve o reuso).

## Antes de publicar

Contexto: primeiro num servidor caseiro (PC antigo), API usada pelo site pessoal com captcha,
pouquíssimas requisições por mês; AWS no futuro; possível projeto de pesquisa para a Latinoware.

- [ ] **Consentimento para o treino (LGPD):** aceite dos termos registrado no cadastro (versão dos
  termos e data), dizendo que as fotos viram dataset anônimo. Sem isso não se coleta dado de treino
  em público.
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
- **Geocodificação reversa em tempo de execução:** o estado só serve ao treino, e o treino já guarda
  a grade de ~11 km; a exportação tira o estado dela com uma base offline de limites estaduais.
- **Sessões por aparelho:** fica uma sessão só (um refresh por usuário; login novo derruba o
  anterior). Ver o README do identity.
