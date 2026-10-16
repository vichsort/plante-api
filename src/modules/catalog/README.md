# catalog

## Propósito

O conhecimento sobre as espécies: taxonomia, nomes populares, dados de cuidado e nutricionais, e as
imagens de referência dos provedores (não as fotos dos usuários). Não sabe nada de usuário.

## API pública

`src.modules.catalog` exporta só domínio:

- **`ISpeciesRegistry`**: o catálogo para os outros módulos. Ele:
  - acha ou cria a espécie que um provedor apontou;
  - grava imagens de referência;
  - busca espécie por nome ou ID.

  As escritas rodam **dentro da transação de quem chama**; as leituras funcionam também fora dela.
- **`ISpeciesEnricher`**: enriquecimento por modelo de linguagem (Gemini), com `EnrichmentResult`
  e `NutritionalEnrichmentResult`.
- **Entidades e tipos:** `PlantSpecies`, `PlantReferenceImage`, `ImageSource`, `PlantNutritional`,
  os enums de espécie e os IDs.

A composição monta o módulo por `src.modules.catalog.container`. O dublê do registry para testes
fica em `tests/fakes.py`.

## Decisões

- **Porta do Gemini dividida (ISP).** O enriquecimento de espécie mora aqui (`adapters/gemini`); o
  complemento do diagnóstico ficou com saúde (`IHealthEnricher`). O cliente HTTP comum está no
  `shared`.
- **Sem JOIN de fora.** O detalhe da planta (jardim) pergunta a espécie ao `ISpeciesRegistry`, em
  vez de fazer JOIN na tabela `plant_species`. São duas consultas em vez de uma, e a tabela continua
  sendo só deste módulo.
- **O enriquecimento cobrado (análise profunda) não mora aqui.** Ele cobra tokens do usuário, e o
  catalog é um módulo base, sem depender de subscription. O use case antigo (sem rota, descartava o
  resultado do Gemini e cobrava mesmo assim) foi removido; quando a feature for desenhada, o use case
  nasce no módulo da tela que a oferece e usa o `ISpeciesEnricher` daqui.

## Erros

| Código | Erro | HTTP | Quando |
| :--- | :--- | :---: | :--- |
| `PLANTE_4014_SPECIES_NOT_FOUND` | `SpeciesNotFoundError` | 404 | Espécie não existe. |
