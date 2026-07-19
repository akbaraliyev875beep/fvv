"""
Tez Yordam EMS — Xabarnoma Xizmati

SMS (Eskiz.uz) va Push (Firebase Cloud Messaging) orqali xabarnomalar.
"""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("tez_yordam.notification")

# ── SMS Token keshi ──────────────────────────────────────────────
_sms_token: str | None = None


async def _get_eskiz_token() -> str | None:
    """Eskiz.uz API uchun autentifikatsiya token olish."""
    global _sms_token
    if _sms_token:
        return _sms_token

    if not settings.eskiz_email or not settings.eskiz_password:
        logger.warning("⚠️ Eskiz.uz ma'lumotlari sozlanmagan")
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.eskiz_base_url}/auth/login",
                data={
                    "email": settings.eskiz_email,
                    "password": settings.eskiz_password,
                },
            )
            response.raise_for_status()
            data = response.json()
            _sms_token = data.get("data", {}).get("token")
            return _sms_token
    except httpx.HTTPError as e:
        logger.error(f"❌ Eskiz auth xatolik: {e}")
        return None


async def send_sms(phone: str, message: str) -> bool:
    """
    SMS xabar yuborish (Eskiz.uz orqali).

    Args:
        phone: Telefon raqami (998XXXXXXXXX formatda)
        message: Xabar matni

    Returns:
        True — yuborildi, False — xatolik
    """
    token = await _get_eskiz_token()
    if token is None:
        logger.warning(f"⚠️ SMS yuborilmadi (token yo'q): {phone[:7]}***")
        return False

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.eskiz_base_url}/message/sms/send",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "mobile_phone": phone,
                    "message": message,
                    "from": "4546",
                },
            )
            response.raise_for_status()
            logger.info(f"✅ SMS yuborildi: {phone[:7]}***")
            return True
    except httpx.HTTPError as e:
        logger.error(f"❌ SMS yuborish xatoligi: {e}")
        return False


async def send_push_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> bool:
    """
    Push notification yuborish (Firebase Cloud Messaging).

    Args:
        fcm_token: Firebase device token
        title: Xabarnoma sarlavhasi
        body: Xabarnoma matni
        data: Qo'shimcha ma'lumot (dict)

    Returns:
        True — yuborildi, False — xatolik
    """
    if not settings.fcm_server_key:
        logger.warning("⚠️ FCM server key sozlanmagan")
        return False

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://fcm.googleapis.com/fcm/send",
                headers={
                    "Authorization": f"key={settings.fcm_server_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "to": fcm_token,
                    "notification": {
                        "title": title,
                        "body": body,
                    },
                    "data": data or {},
                },
            )
            response.raise_for_status()
            logger.info(f"✅ Push yuborildi: {fcm_token[:20]}...")
            return True
    except httpx.HTTPError as e:
        logger.error(f"❌ Push yuborish xatoligi: {e}")
        return False


async def notify_patient_brigade_assigned(
    phone: str,
    brigade_vehicle: str,
) -> None:
    """Bemorga brigada tayinlanganini xabar berish."""
    message = (
        f"🚑 Tez Yordam: Sizga brigada tayinlandi!\n"
        f"Avtomobil: {brigade_vehicle}\n"
        f"Tez orada yetib boramiz!"
    )
    await send_sms(phone, message)


async def notify_brigade_new_assignment(
    fcm_token: str,
    call_id: str,
) -> None:
    """Brigadaga yangi vazifa tayinlanganini xabar berish."""
    await send_push_notification(
        fcm_token=fcm_token,
        title="🆘 Yangi chaqiruv!",
        body="Sizga yangi favqulodda chaqiruv tayinlandi. Tafsilotlar uchun bosing.",
        data={"call_id": call_id, "action": "open_call"},
    )
