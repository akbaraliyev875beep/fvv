"""
Tez Yordam EMS — AI Router

Whisper STT (audio → matn) va LLM Risk Scoring endpointlari.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status

from app.core.dependencies import CurrentUser, DbSession, DispatcherUser, limiter
from app.models.emergency_call import EmergencyCall, RiskLevel
from app.schemas.emergency_schema import RiskScoreRequest, RiskScoreResponse
from app.services.audit_service import log_audit
from app.services.whisper_service import transcribe_audio
from app.services.risk_scorer_service import calculate_risk_score
from app.websockets.connection_manager import manager

logger = logging.getLogger("tez_yordam.ai")
router = APIRouter()


@router.post("/transcribe/{call_id}")
@limiter.limit("10/minute")
async def transcribe_call_audio(
    request: Request,
    call_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    audio: UploadFile = File(...),
):
    """
    Audio faylni matnga aylantirish (Whisper STT).

    1. Audio Whisper API'ga yuboriladi
    2. Transkripsiya chaqiruv yozuviga saqlanadi
    3. Audio fayl o'chiriladi (Data Minimization)
    """
    # Chaqiruvni tekshirish
    from sqlalchemy import select
    result = await db.execute(
        select(EmergencyCall).where(EmergencyCall.id == call_id)
    )
    call = result.scalar_one_or_none()
    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chaqiruv topilmadi",
        )

    # Audio'ni transkripsiya qilish
    audio_content = await audio.read()
    transcript = await transcribe_audio(
        audio_data=audio_content,
        filename=audio.filename or "audio.webm",
    )

    if transcript is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Audio transkripsiyasida xatolik yuz berdi",
        )

    # Transkripsiyani saqlash
    call.transcript = transcript
    await db.flush()

    logger.info(f"🎤 Transkripsiya tayyor: call={call_id}, uzunlik={len(transcript)} belgi")

    return {
        "call_id": str(call_id),
        "transcript": transcript,
    }


@router.post("/risk-score", response_model=RiskScoreResponse)
@limiter.limit("20/minute")
async def get_risk_score(
    request: Request,
    body: RiskScoreRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Transkripsiya matni asosida xavf darajasini baholash (LLM).

    PII ma'lumotlar yuborilmaydi — faqat anonimlashtirilgan tibbiy kontekst.
    Natija tavsiya sifatida ko'rsatiladi, avtomatik qaror qabul qilinmaydi.
    """
    risk_result = await calculate_risk_score(
        transcript=body.transcript,
        age=body.age,
        gender=body.gender,
        chief_complaint=body.chief_complaint,
    )

    if risk_result is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Risk baholashda xatolik yuz berdi",
        )

    # Audit log
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="risk_score_generated",
        entity_type="risk_score",
        entity_id=None,
        ip_address=request.client.host if request.client else None,
        details=f"risk_level={risk_result.risk_level}, confidence={risk_result.confidence_score}",
    )

    logger.info(f"🤖 Risk score: level={risk_result.risk_level}, confidence={risk_result.confidence_score}")

    return risk_result


@router.post("/risk-score/{call_id}")
@limiter.limit("10/minute")
async def score_and_save(
    request: Request,
    call_id: uuid.UUID,
    current_user: DispatcherUser,
    db: DbSession,
):
    """
    Chaqiruvning transkripsiyasiga asoslanib risk score hisoblash va saqlash.

    Faqat dispetcher/admin ishlatishi mumkin.
    """
    from sqlalchemy import select
    result = await db.execute(
        select(EmergencyCall).where(EmergencyCall.id == call_id)
    )
    call = result.scalar_one_or_none()
    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chaqiruv topilmadi",
        )

    if not call.transcript:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chaqiruvda transkripsiya mavjud emas",
        )

    # Risk hisoblash
    risk_result = await calculate_risk_score(
        transcript=call.transcript,
    )

    if risk_result is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Risk baholashda xatolik yuz berdi",
        )

    # Natijani saqlash
    call.risk_level = RiskLevel(risk_result.risk_level)
    call.risk_confidence = risk_result.confidence_score
    call.recommended_action = risk_result.recommended_action
    await db.flush()

    # Audit log
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="risk_score_generated",
        entity_type="emergency_call",
        entity_id=str(call.id),
        ip_address=request.client.host if request.client else None,
    )

    # Dispetcherlarga xabar
    await manager.broadcast_to_dispatchers({
        "type": "risk_score_updated",
        "call_id": str(call.id),
        "risk_level": risk_result.risk_level,
        "confidence": risk_result.confidence_score,
        "recommended_action": risk_result.recommended_action,
        "recommended_services": risk_result.recommended_services,
    })

    return {
        "call_id": str(call.id),
        "risk_level": risk_result.risk_level,
        "confidence": risk_result.confidence_score,
        "recommended_action": risk_result.recommended_action,
        "recommended_services": risk_result.recommended_services,
    }
