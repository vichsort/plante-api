# PlantE - Mais que no solo!
Exemplo de retornos

```json
// sucesso
{
  "success": true,
  "data": { ... },
  "error": null
}

// erro
{
  "success": false,
  "data": null,
  "error": {
    "code": "PLANT_NOT_FOUND",
    "message": "Planta 42 não encontrada."
  }
}
```

## Estrutura que teremos...
```markdown
plante-api/
├── src/
│   ├── domain/                         ← zero dependências externas
│   │   ├── entities/
│   │   │   ├── plant.py                # dataclass pura
│   │   │   ├── user_plant.py
│   │   │   ├── health_record.py
│   │   │   └── care_schedule.py
│   │   ├── value_objects/
│   │   │   ├── confidence_score.py     # 0.0–1.0 com validação
│   │   │   ├── subscription_tier.py    # FREE | PRO
│   │   │   └── plant_profile.py
│   │   ├── ports/
│   │   │   ├── plant_identifier.py     # IPlantIdentifier (ABC)
│   │   │   ├── health_analyzer.py      # IHealthAnalyzer
│   │   │   ├── weather_service.py      # IWeatherService
│   │   │   ├── notification_sender.py  # INotificationSender
│   │   │   └── plant_repository.py     # IPlantRepository
│   │   └── use_cases/
│   │       ├── identify_plant.py
│   │       ├── diagnose_health.py
│   │       ├── schedule_care.py
│   │       └── get_plant_details.py
│   │
│   ├── adapters/
│   │   ├── ai/
│   │   │   ├── gemini/
│   │   │   │   ├── adapter.py
│   │   │   │   ├── prompt_builder.py
│   │   │   │   └── response_parser.py
│   │   │   └── consensus_engine.py     # fase 2
│   │   ├── persistence/
│   │   │   ├── sqlalchemy/
│   │   │   │   ├── models.py           # ORM models (≠ entidades)
│   │   │   │   ├── plant_repo.py
│   │   │   │   └── user_repo.py
│   │   │   └── redis/
│   │   │       └── cache_repo.py
│   │   ├── notifications/
│   │   │   └── firebase_adapter.py
│   │   └── weather/
│   │       └── openmeteo_adapter.py    # grátis, sem chave
│   │
│   ├── api/                            ← FastAPI (só HTTP, sem lógica)
│   │   ├── routers/
│   │   │   ├── identify.py             # POST /v1/identify
│   │   │   ├── garden.py               # GET/POST /v1/garden
│   │   │   ├── health.py               # GET /v1/plants/{id}/health
│   │   │   ├── care.py                 # GET /v1/plants/{id}/care
│   │   │   └── auth.py
│   │   ├── schemas/                    # Pydantic request/response
│   │   │   ├── identify_schema.py
│   │   │   └── plant_schema.py
│   │   ├── dependencies.py             # injeção de dependências
│   │   └── middleware.py               # rate limit, logging
│   │
│   ├── workers/                        ← Celery, separado por domínio
│   │   ├── __init__.py
│   │   ├── care_tasks.py               # lembretes de rega/poda
│   │   ├── weather_tasks.py            # sync clima a cada 6h
│   │   └── notification_tasks.py       # envio push
│   │
│   └── infrastructure/
│       ├── database.py                 # engine async SQLAlchemy 2
│       ├── container.py                # dependency injection
│       └── settings.py                 # pydantic-settings
│
├── tests/
│   ├── unit/                           # sem I/O, testa domínio puro
│   ├── integration/                    # testa adapters com DB real
│   └── conftest.py
│
├── migrations/                         # Alembic (mantém do MVP)
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml              # api + worker + beat + db + redis
│   └── docker-compose.prod.yml
├── .env.example
├── pyproject.toml                      # substitui requirements.txt
└── README.md
```