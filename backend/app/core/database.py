"""
Tez Yordam EMS — Ma'lumotlar Bazasi Ulanishi (SQLite)
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Async engine — SQLite
engine = create_async_engine(
    "sqlite+aiosqlite:///./tez_yordam.db",
    echo=False,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
