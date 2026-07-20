"""
Tez Yordam EMS — Asosiy FastAPI ilova.

Barcha router'lar, middleware'lar va lifespan hodisalari shu yerda ulanadi.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path


from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import auth, emergency, dispatcher, ai, services
from app.core.config import settings
from app.core.database import engine, async_session_factory
from app.websockets.connection_manager import manager

# ── Logging sozlash ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("tez_yordam")

# ── Yo'llar ──────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # → /app
FRONTEND_DIR = BASE_DIR / "frontend"
TEMPLATES_DIR = FRONTEND_DIR / "templates"
STATIC_DIR = Path("/app/frontend/static")   # <-- bu qatorda aniq yo‘l

# ── Lifespan (startup / shutdown) ────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Tez Yordam EMS ishga tushmoqda (Local SQLite mode)...")

    # DB jadvallarni avtomatik yaratish (faqat test uchun!)
    from app.models.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Dastlabki mock ma'lumotlar yaratish
    async with async_session_factory() as db:
        from sqlalchemy import select
        from app.models.user import User, UserRole, Patient
        from app.core.security import encrypt_value
        from app.models.brigade import Brigade, BrigadeStatus

        # Mock Admin/Dispatcher yaratish
        result = await db.execute(select(User).where(User.phone == "998901234567"))
        if not result.scalar_one_or_none():
            admin = User(oneid_pin=encrypt_value("12345678901234"), full_name="Admin", phone="998901234567", role=UserRole.ADMIN)
            db.add(admin)
            
            # Mock Brigade yaratish
            b1 = Brigade(vehicle_number="01A111AA", status=BrigadeStatus.AVAILABLE, latitude=41.3111, longitude=69.2401)
            b2 = Brigade(vehicle_number="01B222BB", status=BrigadeStatus.AVAILABLE, latitude=41.2995, longitude=69.2801)
            db.add_all([b1, b2])
            await db.commit()

    yield

    logger.info("🛑 Tez Yordam EMS to'xtamoqda...")
    await engine.dispose()


# ── FastAPI ilovasi ──────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="O'zbekiston uchun favqulodda tibbiy yordam tizimi",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# ── CORS middleware ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static fayllar ───────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Jinja2 Templates ────────────────────────────────────────────
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ── Rate limiting xatolik handler ────────────────────────────────
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── API Router'larni ulash ───────────────────────────────────────
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Autentifikatsiya"],
)
app.include_router(
    emergency.router,
    prefix="/api/v1/emergency",
    tags=["SOS / Chaqiruvlar"],
)
app.include_router(
    dispatcher.router,
    prefix="/api/v1/dispatcher",
    tags=["Dispetcher"],
)
app.include_router(
    ai.router,
    prefix="/api/v1/ai",
    tags=["AI — STT & Risk Scoring"],
)
app.include_router(
    services.router,
    prefix="/api/v1/services",
    tags=["Xizmat Turlari"],
)


# ── Global xatolik handler ──────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Barcha kutilmagan xatoliklarni ushlash."""
    logger.error(f"Kutilmagan xatolik: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Ichki server xatoligi. Iltimos, keyinroq qayta urinib ko'ring.",
            "error_type": type(exc).__name__,
        },
    )


# ── Bosh sahifa ──────────────────────────────────────────────────
@app.get("/", tags=["Sahifalar"])
async def home(request: Request):
    """SOS asosiy sahifa."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "app_name": settings.app_name},
    )


@app.get("/dashboard", tags=["Sahifalar"])
async def dashboard_page(request: Request):
    """Dispetcher dashboard sahifasi."""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "app_name": settings.app_name},
    )


# ── Websockets ───────────────────────────────────────────────────
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/dispatcher")
async def websocket_dispatcher(websocket: WebSocket, token: str):
    # Dastlabki tekshiruvsiz ruxsat (Faqat demo uchun local)
    await manager.connect(websocket, "dispatcher")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "dispatcher")

@app.websocket("/ws/dispatcher/{service_type}")
async def websocket_dispatcher_by_service(websocket: WebSocket, service_type: str, token: str):
    """Xizmat turiga xos dispetcher kanali."""
    channel = f"dispatcher:{service_type}"
    await manager.connect(websocket, channel)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)

@app.websocket("/ws/patient/{call_id}")
async def websocket_patient(websocket: WebSocket, call_id: str, token: str):
    await manager.connect(websocket, f"patient:{call_id}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"patient:{call_id}")

# ── Sahifalar ──────────────────────────────────────────────────
@app.get("/sos/{call_id}", tags=["Sahifalar"])
async def sos_tracking_page(request: Request, call_id: str):
    """SOS chaqiruv kuzatish sahifasi."""
    return templates.TemplateResponse(
        "sos.html",
        {"request": request, "call_id": call_id, "app_name": settings.app_name},
    )


@app.get("/login", tags=["Sahifalar"])
async def login_page(request: Request):
    """Autentifikatsiya sahifasi."""
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "app_name": settings.app_name},
    )


@app.get("/profile", tags=["Sahifalar"])
async def profile_page(request: Request):
    """Foydalanuvchi profili sahifasi."""
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "app_name": settings.app_name},
    )


@app.get("/history", tags=["Sahifalar"])
async def history_page(request: Request):
    """Chaqiruvlar tarixi sahifasi."""
    return templates.TemplateResponse(
        "history.html",
        {"request": request, "app_name": settings.app_name},
    )


@app.get("/admin", tags=["Sahifalar"])
async def admin_page(request: Request):
    """Admin boshqaruv paneli sahifasi."""
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "app_name": settings.app_name},
    )


# ── Health check ─────────────────────────────────────────────────
@app.get("/health", tags=["Tizim"])
async def health_check():
    """Tizim holati tekshiruvi."""
    return {"status": "healthy", "version": settings.app_version}
