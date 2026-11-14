from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(tags=["Saúde"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(request: Request) -> dict[str, str]:
    with request.app.state.engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
