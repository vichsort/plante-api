# TODO — PlantE API

O que falta fazer. O histórico está no git e nos PRs; as regras, no `ARCHITECTURE.md` e nos
READMEs dos módulos.

## Mais urgentes (impedem publicar no site)

Contexto: primeiro num servidor caseiro (PC antigo), API usada pelo site pessoal com captcha,
pouquíssimas requisições por mês; AWS no futuro; possível projeto de pesquisa para a Latinoware.
O site só ganha cadastro depois destes itens; captcha e aceite dos termos mudam o contrato do
`/auth/register`, então vêm antes do site para ele ser feito uma vez só.

- [ ] **Release `v0.2.0`** (`develop` → `main`): ok do usuário de que está "redondinho".
- [ ] **Validar com as chaves reais:**
  - Testes de contrato: `uv run --env-file .env pytest -m contract` (~2 créditos do Kindwise).
  - Um `/identify` real com o armazenamento escolhido, incluindo a cópia de treino e abrir o
    `image_url` devolvido.
  - A `main` (`v0.1.x`) lê a chave do Kindwise de `PLANT_ID_API_KEY`; a `develop` lê
    `KINDWISE_API_KEY` (com `PLANT_ID_API_KEY` como nome antigo).
- [ ] **Armazenamento das fotos: escolher e preparar o braço** (o código está pronto: chaves no
  banco, links assinados, `STORAGE_BACKEND=local|s3`; regras em `src/shared/README.md`).
  - `local` (padrão): definir `STORAGE_LOCAL_ROOT` e `PUBLIC_API_URL` no servidor; em Docker, um
    volume com a pasta compartilhado entre API e workers; backup periódico da pasta (o dataset de
    treino mora lá).
  - R2: ativar no painel da Cloudflare (pede cartão), criar o bucket e a chave de API;
    `STORAGE_BACKEND=s3`, `S3_ENDPOINT_URL`, `AWS_REGION=auto`, `S3_BUCKET` e as chaves.
- [ ] **E-mail: decidir como publicar** (o código está pronto: `EMAIL_VERIFICATION_REQUIRED`,
  `EMAIL_BACKEND=log|smtp|ses`; regras no README do identity).
  - Sem provedor: `EMAIL_VERIFICATION_REQUIRED=false` (a conta nasce verificada; a troca de e-mail
    vale na hora). Riscos aceitos: alguém usar um e-mail que não é seu (resolve à mão) e contas
    descartáveis (o captcha e o teto global seguram).
  - Para ligar a verificação: conta grátis num provedor (Resend 3 mil/mês, Brevo 300/dia), os
    registros DNS (SPF/DKIM) no painel da Cloudflare (o Resend usa um subdomínio próprio e não mexe
    no redirecionamento), `EMAIL_BACKEND=smtp` e `SMTP_*` no `.env`, e então
    `EMAIL_VERIFICATION_REQUIRED=true`.
  - Não existe "esqueci a senha": quem esquecer perde a conta até existir (depende de e-mail).
- [ ] **Captcha: criar o widget** (o código está pronto; regras no README do identity). Painel da
  Cloudflare → Turnstile → Add widget; hostnames = domínio do site + `localhost`; modo Managed.
  Site key no site (o token vai em `captcha_token` no `/auth/register`); secret key em
  `TURNSTILE_SECRET_KEY` no `.env` da API (vazia desliga o captcha).
- [ ] **Termos: escrever o texto e publicar no site** (o código está pronto). Dizer que as fotos
  vão aos provedores de identificação (o Kindwise pode treinar com elas e redistribuí-las em CC
  BY-SA 4.0, T&C 17.5) e viram dataset anônimo. Depois, `TERMS_URL` (e `TERMS_VERSION`, que sobe a
  cada mudança do texto) no `.env`. O site busca `GET /terms` e manda `accepted_terms_version` no
  cadastro. Posso rascunhar o texto para revisão.
- [ ] **Teto diário do serviço:** escolher `PROVIDER_DAILY_LIMIT` (padrão 30 identificações +
  diagnósticos por dia) de acordo com os créditos comprados do Kindwise.
- [ ] **Créditos do Kindwise:** a chave tem limite de 10 identificações por mês. Comprar créditos
  (menor pacote ~€50 / 1000) e ajustar o limite no painel. Cada `/identify` e `/diagnose` gasta 1.
- [ ] Restringir `/health/*` no proxy reverso (Caddy/nginx).
- [ ] `FORWARDED_ALLOW_IPS` = IP/faixa do proxy reverso ou do `cloudflared`, se usar Cloudflare
  Tunnel (recomendado: não abre portas nem expõe o IP de casa).

## Até a `v1.0.0`

- [ ] **Inglês em tudo:** comentários, docstrings, READMEs, `ARCHITECTURE.md`. Aos poucos, sem
  mutirão: texto novo já sai em inglês; o existente migra quando fizer sentido.

## Produto e dados

- [ ] **Engine de confiança do rótulo** (desenho no README do training), nesta ordem:
  1. ~~Pesquisar os termos de uso~~ (feito; resumo no README do training). Falta a resposta dos
     provedores (perguntas, contatos e status em `docs/decisions/2026-10-19-provider-emails.md`): perguntar ao Kindwise (support@FlowerChecker.com) se dá para treinar um modelo
     próprio com as respostas como rótulo (17.3.3) e se há licença de pesquisa (17.6); perguntar ao
     PlantNet (contact@plantnet-project.org) sobre treino com as imagens CC BY-SA e conferir os
     termos do plano gratuito. Decidir também se o modelo é de pesquisa ou do produto pago.
  2. Guardar URL + licença de cada imagem de referência, por sugestão, nos sinais da amostra (hoje
     a licença é descartada e só a sugestão vencedora é guardada).
  3. v1: engine (só identificação, regras da tabela, N = 10), exportação versionada e relatório.
  4. Depois, quando houver ~200 amostras: página de revisão do conjunto de referência (foto, rótulo
     e botões certo/errado/não sei; gera o arquivo de respostas). Serve de demonstração também.
- [ ] **Análise profunda pela metade:** `ISpeciesEnricher.enrich_nutritional`, `PlantNutritional` e
  `IHealthEnricher.analyze_disease` existem sem uso. Decidir se a feature entra (rota, use case no
  módulo da tela, cobrança) ou se sai.
  - Regra proposta, a avaliar: `PlantSpecies.apply_enrichment` só preenche campos vazios (o Gemini
    nunca sobrescreve dado dos provedores); nomes populares unidos, provedores primeiro; falha →
    `FAILED` e sem cobrança.
- [ ] **Conquistas:** regra de concessão (consumir os eventos que hoje ninguém consome).
- [ ] **Imagem de referência `user_confirmed` e a exclusão de conta:** a FK `user_id` é `SET NULL`,
  mas a entidade exige `user_id` nesse tipo; excluir a conta deixaria uma linha que quebra ao ser
  lida. Hoje nada cria `user_confirmed`. Decidir antes de criar (apagar junto, ou anonimizar e
  relaxar a regra).

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
