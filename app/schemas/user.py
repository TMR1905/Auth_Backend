from datetime import datetime
from pydantic import BaseModel, EmailStr


# ============ REQUEST SCHEMAS ============

class UserCreate(BaseModel):
    """Used when: User registers"""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Used when: User updates their profile"""
    email: EmailStr | None = None


class PasswordChange(BaseModel):
    """Used when: User changes password"""
    current_password: str
    new_password: str


# ============ RESPONSE SCHEMAS ============

class UserResponse(BaseModel):
    """Basic user info returned to client"""
    id: str
    email: str
    is_active: bool
    is_verified: bool
    two_factor_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserDetailResponse(UserResponse):
    """Extended user info (includes updated_at)"""
    updated_at: datetime
