"""
Tez Yordam EMS — Whisper STT Xizmati

OpenAI Whisper API orqali audio faylni matnga aylantirish.
Audio fayllar tahlildan keyin o'chiriladi (Data Minimization).
"""

import logging
import io

import httpx

from app.core.config import settings

logger = logging.getLogger("tez_yordam.whisper")


async def transcribe_audio(
    audio_data: bytes,
    filename: str = "audio.webm",
    language: str = "uz",
) -> str | None:
    """
    Audio ma'lumotni Whisper API orqali matnga aylantirish.

    Args:
        audio_data: Audio fayl baytlari
        filename: Fayl nomi (format aniqlash uchun)
        language: Til kodi (default: o'zbek)

    Returns:
        Transkripsiya matni yoki None (xatolik bo'lsa)
    """
    if not settings.openai_api_key:
        logger.warning("⚠️ OpenAI API kaliti sozlanmagan — mock natija qaytarilmoqda")
        return _mock_transcription()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                },
                data={
                    "model": settings.whisper_model,
                    "language": language,
                    "response_format": "text",
                },
                files={
                    "file": (filename, io.BytesIO(audio_data), "audio/webm"),
                },
            )
            response.raise_for_status()

            transcript = response.text.strip()
            logger.info(f"✅ Whisper transkripsiya tayyor: {len(transcript)} belgi")
            return transcript

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Whisper API xatolik: {e.response.status_code} — {e.response.text}")
        return None
    except httpx.HTTPError as e:
        logger.error(f"❌ Whisper API ulanish xatoligi: {e}")
        return None


def _mock_transcription() -> str:
    """Test/dev muhiti uchun mock transkripsiya."""
    return (
        "Ko'kragimda kuchli og'riq bor, nafas olish qiyin. "
        "Bu holat 30 daqiqa oldin boshlandi. "
        "Oldin ham shunday bo'lgan, dori ichganman."
    )
