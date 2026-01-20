from pathlib import Path
from app.models import User, OAuthAccount, RefreshToken
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.database import init_db
from app.api.v1.router import router as api_v1_router
from app.core.rate_limit import limiter



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup
    await init_db()
    print("Database tables created!")
    yield


app = FastAPI(lifespan=lifespan)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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