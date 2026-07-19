"""
Tez Yordam EMS — Audit Xizmati

Barcha kritik amallarni audit_logs jadvaliga yozish.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emergency_call import AuditLog

logger = logging.getLogger("tez_yordam.audit")


async def log_audit(
    db: AsyncSession,
    user_id: str | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    ip_address: str | None = None,
    details: str | None = None,
) -> AuditLog:
    """
    Audit log yozish.

    Args:
        db: DB session
        user_id: Foydalanuvchi ID (UUID string)
        action: Amal turi (masalan: sos_created, brigade_assigned)
        entity_type: Ob'ekt turi
        entity_id: Ob'ekt ID
        ip_address: So'rov IP manzili
        details: Qo'shimcha tafsilotlar

    Returns:
        Yaratilgan AuditLog
    """
    audit = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        details=details,
    )
    db.add(audit)
    await db.flush()

    logger.debug(
        f"📝 Audit: {action} | user={str(user_id)[:8] if user_id else 'system'} | "
        f"entity={entity_type}:{entity_id}"
    )

    return audit
