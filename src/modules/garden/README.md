# garden

## Propósito

As plantas que o usuário cultiva (o "jardim"): adicionar a partir de uma identificação, listar,
detalhar, regar, acompanhar a sequência de regas no prazo e tirar do jardim.

Fica de fora:
- o que a planta é (identification) e a espécie (catalog, pelo `ISpeciesRegistry`);
- o limite de plantas do plano (subscription, pelo `IGardenQuota`);
- a saúde da planta (health), que lê a planta pelo `IPlantLookup`.

## API pública

`src.modules.garden` exporta só domínio:

- **`IPlantLookup`**: `get_for_user(user_plant_id, user_id)` devolve a `UserPlant` ou lança
  `PlantNotFoundError` (não existe, foi tirada do jardim ou é de outro usuário). Lê dentro da
  transação de quem chama, se houver. O health usa para diagnosticar e listar o histórico.
- **Tipos:** `UserPlant`, `UserPlantId`, `PlantNotFoundError` e os eventos `PlantAddedToGardenEvent`,
  `PlantWateredEvent` e `StreakBrokenEvent` (ninguém consome ainda; conquistas, depois).

A composição monta o módulo por:
- `container` (`GardenContainer`);
- `api` (rotas `/garden` e `/plants/{id}`, num router só);
- `workers` (a task `garden.break_missed_streaks`; o agendamento no beat é da composição).

O dublê do lookup para testes fica em `tests/fakes.py` (`FakePlantLookup`), junto com as portas em
memória e as fábricas de planta dos testes daqui.

## Decisões

- **Uma planta só entra no jardim a partir de uma identificação** (`POST /garden` com
  `identification_id`, lida pelo `IIdentificationLookup`): é aí que a `UserPlant` nasce. Repetir
  com a mesma identificação devolve a planta existente, sem sinal nem evento novo.
  - O limite do plano conta as plantas **ativas** (`count_by_user`; não há contador guardado).
  - Adicionar registra um sinal implícito positivo (`added_to_garden`) na amostra de treino da
    identificação.
- **Rega e sequência** (`CareSchedule`, `Streak`):
  - O vencimento é um **dia do calendário local** (`LocalCalendar`, fuso em `LOCAL_TIMEZONE`,
    padrão `America/Sao_Paulo`), não um instante.
  - A janela vai de 1 dia antes a 1 dia depois do vencimento. Antes dela a rega é recusada
    (`PLANTE_4016`); dentro dela soma 1 à sequência; depois dela é aceita, mas a sequência
    recomeça em 1.
  - Uma rega por dia. A primeira rega (sem vencimento) vale a qualquer dia. Cada rega recalcula o
    vencimento (dia da rega + intervalo de 7 dias).
- **Cron diário** `garden.break_missed_streaks` (beat, 03:00 no fuso local): zera a sequência das
  plantas cuja janela passou inteira e publica `StreakBrokenEvent`. Rodar de novo no mesmo dia não
  quebra nada a mais. A task roda no container do worker (`src/bootstrap/worker.py`), que fecha as
  conexões no fim de cada task.
- **Tirar do jardim é soft delete** e **não é rejeição da identificação** (a planta pode ter
  morrido ou sido doada): identificação e dado de treino não mudam.
- **`/garden` e `/plants` no mesmo módulo e no mesmo router** (`router` inclui os dois, nessa
  ordem): o detalhe da planta é do jardim; o prefixo `/plants` só ficou por contrato da API.
- **Planta de outro usuário é 404, nunca 403** (a API não distingue "não existe" de "não é sua").

## Erros

| Código | Erro | HTTP | Quando |
| :--- | :--- | :---: | :--- |
| `PLANTE_4001_PLANT_NOT_FOUND` | `PlantNotFoundError` | 404 | Planta não existe, foi tirada do jardim ou é de outro usuário. |
| `PLANTE_4016_NOT_READY_FOR_WATERING` | `PlantNotReadyForWateringError` | 400 | Rega antes da janela (vencimento − 1 dia) ou segunda rega no mesmo dia. |

`PLANTE_4012_IDENTIFICATION_NOT_FOUND` (adicionar com identificação inexistente ou de outro usuário)
é do identification; `PLANTE_4005_FREE_TIER_PLANT_LIMIT`, do subscription.

`PLANTE_4009_FORBIDDEN` (`ForbiddenError`) foi aposentado em 2026-10-19 (aprovado pelo usuário): a
rega conferia o dono depois de uma busca que já filtrava por ele, então o 403 documentado nunca
saía. Não reutilizar o número.
