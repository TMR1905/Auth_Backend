from pydantic import BaseModel


# ============ REQUEST SCHEMAS ============

class TwoFactorVerify(BaseModel):
    """Used when: User enters 2FA code during login or setup"""
    code: str


class TwoFactorLoginRequest(BaseModel):
    """Used when: User logs in with 2FA (after password verified)"""
    user_id: str
    code: str


# ============ RESPONSE SCHEMAS ============

class TwoFactorSetupResponse(BaseModel):
    """Returned when user starts 2FA setup"""
    secret: str
    qr_code: str  # Base64 encoded PNG image


class TwoFactorStatusResponse(BaseModel):
    """Returned when checking 2FA status"""
    enabled: bool
