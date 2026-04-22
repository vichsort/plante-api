from fastapi import FastAPI

app = FastAPI(
    title="PlantE API",
    description="Sistema de identificação e gestão botânica",
    version="2.0.0",
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "plante-api"}