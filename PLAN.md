# Auth System - Implementation Plan

## Project Overview
A complete authentication backend built with FastAPI featuring:
- User registration and login (email/password)
- JWT-based authentication (access + refresh tokens)
- OAuth2 integration (Google, GitHub)
- Optional 2FA (TOTP-based)
- Password reset flow

---

## Phase 1: Foundation & Core Setup

### 1.1 Configuration & Database
- [ ] **config.py** - Pydantic settings with environment variables
  - Database URL
  - JWT secret, algorithm, expiration times
  - OAuth client IDs/secrets
  - 2FA issuer name
- [ ] **database.py** - SQLAlchemy async setup
  - Engine and session factory
  - Base model class
  - `get_db` dependency

### 1.2 Core Security Utilities
- [ ] **core/security.py**
  - Password hashing (bcrypt via passlib)
  - JWT creation and verification
  - Token payload structure
- [ ] **core/two_factor.py**
  - TOTP secret generation
  - QR code URL generation
  - TOTP verification

### 1.3 Database Models
- [ ] **models/user.py** - User model
  ```
  - id (UUID)
  - email (unique)
  - hashed_password (nullable for OAuth-only users)
  - is_active, is_verified
  - two_factor_enabled, two_factor_secret
  - created_at, updated_at
  ```
- [ ] **models/oauth_account.py** - Linked OAuth accounts
  ```
  - id (UUID)
  - user_id (FK)
  - provider (google, github)
  - provider_user_id
  - created_at
  ```
- [ ] **models/refresh_token.py** - Stored refresh tokens
  ```
  - id (UUID)
  - user_id (FK)
  - token_hash
  - expires_at
  - revoked
  - created_at
  ```

---

## Phase 2: Schemas & Basic Auth

### 2.1 Pydantic Schemas
- [ ] **schemas/user.py**
  - UserCreate, UserRead, UserUpdate
- [ ] **schemas/auth.py**
  - LoginRequest, TokenResponse
  - RefreshTokenRequest
  - PasswordResetRequest, PasswordResetConfirm
- [ ] **schemas/two_factor.py**
  - TwoFactorSetupResponse (with QR code)
  - TwoFactorVerifyRequest

### 2.2 User Service
- [ ] **services/user_service.py**
  - create_user()
  - get_user_by_email()
  - get_user_by_id()
  - update_user()
  - verify_user_email()

### 2.3 Auth Service
- [ ] **services/auth_service.py**
  - authenticate_user() - verify credentials
  - create_tokens() - generate access + refresh pair
  - refresh_access_token() - validate refresh, issue new access
  - revoke_refresh_token()
  - initiate_password_reset()
  - complete_password_reset()

---

## Phase 3: API Endpoints - Basic Auth

### 3.1 Dependencies
- [ ] **dependencies.py**
  - get_current_user() - extract user from JWT
  - get_current_active_user() - ensure user is active
  - require_2fa_verified() - for 2FA-protected routes

### 3.2 Auth Routes
- [ ] **api/v1/auth.py**
  - `POST /auth/register` - Create new user
  - `POST /auth/login` - Login, return tokens
  - `POST /auth/refresh` - Refresh access token
  - `POST /auth/logout` - Revoke refresh token
  - `POST /auth/password-reset` - Request password reset
  - `POST /auth/password-reset/confirm` - Complete reset

### 3.3 User Routes
- [ ] **api/v1/users.py**
  - `GET /users/me` - Get current user profile
  - `PATCH /users/me` - Update profile
  - `DELETE /users/me` - Delete account

---

## Phase 4: OAuth2 Integration

### 4.1 OAuth Configuration
- [ ] **core/oauth_providers.py**
  - Google OAuth client setup
  - GitHub OAuth client setup
  - Provider URL constants (auth URL, token URL, user info URL)

### 4.2 OAuth Service
- [ ] **services/oauth_service.py**
  - generate_oauth_url() - Create redirect URL with state
  - exchange_code_for_token() - Handle callback
  - get_oauth_user_info() - Fetch user profile from provider
  - link_oauth_account() - Connect OAuth to existing user
  - create_oauth_user() - Create new user from OAuth

