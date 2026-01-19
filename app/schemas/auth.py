from datetime import datetime
from pydantic import BaseModel, EmailStr


# ============ REQUEST SCHEMAS ============

class LoginRequest(BaseModel):
    """Used when: User logs in"""
    email: EmailStr
    password: str


class TokenRefresh(BaseModel):
    """Used when: Refreshing access token"""
    refresh_token: str


# ============ RESPONSE SCHEMAS ============

class Token(BaseModel):
    """Returned after successful login"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Decoded JWT payload (internal use)"""
    sub: str  # user_id
    exp: datetime
    type: str  # "access" or "refresh"
