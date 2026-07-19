"""
Tez Yordam EMS — Risk Scorer Xizmati (LLM)

LLM orqali bemorning transkripsiya matni va tibbiy kontekstidan
xavf darajasini baholash.

PII ma'lumotlar HECH QACHON LLM'ga yuborilmaydi.
"""

import json
import logging

import httpx

from app.core.config import settings
from app.schemas.emergency_schema import RiskScoreResponse

logger = logging.getLogger("tez_yordam.risk_scorer")

# ── Tizim prompti ───────────────────────────────────────────────
SYSTEM_PROMPT = """Sen O'zbekistondagi tez tibbiy yordam tizimi uchun xavf darajasini baholovchi AI assistantisan.

Senga bemorning ANONIMLASHTIRILGAN tibbiy ma'lumotlari beriladi (ism, pasport, telefon raqami BERILMAYDI).

Sening vazifang:
1. Bemorning holatini tahlil qilish
2. Xavf darajasini aniqlash: LOW, MEDIUM, HIGH, CRITICAL
3. Tavsiya qilingan harakatni yozish
4. Ishonch darajasini 0.0 dan 1.0 gacha baholash
5. Qaysi favqulodda xizmatlar kerakligini aniqlash. Xizmat kodlari: ambulance, fire, police, fvv, gas

JAVOBNI FAQAT quyidagi JSON formatida ber, boshqa hech narsa yozma:
{
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "confidence_score": 0.0-1.0,
    "recommended_action": "Tavsiya qilingan harakat",
    "reasoning": "Qisqa izoh",
    "recommended_services": ["ambulance", "fire"]
}

Xavf darajalari mezonlari:
- CRITICAL: Hayotga bevosita xavf (to'xtab qolgan nafas, ko'p qon ketish, insult belgilari, og'ir alergia)
- HIGH: Jiddiy holat, tezkor yordam kerak (ko'krak og'rig'i, og'ir jarohat, yuqori isitma bilan boshqa belgilar)
- MEDIUM: Tibbiy yordam kerak, lekin bevosita xavf kam (sinish gumon qilinishi, o'rtacha og'riq, engil jarohat)
- LOW: Shoshilinch emas (engil og'riq, kichik shikoyatlar, maslahat kerak)

Xizmatga xos savollar (Agar dispetcherga qo'shimcha ma'lumot kerak bo'lsa, "recommended_action" ichida quyidagi savollarni tavsiya qil):
- Tez Yordam: "Nafas olishi bormi? Qon ketayaptimi?"
- O't o'chirish: "Yong'in qayerda? Necha qavatli bino? Ichkarida odam bormi?"
- Militsiya: "Qurollanganmi? Necha kishi?"
- Gaz: "Gaz hidi sezilayaptimi? Qaysi manzil?"

Har doim bemor foydasiga xato qil — noaniq holatlarda xavfni biroz oshir."""


async def calculate_risk_score(
    transcript: str,
    age: int | None = None,
    gender: str | None = None,
    chief_complaint: str | None = None,
) -> RiskScoreResponse | None:
    """
    Transkripsiya matni asosida xavf darajasini hisoblash.

    Args:
        transcript: Bemorning so'zlari (anonimlashtirilgan)
        age: Yoshi (ixtiyoriy)
        gender: Jinsi (ixtiyoriy)
        chief_complaint: Asosiy shikoyat (ixtiyoriy)

    Returns:
        RiskScoreResponse yoki None
    """
    if not settings.llm_api_key:
        logger.warning("⚠️ LLM API kaliti sozlanmagan — mock natija qaytarilmoqda")
        return _mock_risk_score(transcript)

    # Foydalanuvchi prompti — faqat tibbiy kontekst, PII yo'q
    user_message = f"Bemor so'zlari: {transcript}"
    if age:
        user_message += f"\nYosh: {age}"
    if gender:
        user_message += f"\nJins: {gender}"
    if chief_complaint:
        user_message += f"\nAsosiy shikoyat: {chief_complaint}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)

            return RiskScoreResponse(
                risk_level=result["risk_level"],
                confidence_score=result["confidence_score"],
                recommended_action=result["recommended_action"],
                reasoning=result.get("reasoning", ""),
                recommended_services=result.get("recommended_services", []),
            )

    except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
        logger.error(f"❌ LLM Risk Score xatolik: {e}")
        return None


def _mock_risk_score(transcript: str) -> RiskScoreResponse:
    """Test/dev muhiti uchun mock risk score."""
    # Oddiy kalit so'z tahlili
    critical_words = ["nafas", "qon", "hushdan ketdi", "to'xtab qoldi", "insult"]
    high_words = ["og'riq", "ko'krak", "jarohat", "isitma", "bosh aylanishi"]

    transcript_lower = transcript.lower()

    if any(word in transcript_lower for word in critical_words):
        return RiskScoreResponse(
            risk_level="CRITICAL",
            confidence_score=0.85,
            recommended_action="Darhol reanimatsiya brigadasini yuborish",
            reasoning="Hayotga bevosita xavf belgilari aniqlandi (mock)",
            recommended_services=["ambulance", "fire"] if "yong'in" in transcript_lower else ["ambulance"]
        )
    elif any(word in transcript_lower for word in high_words):
        return RiskScoreResponse(
            risk_level="HIGH",
            confidence_score=0.75,
            recommended_action="Tezkor brigada yuborish, kardiolog tayyorlash",
            reasoning="Jiddiy tibbiy holat belgilari (mock)",
            recommended_services=["ambulance"]
        )
    else:
        return RiskScoreResponse(
            risk_level="MEDIUM",
            confidence_score=0.65,
            recommended_action="Standart brigada yuborish",
            reasoning="O'rtacha darajadagi tibbiy yordam zarur (mock)",
            recommended_services=["ambulance"]
        )
