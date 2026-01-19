from app.models import User, OAuthAccount, RefreshToken
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.api.v1.router import router as api_v1_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup
    await init_db()
    print("Database tables created!")
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(api_v1_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}