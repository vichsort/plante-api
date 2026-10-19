# identity

## Propósito

Quem é o usuário e como ele entra: cadastro, verificação do e-mail por código, login, sessão (JWT),
troca de e-mail e de senha, e a localização do perfil.

Fica de fora:
- cota de tokens (quota);
- conquistas (achievements);
- a autenticação das rotas dos outros módulos (`CurrentUserId`, no shared). O identity só emite e
  valida os tokens; o kernel pergunta o dono pela porta `IAccessTokenVerifier`, que o
  `JwtTokenService` implementa.

## API pública

`src.modules.identity` exporta só domínio:

- **`IUserDirectory`**: o que os outros módulos podem saber do usuário, sem ver a conta
  (credenciais e e-mail ficam aqui):
  - `region_of(user_id)`: país e estado do perfil (identificação e saúde gravam a região no treino);
  - `ensure_exists(user_id)`: confere que a conta existe.

  Os dois lançam `UserNotFoundError` (do kernel) e leem dentro da transação de quem chama, se houver.
- **Tipos:** `UserLocation` e o evento `UserRegisteredEvent`.

A composição monta o módulo por:
- `container` (`IdentityContainer`);
- `api` (rotas `/auth/*` e `/profile/email|password|location`);
- `workers` (a task `notification.send_verification_email` e a rota evento → task, `route_event`).

O dublê do diretório para testes fica em `tests/fakes.py` (`FakeUserDirectory`), junto com as
portas em memória dos testes daqui.

## Decisões

- **Conta:**
  - Todo usuário nasce `pending_verification`. O cadastro não cria nada em `subscriptions`:
    quem não tem linha lá é FREE.
  - E-mail na forma canônica (`normalize_email`: sem espaços nas pontas, em minúsculas) no
    cadastro, no login e na troca. O banco garante com o CHECK `ck_users_email_normalized`.
  - **Senha forte** (`PasswordPolicy`: 8+ caracteres, uma maiúscula, um número) no cadastro e na troca.
  - **Exclusão definitiva** (`DELETE /profile`, senha no corpo, nunca na query): sem soft delete,
    porque guardar o e-mail de quem pediu para sair é guardar dado pessoal (LGPD).
    - A linha do usuário sai, e o banco leva jardim, identificações, diagnósticos, plano e
      conquistas (`CASCADE`). O treino não aponta para o usuário e fica.
    - O e-mail fica livre na hora: o mesmo endereço cria uma conta nova.
    - O refresh é revogado; o access morre sozinho em minutos (e não acha mais o usuário).
    - As fotos saem depois do commit (`IImageStorage.delete_user_images`, que apaga o prefixo do
      usuário). Se o S3 falhar, a conta sai mesmo assim e o log `account.photos_not_deleted` diz qual
      prefixo limpar à mão.
- **Código de verificação:** `PLA-XXX-C-XXX`, com dígito verificador. Fica 15 minutos no Redis.
  - É enviado pela task do Celery depois do commit do cadastro.
  - Uma nova tentativa da task reaproveita o código ainda válido: o e-mail que chegar tem sempre o
    código aceito.
- **Tokens:** access de 15 minutos, refresh de 30 dias, um refresh por usuário (login novo derruba a
  sessão anterior). Uma sessão só é decisão, não limitação: sessões por aparelho foram descartadas
  (2026-10-19).
  - O refresh **rotaciona**: cada uso devolve um refresh novo. Reusar um refresh já trocado revoga
    a sessão (sinal de roubo). Efeito aceito: um retry do app também derruba.
  - Todo token tem `jti`, então dois emitidos no mesmo segundo nunca são iguais.
  - **O logout revoga só o refresh.** O access é JWT sem estado e vale até expirar (no máximo 15
    minutos). Uma lista de bloqueio no Redis custaria uma consulta por requisição, para cobrir uma
    janela curta.
- **Troca de e-mail** (`PATCH /profile/email`): o endereço novo fica pendente (`pending_email`) e
  recebe um código; o e-mail atual continua entrando.
  - `POST /auth/verify-email` com esse código confirma a troca.
  - Se outra conta tiver ficado com o endereço nesse meio-tempo, 409.
- **Tasks sem o container raiz.** A task recebe as dependências por wiring
  (`Provide[IdentityContainer.x]`); a composição liga o container (`src/bootstrap/wiring.py`), e os
  testes podem passá-las direto.
- **Estado normalizado.** O `UserLocation` põe a sigla em maiúsculas ("sp" → "SP") e o nome com
  inicial maiúscula, menos os conectivos ("rio grande do sul" → "Rio Grande do Sul"). Antes o
  `title()` transformava "SP" em "Sp", inclusive na região que vai ao treino.

## Erros

| Código | Erro | HTTP | Quando |
| :--- | :--- | :---: | :--- |
| `PLANTE_4100_WEAK_PASSWORD` | `WeakPasswordError` | 400 | Senha (cadastro ou troca) fora da `PasswordPolicy`, ou nova senha igual à atual. |
| `PLANTE_4101_INVALID_VERIFICATION_CODE` | `InvalidVerificationCodeError` | 400 | Código fora do formato, expirado ou diferente do enviado. |
| `PLANTE_4102_WRONG_CREDENTIALS` | `InvalidCredentialsError` | 400 | Login com e-mail ou senha errados (mesma resposta para os dois), ou senha atual incorreta ao trocar e-mail ou senha. Não é 401: a sessão continua válida. |
| `PLANTE_4120_EMAIL_NOT_VERIFIED` | `EmailNotVerifiedError` | 403 | Login com a senha certa, mas e-mail ainda não verificado. |
| `PLANTE_4140_EMAIL_ALREADY_IN_USE` | `EmailAlreadyInUseError` | 409 | E-mail já usado por outra conta (cadastro ou troca de e-mail). |

Token ausente, inválido ou expirado (inclusive o refresh) responde `PLANTE_4010_UNAUTHORIZED`, e
conta inexistente responde `PLANTE_4031_USER_NOT_FOUND` (erros do kernel).
