from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.config import settings
from app import models  # This loads all models



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables for dev/test (SQLite)
    if "sqlite" in settings.DATABASE_URL:
        await init_db()
    yield
    # Shutdown: cleanup if needed

app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
