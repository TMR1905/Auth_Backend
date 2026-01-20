from pathlib import Path
from app.models import User, OAuthAccount, RefreshToken
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# Serve static files
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    """Serve the test UI"""
    return FileResponse(static_dir / "index.html")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}