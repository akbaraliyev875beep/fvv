"""
Tez Yordam EMS — FastAPI Dependencies

get_current_user, role_required, rate limiter va boshqa dependency'lar.
"""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole

logger = logging.getLogger("tez_yordam.deps")

# ── Bearer token sxemasi ─────────────────────────────────────────
security_scheme = HTTPBearer(auto_error=False)

# ── Rate Limiter ─────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security_scheme)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Joriy foydalanuvchini JWT token orqali aniqlash.

    Token yo'q yoki noto'g'ri bo'lsa — 401 xatolik.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentifikatsiya talab qilinadi",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token noto'g'ri yoki muddati tugagan",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Token turi tekshirish
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token talab qilinadi",
        )

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token'da foydalanuvchi ma'lumoti topilmadi",
        )

    import uuid
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Noto'g'ri foydalanuvchi ID formati",
        )

    # DB'dan foydalanuvchini olish
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi topilmadi",
        )

    return user


def role_required(*roles: UserRole):
    """
    Ruxsat berilgan rollarni tekshiruvchi dependency.

    Foydalanish:
        @router.get("/admin-only", dependencies=[Depends(role_required(UserRole.ADMIN))])
    """

    async def _check_role(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bu amal uchun quyidagi rollardan biri kerak: {', '.join(r.value for r in roles)}",
            )
        return current_user

    return _check_role


# ── Tip annotatsiyalari (qayta ishlatish uchun) ──────────────────
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
DispatcherUser = Annotated[User, Depends(role_required(UserRole.DISPATCHER, UserRole.ADMIN))]
BrigadeUser = Annotated[User, Depends(role_required(UserRole.BRIGADE))]
AdminUser = Annotated[User, Depends(role_required(UserRole.ADMIN))]
