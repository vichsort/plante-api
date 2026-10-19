# achievements

## Propósito

As conquistas (badges) do usuário: o catálogo de medalhas (`AchievementBadge`) e a listagem das que
ele desbloqueou (`GET /profile/achievements`).

Fica de fora, por enquanto: a **regra de concessão**. Ela é da segunda entrega e vai consumir os
eventos que os outros módulos já publicam (`PlantAddedToGardenEvent`, `PlantWateredEvent`,
`StreakBrokenEvent`, `PlantIdentifiedEvent`…), que hoje ninguém consome. Conta e perfil são do
identity; plano e cota de tokens, do subscription.

## API pública

`src.modules.achievements` exporta só domínio: `AchievementBadge` (o catálogo, com código, título,
descrição e ícone de cada medalha, e `from_code`) e `AchievementId`. Ninguém usa o módulo hoje; ele
não usa nenhum outro (topo das dependências, ao lado do health).

A composição monta o módulo por:
- `container` (`AchievementsContainer`);
- `api` (rota `GET /profile/achievements`).

## Decisões

- **Módulo próprio, não parte do identity:** para o identity não virar o módulo-deus do `User`.
- **`/profile` é só prefixo de URL** (a tela "Meu perfil" do app): a rota daqui fica sob ele, com
  a tag `profile`, como as do identity e do subscription. Não existe módulo "profile".
- **Só leitura por enquanto:** o repositório só lista. O antigo `grant_badge` saiu sem uso; a
  concessão (e quem gera o ID da conquista) será desenhada na segunda entrega.
- **`AchievementBadge` fica** como catálogo, mesmo sem uso no código: é a lista de medalhas que a
  regra de concessão vai usar. A rota devolve só o `badge_code` gravado.
- **Hoje:** nada concede conquistas, então a lista sai sempre vazia (o e2e marca isso).
- **List order:** most recently unlocked first, ties broken by `badge_code`, so the order is stable.

## Erros

O módulo não define erros. A rota só devolve os comuns do shared (ex.: `PLANTE_4010_UNAUTHORIZED`
sem token válido); usuário sem conquistas recebe a lista vazia.
