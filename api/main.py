"""
API CREDANZA — Fase 2 (CODER 4).

Backend FastAPI que se interpone entre la app de escritorio y MySQL.
Se ejecuta desde la RAÍZ del proyecto (para que resuelvan los imports
de models.py, database.py y utils/):

    uvicorn api.main:app --reload
"""

from fastapi import FastAPI

from api import config
from api.routers import auth

config.validar_config()

app = FastAPI(
    title="CREDANZA API",
    description="API de gestión financiera CREDANZA — CODER 4",
    version="0.1.0",
)

app.include_router(auth.router)


@app.get("/health", tags=["infra"])
def health() -> dict:
    """Verificación simple de que la API está viva (sin tocar la base)."""
    return {"status": "ok", "service": "credanza-api"}
