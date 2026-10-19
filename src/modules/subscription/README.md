# subscription

## Propósito

O plano do usuário (`FREE` ou `PRO`) e a cota diária de tokens que as ações de IA consomem.

- **O plano é demonstrativo:** não há compra, e o upgrade é só uma flag com prazo.
- **A cota é regra de verdade:** ela protege os créditos do Kindwise e do Gemini.

Fica de fora: pagamento, e saber se o usuário existe. Este é um módulo base; quem tem a conta é o
identity, e aqui só existe a FK para `users`.

## API pública

`src.modules.subscription` exporta só domínio:

- **`ITokenWallet`**: a cota, para quem consome IA (identificação, diagnóstico). O uso esperado:
  1. conferir o saldo antes das chamadas caras (`ensure_can_identify`, `ensure_can_diagnose`,
     `can_enrich_diagnosis`);
  2. chamar os provedores fora da transação;
  3. cobrar com `charge`, **dentro da transação de quem chama**, junto com o que foi entregue.

  Chamado fora de uma transação, `charge` levanta erro em vez de perder a cobrança em silêncio.
- **`IGardenQuota`**: o limite de plantas no jardim pelo plano ativo.
- **Tipos:** `Subscription`, `SubscriptionTier`, `FeatureCost`, o evento `SubscriptionUpgradedEvent`
  e os erros abaixo.

A rota `POST /profile/subscription/upgrade` mora em `api/` (sob o prefixo `/profile`, a tela "Meu
perfil" do cliente). A composição monta o módulo por `src.modules.subscription.container`. Os
dublês do wallet e da quota para testes ficam em `tests/fakes.py`, com as regras de verdade.

## Decisões

- **Sem linha = FREE com a cota cheia.** O cadastro não chama este módulo. A linha nasce na primeira
  cobrança ou no upgrade. Por isso uma conta nova não precisa de nada aqui, e a migration
  (`f4c2a8d6e1b3`) só copiou de `users` quem tinha algo diferente do padrão.
- **Vale o plano ativo:** PRO vencido conta como FREE (`Subscription.active_tier`).
- **Cota diária no dia local** (`LocalCalendar`, `LOCAL_TIMEZONE`), sem cron. `tokens_day` guarda o
  dia a que o contador se refere, e a primeira cobrança de um dia novo recomeça do zero.
  - Limites: FREE 3 tokens por dia e 3 plantas; PRO 30 tokens e 50 plantas.
  - Custos: identificar 1; diagnóstico 1, mais 1 pelo complemento do Gemini (só chamado se os 2
    couberem, e só cobrado se entregue); análise profunda 2 (a feature ainda não existe).
  - O upgrade começa com a cota do PRO cheia.
- **A cobrança trava a linha** (`INSERT … ON CONFLICT DO NOTHING` + `SELECT … FOR UPDATE`).
  - Antes, duas identificações simultâneas podiam ler o mesmo saldo, e uma cobrança sobrescrevia a
    outra (o usuário ganhava tokens).
  - O `INSERT` prévio também cobre a primeira cobrança de quem ainda não tem linha.
- **Conta inexistente:** a única FK da tabela é para `users`, então a violação dela vira
  `UserNotFoundError` (do kernel), sem este módulo importar o identity.
- **Conferir o saldo antes, cobrar depois.** O saldo é conferido antes de chamar os provedores (eles
  gastam crédito), e a cobrança é feita na escrita, sobre a linha travada. Duas requisições
  simultâneas podem passar pela conferência com o último token; a segunda cobrança ultrapassa a
  cota em 1. Aceito: travar a linha durante as chamadas à IA prenderia uma conexão por segundos.

## Erros

| Código | Erro | HTTP | Quando |
| :--- | :--- | :---: | :--- |
| `PLANTE_4221_FREE_TIER_PLANT_LIMIT` | `PlantLimitExceededError` | 403 | O plano ativo atingiu o limite de plantas no jardim. |
| `PLANTE_4220_SUBSCRIPTION_REQUIRED` | `SubscriptionRequiredError` | 403 | Tokens do dia esgotados para a ação pedida. |

O upgrade de um usuário sem conta responde `PLANTE_4031_USER_NOT_FOUND` (erro do kernel).