### 4.3 OAuth Routes
- [ ] **api/v1/oauth.py**
  - `GET /oauth/{provider}/authorize` - Redirect to provider
  - `GET /oauth/{provider}/callback` - Handle callback, issue tokens
  - `GET /users/me/oauth-accounts` - List linked accounts
  - `DELETE /users/me/oauth-accounts/{provider}` - Unlink account

---

## Phase 5: Two-Factor Authentication (2FA)

### 5.1 2FA Service
- [ ] **services/two_factor_service.py**
  - generate_2fa_secret() - Create new TOTP secret
  - get_2fa_qr_code() - Generate QR code data URL
  - verify_2fa_code() - Validate TOTP code
  - enable_2fa() - Store secret, mark enabled
  - disable_2fa() - Remove secret, mark disabled

### 5.2 2FA Routes
- [ ] **api/v1/two_factor.py**
  - `POST /auth/2fa/setup` - Generate secret + QR code
  - `POST /auth/2fa/verify` - Verify code and enable 2FA
  - `POST /auth/2fa/disable` - Disable 2FA (requires code)
  - `POST /auth/2fa/validate` - Validate code during login

### 5.3 Login Flow Update
- [ ] Modify login to return `requires_2fa: true` when enabled
- [ ] Issue partial token that only allows 2FA validation
- [ ] Issue full tokens only after 2FA validation

---

## Phase 6: Email Verification & Polish

### 6.1 Email Service (optional but recommended)
- [ ] **services/email_service.py**
  - send_verification_email()
  - send_password_reset_email()
  - (Can stub this initially, implement later)

### 6.2 Verification Routes
- [ ] **api/v1/auth.py** (additions)
  - `POST /auth/verify-email` - Verify email with token
  - `POST /auth/resend-verification` - Resend verification email

---

## Phase 7: Testing & Documentation

### 7.1 Tests
- [ ] **tests/conftest.py** - Fixtures (test DB, test client)
- [ ] **tests/test_auth.py** - Registration, login, refresh, logout
- [ ] **tests/test_oauth.py** - OAuth flows (mocked)
- [ ] **tests/test_2fa.py** - 2FA setup, verify, login with 2FA
- [ ] **tests/test_users.py** - User CRUD

### 7.2 Documentation
- [ ] OpenAPI docs configured (automatic with FastAPI)
- [ ] Example .env.example file
- [ ] README with setup instructions

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Database | PostgreSQL (or SQLite for dev) |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Auth | python-jose (JWT), passlib (bcrypt) |
| OAuth | httpx (for OAuth API calls) |
| 2FA | pyotp |
| Validation | Pydantic v2 |
| Testing | pytest, pytest-asyncio |

---

## Dependencies to Install

```bash
pip install fastapi[standard] sqlalchemy[asyncio] asyncpg alembic
pip install python-jose[cryptography] passlib[bcrypt]
pip install pyotp qrcode[pil]
pip install httpx python-multipart
pip install pytest pytest-asyncio httpx
```

---

## File Structure (Final)

```
app/
├── __init__.py
├── main.py
├── config.py
├── database.py
├── dependencies.py
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       ├── router.py
│       ├── auth.py
│       ├── users.py
│       ├── oauth.py
│       └── two_factor.py
├── core/
│   ├── __init__.py
│   ├── security.py
│   ├── oauth_providers.py
│   └── two_factor.py
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── oauth_account.py
│   └── refresh_token.py
├── schemas/
│   ├── __init__.py
│   ├── user.py
│   ├── auth.py
│   └── two_factor.py
└── services/
    ├── __init__.py
    ├── user_service.py
    ├── auth_service.py
    ├── oauth_service.py
    └── two_factor_service.py
```

---

## Implementation Order (Recommended)

1. **Phase 1** → Get database and core security working
2. **Phase 2** → Schemas and services (no routes yet)
3. **Phase 3** → Basic auth endpoints (register/login/refresh)
4. **Phase 5** → 2FA (before OAuth - simpler to test)
5. **Phase 4** → OAuth integration
6. **Phase 6** → Email verification
7. **Phase 7** → Tests and docs

---

## Notes

- **Refresh tokens stored in DB**: Allows revocation and "logout everywhere"
- **2FA is optional per-user**: Users can enable/disable it
- **OAuth users can set password later**: Allows account recovery
- **Stateless access tokens**: Short-lived (15 min), no DB lookup needed
- **Refresh tokens**: Longer-lived (7 days), stored and validated against DB
