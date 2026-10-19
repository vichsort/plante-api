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
  unsure` + sugestão) ou implícitos (`added_to_garden` e `removed_*`, o motivo da exclusão). A confiança
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
  - testes dos adapters de provedor (`identification/tests/unit/test_kindwise_identifier.py`,
    `test_plantnet_identifier.py` e `health/tests/unit/test_kindwise_analyzer.py`): respostas reais
    dos provedores não vazam dados ecoados para os sinais;
  - `tests/integration/test_user_and_training_flow.py` (raiz): depois de apagar o usuário, o treino
    fica inteiro e sem nada que aponte para ele.

### Engine de confiança do rótulo (desenho acordado em 2026-10-19, ainda não implementada)

No espírito da `ConsensusPolicy`: uma classe pura, versionada e testada, em que os testes mostram a
decisão de cada caso. Decide, para cada amostra, uma **faixa**, o **rótulo** e os **motivos**.

**Princípio:** dado certo, mesmo fraco, é ganho; dado com rótulo errado é perda (ensina o modelo a
errar). As faixas separam o que se sabe que está certo do que não se sabe. Na dúvida, mais garantia
e menos volume.

**Escopo da v1:** só identificação. Saúde depois (pouco sinal hoje, um provedor só).

**Faixas:** `confiável`, `revisar`, `fora` e `referência` (imagens de referência dos provedores e
de fontes abertas, abaixo). O treino começa com `confiável` + `referência`.

**Regras da v1**, em ordem (a primeira que casar decide):

| # | Regra | Faixa |
| :---: | :--- | :--- |
| 1 | Algum provedor diz que provavelmente não é planta (`is_plant` < 0,5) | fora |
| 2 | O último voto de rótulo do usuário é `wrong` ou `removed_misidentified` | fora (a sugestão dele vira **candidata**) |
| 3 | Espécie com menos de N amostras no lote (N = 10 para começar, parâmetro) | fora (cauda longa) |
| 4 | Acordo exato, sem `low_confidence`, sem voto negativo | confiável |
| 5 | Último voto `correct` **e** confiança ≥ 85% | confiável |
| 6 | Todo o resto (consenso parcial, um provedor só, `low_confidence`, `unsure`) | revisar |

- **Vale o voto mais recente:** só o dono vota, então votos em conflito são a mesma pessoa mudando
  de ideia.
- **Sinal implícito nunca promove sozinho** (jardim, cuidado continuado, motivo da exclusão).
- **`correct` não salva confiança baixa:** o usuário não é botânico; a confirmação dele só confirma
  o que os provedores já achavam provável.
- Identificação abaixo de 60% e foto vetada como "não é planta" nunca chegam ao dataset (a
  requisição falha antes de gravar).

**Imagens de referência como dado rotulado** (ideia do usuário):

- Cada imagem que um provedor manda junto de uma sugestão é um exemplo **da espécie daquela
  sugestão**, independentemente de a sugestão bater com a foto do usuário. Foto borrada de gramínea
  com sugestões suculenta, palmeira, girassol e maracujá: a gramínea não entra; as quatro imagens
  entram, cada uma com o rótulo da própria sugestão.
- Não são 100% certas (observações validadas pela comunidade, bases dos provedores), mas são muito
  mais confiáveis que um palpite: ficam na faixa `referência` e só saem por licença ou duplicata.
- **Licença e autor por imagem são obrigatórios.** Sem licença registrada, a imagem não entra. Hoje
  o adapter lê o `license_name` e o descarta, e só as imagens da sugestão vencedora são guardadas
  (baixadas dentro da requisição). O plano: guardar URL + licença de cada imagem, por sugestão, nos
  sinais da amostra (barato); baixar só na exportação, sem custo no `/identify`; remover duplicatas
  (a mesma imagem volta em muitas consultas).
- **Termos de uso a verificar antes de qualquer código:** se o Kindwise e o PlantNet permitem usar
  as imagens similares para treinar outro modelo.
- **Fontes abertas como adapters** (longo prazo): uma porta de fonte de referência, um adapter por
  fonte, cada imagem com licença e autor. Candidatas a confirmar: GBIF (licença por imagem),
  iNaturalist (observações de grau de pesquisa, dados abertos), Pl@ntNet-300K (dataset de pesquisa
  publicado pelo PlantNet). O dataset nasce juridicamente limpo, e o relatório mostra a origem de
  cada imagem.
- **Estratégia:** as referências são a base (o catálogo limpo, o que os provedores já sabem); o
  diferencial é a foto real do usuário, no quintal, sob a luz do Brasil. Começa mais fraco que eles
  e ganha especificidade com o tempo; o que eles não são é aberto, simples e brasileiro.

**Termos de uso (lidos em 2026-10-19; leitura nossa, não parecer jurídico):**

| Fonte | O que diz | Para o dataset |
| :--- | :--- | :--- |
| Kindwise ([T&C da API, v3](https://www.kindwise.com/terms-and-conditions)) | 17.3.3: o cliente não pode usar os serviços para desenvolver sistema próprio "baseado no mesmo princípio". 17.4.1: fotos do `Output` (as similares) só para processar a resposta para o usuário final. 17.6: outros parâmetros de licença podem ser combinados. | Imagens similares **não** entram. Usar as respostas como rótulo para treinar um identificador próprio também esbarra no 17.3.3: **perguntar antes** (support@FlowerChecker.com). |
| Kindwise, sobre as fotos que mandamos | 17.5: licença não exclusiva e irrevogável para usar as fotos dos nossos usuários em machine learning e redistribuí-las em CC BY-SA 4.0 (rostos borrados); 20.3/20.4: dados de terceiros anonimizados após 6 meses. | Entra no texto do consentimento: a foto vai para provedores que podem usá-la. |
| PlantNet ([imagens da API](https://my.plantnet.org/doc/references/using-images), [contrato da API v4](https://my.plantnet.org/documents/agreement_PlantNet_API_english_v4.pdf)) | Imagens em CC BY, CC BY-SA ou domínio público; uso interno e comercial permitido com fonte e autor; outro uso exige consentimento escrito do CIRAD. Nada explícito sobre treino. | Candidatas, com licença e autor por imagem. ShareAlike em modelo treinado é zona cinzenta: **perguntar** (contact@plantnet-project.org). Conferir também os termos do plano gratuito que usamos. |
| [Pl@ntNet-300K v2](https://zenodo.org/records/10419064) | Dataset de pesquisa; licença por imagem: CC BY-SA, CC BY-NC ou CC BY-NC-SA. | Bom para pesquisa (Latinoware); as NC não servem se o modelo for para o produto pago. |
| [iNaturalist (AWS Open Data)](https://registry.opendata.aws/inaturalist-open-data) | Licença por foto (CC0 a CC BY-NC). Os termos do iNaturalist proíbem treinar IA **para fins comerciais** com os dados deles. | Só para pesquisa não comercial, salvo autorização. |
| [GBIF](https://techdocs.gbif.org/en/data-publishing/multimedia-publishing) | Licença por mídia, definida por quem publica (CC0, CC BY, CC BY-NC…). | Filtrar CC0 e CC BY por imagem. |

**Atenção:** o PlantE tem plano pago (Pro). Se o modelo treinado servir ao produto pago, o uso é
comercial: fica de fora tudo que for NC e os dados do iNaturalist. Um modelo só de pesquisa
(Latinoware) tem mais fontes à disposição.

**Exportação:** o banco guarda a matéria-prima (amostras e eventos); o treino precisa de uma pasta
pronta. A exportação é um comando (não uma rota), rodado quando for treinar, que:

1. lê amostras e eventos;
2. passa cada um pela engine (faixa, rótulo, motivos);
3. copia as imagens que entram (baixando as de referência, com dedupe);
4. grava `samples.jsonl` (foto → rótulo, faixa, motivos, versão das regras) e a lista das fotos;
5. gera o relatório do lote (*datasheet*): contagens por faixa, motivo, espécie, estado e fonte,
   mais as candidatas sugeridas pelos usuários.

Cada exportação é versionada: regra nova gera um lote novo do mesmo estoque, sem migrar dados.

**Proteções:**

- a amostra bruta nunca é apagada: errar a mão só muda a faixa dela no próximo lote;
- um conjunto de referência revisado à mão (~200 amostras) mede a precisão da faixa `confiável`
  antes de afrouxar qualquer regra (formato da revisão: planilha ou página, a decidir);
- o estado sai da grade de ~11 km com uma base offline de limites estaduais (sem geocodificação
  em tempo de execução nem serviço de terceiros); sem GPS, vale o estado do perfil.

A análise profunda (Gemini), se virar sinal, entra aqui também.

## Erros

O módulo não define erros próprios. Gravação fora de uma transação é erro de programação
(`RuntimeError`), não erro de API.
