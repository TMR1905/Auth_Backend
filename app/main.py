from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.config import settings
from app import models  # This loads all models
from app.api.v1.router import router as api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables for dev/test (SQLite)
    if "sqlite" in settings.DATABASE_URL:
        await init_db()
    yield
    # Shutdown: cleanup if needed

app = FastAPI(
    title="Auth Backend",
    description="Authentication API with JWT, OAuth2, and 2FA support",
    version="1.0.0",
    lifespan=lifespan,
)

# Include API routes
app.include_router(api_v1_router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
