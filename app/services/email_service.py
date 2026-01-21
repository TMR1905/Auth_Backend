from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.email_token import EmailVerificationToken
from app.models.user import User


# Email configuration
mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

mail_client = FastMail(mail_config)


async def create_verification_token(db: AsyncSession, user: User) -> EmailVerificationToken:
    """Create a new email verification token for a user."""
    # Delete any existing tokens for this user
    await db.execute(
        delete(EmailVerificationToken).where(EmailVerificationToken.user_id == user.id)
    )

    # Create new token
    token = EmailVerificationToken(user_id=user.id)
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def get_verification_token(db: AsyncSession, token: str) -> EmailVerificationToken | None:
    """Get a verification token if it exists and is not expired."""
    result = await db.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.token == token)
    )
    verification_token = result.scalar_one_or_none()

    if not verification_token:
        return None

    # Check if expired (use naive UTC datetime for SQLite compatibility)
    if verification_token.expires_at < datetime.utcnow():
        await db.delete(verification_token)
        await db.commit()
        return None

    return verification_token


async def send_verification_email(email: str, token: str) -> None:
    """Send verification email to user."""
    verification_url = f"{settings.APP_URL}/api/v1/auth/verify-email?token={token}"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Verify Your Email</h2>
        <p>Thank you for registering! Please click the button below to verify your email address:</p>
        <a href="{verification_url}"
           style="display: inline-block; padding: 12px 24px; background-color: #007bff;
                  color: white; text-decoration: none; border-radius: 4px; margin: 20px 0;">
            Verify Email
        </a>
        <p>Or copy and paste this link into your browser:</p>
        <p style="color: #666;">{verification_url}</p>
        <p style="color: #999; font-size: 12px;">This link expires in 24 hours.</p>
    </body>
    </html>
    """

    message = MessageSchema(
        subject="Verify Your Email Address",
        recipients=[email],
        body=html_content,
        subtype=MessageType.html,
    )

    await mail_client.send_message(message)


async def verify_user_email(db: AsyncSession, token: str) -> User | None:
    """Verify a user's email using the token."""
    verification_token = await get_verification_token(db, token)

    if not verification_token:
        return None

    # Get the user
    result = await db.execute(
        select(User).where(User.id == verification_token.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return None

    # Mark user as verified
    user.is_verified = True
    await db.delete(verification_token)
    await db.commit()
    await db.refresh(user)

    return user
