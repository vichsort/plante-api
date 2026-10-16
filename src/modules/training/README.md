# training

## Propósito

O dataset que treina a IA própria do PlantE, montado a partir das identificações e dos diagnósticos,
**sem nenhum dado pessoal**. Requisito inegociável: a IA treinada não pode ser pessoalizada, e
apagar planta ou conta nunca remove dado de treino.

Fica de fora (por enquanto): a engine de confiança do rótulo e a exportação do dataset. Os dois
vão morar aqui.

## API pública

`src.modules.training` exporta só domínio:

- **`ITrainingRecorder`**: a única porta de escrita, para os outros módulos. Grava amostra de
  identificação, amostra de saúde e feedback, sempre **dentro da transação de quem chama**.
  Chamado fora de uma transação, levanta erro em vez de perder a gravação em silêncio.
- **Entidades:** `TrainingIdentificationSample`, `TrainingHealthSample`, `TrainingFeedback`.
- **Alvo do feedback:** `IdentificationLabel` (com sugestão opcional de espécie) e `HealthLabel`.
- **Vocabulário do dataset**, que quem produz o dado importa daqui:
  - sinais dos provedores (`IdentificationSignals`, `HealthSignals`, `SpeciesSuggestion`, `DiseaseSuggestion`);
  - origem (`IdentificationOrigin`, `IdentificationProvider`, `HealthSource`, `HealthSeverity`);
  - `TrainingLocation`, `month_of` e os IDs.

A composição monta o módulo por `src.modules.training.container` (`TrainingContainer.recorder`).
O dublê do recorder para testes fica em `tests/fakes.py`.

## Decisões

- **Separação na gravação.** Cada `/identify` e `/diagnose` grava duas coisas sem ligação de volta:

  | | Lado do usuário (`identifications`, `user_plants`, `health_records`) | Treino (`training_*`) |
  | :--- | :--- | :--- |
  | Dono | `user_id`; tudo sai com o usuário (FKs `CASCADE`) | ninguém; sem `user_id`, sem FK para tabelas do usuário |
  | Foto | a do usuário (`identifications/…`) | cópia própria, chave aleatória em `training/…`, nunca devolvida ao cliente |
  | Tempo | horário exato | só o mês (`period`); as tabelas não usam o `AuditMixin` |
  | Local | — | estado do perfil + grade de ~11 km (GPS com 1 casa decimal), só se o cliente mandou o GPS |
  | Provedor | — | sinais filtrados: sugestões e probabilidades por provedor, `is_plant`, consenso, versão do modelo |

  O vínculo é **de mão única**: o lado do usuário guarda o `training_sample_id`; a amostra nunca
  aponta de volta, e o vínculo some quando o dado do usuário é apagado.
- **O que nunca entra:**
  - `user_id` ou qualquer ID do lado do usuário; GPS exato; URL/chave da foto do usuário; EXIF;
  - do Kindwise: `access_token` (dá acesso à foto na API deles), `input` (ecoa coordenadas, URL da
    foto e data/hora), `custom_id` e horários;
  - do PlantNet: `query` e `remainingIdentificationRequests`.

  Os adapters dos provedores descartam esses campos ao montar os sinais.
- **Feedback é sinal, não confirmação.** Eventos acumulados, explícitos (`correct | wrong |
  unsure` + sugestão) ou implícitos (`added_to_garden`; no futuro, motivo da exclusão). A confiança
  do rótulo **não** é calculada na gravação: a engine vai pesar os sinais brutos na exportação, com
  versão, para os pesos mudarem sem migrar dados.
- **Alvo tipado** (`FeedbackTarget = IdentificationLabel | HealthLabel`):
  - antes eram dois IDs opcionais e um `if` que conferia "exatamente um", e a sugestão de espécie
    era aceita até em feedback de saúde;
  - agora o tipo garante as duas coisas, e um alvo novo é mais um tipo na união;
  - o banco não mudou: o mapper traduz o alvo para as colunas.
- **Sem módulo `feedback` separado, nem use case genérico.** Feedback só existe para o dataset. Já
  conferir que a identificação (ou o diagnóstico) é do usuário é regra do módulo do dado pessoal.
  Cada um deles chama o `ITrainingRecorder` depois de conferir o dono.
- **O vocabulário mora aqui.** Sinais, origem e severidade descrevem o formato das amostras. Se
  ficassem com quem produz o dado, este módulo dependeria de identificação e saúde.
- **Modelo de ameaça:** o alvo é o dataset como artefato (exportado, usado no treino,
  compartilhado). Quem tem acesso a produção sempre pode cruzar dados; isso não justifica
  complexidade extra.
- **Guardas automáticas:**
  - `tests/integration/test_training_tables.py`: colunas numa lista fechada, FKs só entre tabelas de
    treino, nenhum horário exato;
  - `tests/integration/test_recorder.py`: grava só com a transação de quem chama;
  - `tests/unit/adapters/test_provider_fixtures.py` (raiz): respostas reais dos provedores não
    vazam dados ecoados para os sinais;
  - `tests/integration/test_user_and_training_flow.py` (raiz): depois de apagar o usuário, o treino
    fica inteiro e sem nada que aponte para ele.

## Erros

O módulo não define erros próprios. Gravação fora de uma transação é erro de programação
(`RuntimeError`), não erro de API.
