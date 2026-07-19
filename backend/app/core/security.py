"""
Tez Yordam EMS — Xavfsizlik Moduli

JWT token yaratish/tekshirish, parol hashlash, AES-256 shifrlash,
OneID OAuth2 token almashtirish funksiyalari.
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Parol hashlash ───────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── AES-256 shifrlash (PII maydonlar uchun) ──────────────────────
_fernet_key = base64.urlsafe_b64encode(
    hashlib.sha256(settings.encryption_key.encode()).digest()
)
fernet = Fernet(_fernet_key)


def encrypt_value(value: str) -> str:
    """Matnni AES-256 bilan shifrlash."""
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(encrypted_value: str) -> str:
    """Shifrlangan matnni ochish."""
    return fernet.decrypt(encrypted_value.encode()).decode()


# ── JWT Token'lar ────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Qisqa muddatli access token yaratish (default: 15 daqiqa)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict) -> str:
    """Uzoq muddatli refresh token yaratish (default: 7 kun)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": secrets.token_urlsafe(32),  # Token ID — rotatsiya uchun
    })
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    """JWT tokenni dekodlash va tekshirish."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None


# ── OneID OAuth2 ─────────────────────────────────────────────────
def get_oneid_authorization_url(state: str) -> str:
    """OneID'ga redirect URL yaratish."""
    params = {
        "response_type": "one_code",
        "client_id": settings.oneid_client_id,
        "redirect_uri": settings.oneid_redirect_uri,
        "scope": "openid",
        "state": state,
    }
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{settings.oneid_authorization_url}?{query_string}"


async def exchange_oneid_code(code: str) -> dict | None:
    """
    OneID authorization code'ni token va foydalanuvchi ma'lumotlariga almashtirish.

    Qaytarish: {"pin": "...", "full_name": "...", "phone": "...", ...} yoki None
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Token olish
            token_response = await client.post(
                settings.oneid_token_url,
                data={
                    "grant_type": "one_authorization_code",
                    "client_id": settings.oneid_client_id,
                    "client_secret": settings.oneid_client_secret,
                    "code": code,
                    "redirect_uri": settings.oneid_redirect_uri,
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()

            access_token = token_data.get("access_token")
            if not access_token:
                return None

            # Foydalanuvchi ma'lumotlarini olish
            userinfo_response = await client.get(
                settings.oneid_userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_response.raise_for_status()
            return userinfo_response.json()

        except httpx.HTTPError:
            return None


def generate_state_token() -> str:
    """CSRF himoyasi uchun tasodifiy state token yaratish."""
    return secrets.token_urlsafe(32)
