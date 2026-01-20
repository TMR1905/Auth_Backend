from slowapi import Limiter
from slowapi.util import get_remote_address
from redis.asyncio import Redis

from app.config import settings


# Create Redis connection for rate limiting storage
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

# Create limiter with Redis backend
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
)


# Rate limit strings for different endpoint types
RATE_LIMIT_LOGIN = "5/minute"  # 5 login attempts per minute
RATE_LIMIT_REGISTER = "3/minute"  # 3 registrations per minute
RATE_LIMIT_2FA = "5/minute"  # 5 2FA attempts per minute
RATE_LIMIT_REFRESH = "10/minute"  # 10 token refreshes per minute
