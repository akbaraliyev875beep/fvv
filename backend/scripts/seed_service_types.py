import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_factory
from app.models.service_type import ServiceType
import app.models.brigade
import app.models.emergency_call
import app.models.user

async def seed_service_types():
    async with async_session_factory() as session:
        services = [
            ServiceType(
                id=uuid.uuid4(),
                code="ambulance",
                name_uz="Tez Yordam",
                name_ru="Скорая Помощь",
                phone_number="103",
                color_hex="#EF4444",
                icon="fa-solid fa-truck-medical",
                is_active=True
            ),
            ServiceType(
                id=uuid.uuid4(),
                code="fire",
                name_uz="O't o'chirish",
                name_ru="Пожарная служба",
                phone_number="101",
                color_hex="#F97316",
                icon="fa-solid fa-fire-extinguisher",
                is_active=True
            ),
            ServiceType(
                id=uuid.uuid4(),
                code="police",
                name_uz="Militsiya",
                name_ru="Милиция",
                phone_number="102",
                color_hex="#3B82F6",
                icon="fa-solid fa-building-shield",
                is_active=True
            ),
            ServiceType(
                id=uuid.uuid4(),
                code="fvv",
                name_uz="FVV (Favqulodda Vaziyatlar Vazirligi)",
                name_ru="МЧС",
                phone_number="112",
                color_hex="#EAB308",
                icon="fa-solid fa-shield-halved",
                is_active=True
            ),
            ServiceType(
                id=uuid.uuid4(),
                code="gas",
                name_uz="Gaz xizmati",
                name_ru="Служба газа",
                phone_number="104",
                color_hex="#8B5CF6",
                icon="fa-solid fa-fire-flame-simple",
                is_active=True
            ),
        ]
        
        for s in services:
            session.add(s)
            
        await session.commit()
        print("Service types have been seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_service_types())
