# Respostas reais dos provedores de IA

Capturadas em 2026-10-14 contra as APIs reais (Kindwise `plant.id/api/v3`, PlantNet `v2/identify/all`),
com as imagens públicas do Wikimedia Commons `Monstera_deliciosa3.jpg` e `Cat_November_2010-1a.jpg`.
Removidos: `access_token` e imagem enviada (`input.images`) do Kindwise; hash da imagem (`query.images`) do PlantNet.

| Arquivo | Requisição | Resposta |
|---|---|---|
| `kindwise/identification_monstera.json` | foto de Monstera | 201, `is_plant.binary: true` |
| `kindwise/identification_cat.json` | foto de gato | 201, `is_plant.binary: false`, sugere "Magnolia kobus" 6% |
| `kindwise/health_assessment_cat.json` | foto de gato | 201, `is_plant.binary: false`, sugere "Lepidoptera" |
| `plantnet/identify_monstera.json` | multipart, Monstera | 200, Monstera deliciosa 85,8% |
| `plantnet/identify_cat_404.json` | multipart, gato | 404 `Species not found` |
| `plantnet/identify_invalid_file_400.json` | multipart, bytes aleatórios | 400 `Unsupported file type` |
| `plantnet/identify_json_body_415.json` | JSON com base64 (formato antigo do adapter) | 415 |

Respostas só em texto (não salvas como arquivo):
- Kindwise 400 para bytes que não são imagem: `Invalid image data` (identification e health_assessment).
- Kindwise 400 para payload sem `images`: `Images have to be list of base64 strings`; `images` com tipo errado → 500 HTML.
- PlantNet 400 para `organs` inválido ou desbalanceado com `images` (erro nosso, não da imagem).
