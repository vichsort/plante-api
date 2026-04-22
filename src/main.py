from fastapi import FastAPI
from src.api.exception_handlers import register_exception_handlers
from src.domain.exceptions import PlantNotFoundError, SubscriptionRequiredError

app = FastAPI(
    title="PlantE API",
    description="Sistema de identificação e gestão botânica",
    version="0.0.0",
)

register_exception_handlers(app)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "plante-api"}

@app.get("/test/not-found")
async def test_not_found():
    raise PlantNotFoundError(plant_id=99)

@app.get("/test/subscription")
async def test_subscription():
    raise SubscriptionRequiredError(feature="Diagnóstico de saúde")