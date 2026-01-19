import pyotp
import qrcode
import io
import base64


def generate_totp_secret() -> str:
    """
    Generate a random secret key for TOTP.

    This secret is stored in user's database record and shared
    with their authenticator app (Google Authenticator, Authy, etc.)

    Returns: 32-character base32 string like "JBSWY3DPEHPK3PXP"
    """
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = "AuthBackend") -> str:
    """
    Generate the URI that authenticator apps scan.

    Args:
        secret: The user's TOTP secret
        email: User's email (shows in authenticator app)
        issuer: Your app name (shows in authenticator app)

    Returns: "otpauth://totp/AuthBackend:user@email.com?secret=XXX&issuer=AuthBackend"
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def generate_qr_code(uri: str) -> str:
    """
    Generate a QR code image as base64 string.

    User scans this QR code with their authenticator app.
    Returns base64 so you can embed in HTML: <img src="data:image/png;base64,{result}">

    Args:
        uri: The TOTP URI from get_totp_uri()

    Returns: Base64 encoded PNG image
    """
    # Create QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)

    # Convert to image
    img = qr.make_image(fill_color="black", back_color="white")

    # Save to bytes buffer
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")  # type: ignore[call-arg]
    buffer.seek(0)

    # Convert to base64
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def verify_totp(secret: str, code: str) -> bool:
    """
    Verify a TOTP code from user's authenticator app.

    Args:
        secret: User's TOTP secret (from database)
        code: 6-digit code user entered (from their app)

    Returns: True if code is valid, False otherwise

    Note: Codes are valid for 30 seconds, but we allow 1 window
    before/after for clock drift (valid_window=1)
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def get_current_totp(secret: str) -> str:
    """
    Get the current TOTP code (for testing purposes).

    In production, you wouldn't use this - the user provides
    the code from their authenticator app.

    Args:
        secret: User's TOTP secret

    Returns: Current 6-digit code like "123456"
    """
    totp = pyotp.TOTP(secret)
    return totp.now()
