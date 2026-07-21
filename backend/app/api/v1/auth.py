"""
Tez Yordam EMS — Autentifikatsiya Router

OneID OAuth2/OIDC orqali login, JWT token yaratish/yangilash.
Local demo uchun mock OneID.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import CurrentUser, DbSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    encrypt_value,
)
from app.models.user import Patient, User, UserRole
from app.schemas.user_schema import (
    TokenResponse,
    UserRead,
    UserWithProfile,
    UserUpdate,
    UserRoleUpdate,
    PatientProfileUpdate,
)

logger = logging.getLogger("tez_yordam.auth")
router = APIRouter()


@router.get("/login/oneid")
async def login_with_oneid(request: Request):
    """Mock OneID login — local test uchun."""
    return RedirectResponse(url="/api/v1/auth/callback?code=mock_code&state=mock_state")


@router.get("/callback")
async def oneid_callback(
    request: Request,
    code: str,
    state: str,
    db: DbSession,
):
    """Mock OneID callback — foydalanuvchi yaratish va JWT berish."""
    # Mock OneID data
    user_info = {
        "pin": "12345678901234",
        "full_name": "Eshmatov Toshmat",
        "mob_phone_no": "998991234567",
    }

    oneid_pin = user_info["pin"]
    full_name = user_info["full_name"]
    phone = user_info["mob_phone_no"]

    # Telefon raqam bo'yicha qidirish (encryption tufayli pin bo'yicha qidirish murakkab)
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if user is None:
        encrypted_pin = encrypt_value(oneid_pin)
        user = User(
            oneid_pin=encrypted_pin,
            full_name=full_name,
            phone=phone,
            role=UserRole.ADMIN,  # Demo uchun admin qilamiz
        )
        db.add(user)
        await db.flush()

        patient = Patient(user_id=user.id)
        db.add(patient)
        await db.flush()
        logger.info(f"Yangi foydalanuvchi yaratildi: {user.id}")
    else:
        logger.info(f"Mavjud foydalanuvchi kirdi: {user.id}")

    # JWT yaratish
    access = create_access_token({"sub": str(user.id), "role": user.role.value})

    # HTML orqali token'ni localStorage'ga saqlash va redirect
    html = f"""
    <html><body><script>
        localStorage.setItem('access_token', '{access}');
        window.location.href = '/';
    </script></body></html>
    """
    return HTMLResponse(content=html)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: Request,
    db: DbSession,
):
    """Access token'ni refresh token orqali yangilash (local — Redis'siz)."""
    # Demo uchun oddiy qayta-token berish
    return {"detail": "Refresh token local demo'da ishlamaydi. Qayta login qiling."}


@router.post("/logout")
async def logout(request: Request):
    """Chiqish."""
    return {"detail": "Muvaffaqiyatli chiqildi"}

# Admin login page (GET)
@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page():
    """Render simple admin login form."""
    html = """
    <html>
      <head><title>Admin Login</title></head>
      <body style='font-family:Arial, sans-serif;'>
        <h2>Admin Login</h2>
        <form action='/api/v1/auth/admin/login' method='post'>
          <label>Username: <input type='text' name='username' required></label><br/><br/>
          <label>Password: <input type='password' name='password' required></label><br/><br/>
          <button type='submit'>Login</button>
        </form>
      </body>
    </html>
    """
    return HTMLResponse(content=html)

# Admin login processing (POST)
@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(
    username: str = Form(...),
    password: str = Form(...),
    db: DbSession,
):
    """Hard‑coded admin authentication.
    Username: 'aka'
    Password: '123Diyorbek'
    """
    if username != "aka" or password != "123Diyorbek":
        raise HTTPException(status_code=401, detail="Invalid admin credentials")

    # Find existing admin or create one
    result = await db.execute(select(User).where(User.role == UserRole.ADMIN))
    admin_user = result.scalar_one_or_none()
    if admin_user is None:
        # create a dummy admin user; pin can be placeholder
        admin_user = User(
            oneid_pin=encrypt_value("admin_pin"),
            full_name="Admin",
            phone="admin",
            role=UserRole.ADMIN,
        )
        db.add(admin_user)
        await db.flush()
        # also create a patient record for admin (optional)
        patient = Patient(user_id=admin_user.id)
        db.add(patient)
        await db.flush()

    access = create_access_token({"sub": str(admin_user.id), "role": admin_user.role.value})
    refresh = create_refresh_token({"sub": str(admin_user.id)})
    return {"access_token": access, "refresh_token": refresh}

# Admin dashboard placeholder (GET) – protected by AdminUser
@router.get("/admin/dashboard", response_class=HTMLResponse, dependencies=[Depends(AdminUser)])
async def admin_dashboard():
    """Simple placeholder dashboard for admin."""
    html = """
    <html>
      <head><title>Admin Dashboard</title></head>
      <body style='font-family:Arial, sans-serif;'>
        <h1>Admin Dashboard</h1>
        <p>This is a placeholder. You can extend it with real admin UI.</p>
        <a href='/'>← Back to Home</a>
      </body>
    </html>
    """
    return HTMLResponse(content=html)

# Endpoint for admin to create dispatcher users
@router.post("/admin/dispatchers", response_model=UserRead, dependencies=[Depends(AdminUser)])
async def create_dispatcher(
    username: str = Form(...),
    full_name: str = Form(...),
    phone: str = Form(...),
    db: DbSession,
):
    """Create a new dispatcher user (role DISPATCHER)."""
    # Check if phone already used
    existing = await db.execute(select(User).where(User.phone == phone))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Phone number already used")
    # Create user
    user = User(
        oneid_pin=encrypt_value(username),
        full_name=full_name,
        phone=phone,
        role=UserRole.DISPATCHER,
    )
    db.add(user)
    await db.flush()
    return UserRead.model_validate(user)



@router.get("/me", response_model=UserWithProfile)
async def get_current_user_info(current_user: CurrentUser):
    """Joriy foydalanuvchi ma'lumotlari."""
    # current_user.patient_profile is eagerly loaded via selectin
    return UserWithProfile.model_validate({
        "id": current_user.id,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "role": current_user.role.value,
        "created_at": current_user.created_at,
        "blood_type": current_user.patient_profile.blood_type if current_user.patient_profile else None,
        "allergies": current_user.patient_profile.allergies if current_user.patient_profile else None,
        "chronic_conditions": current_user.patient_profile.chronic_conditions if current_user.patient_profile else None,
        "home_latitude": current_user.patient_profile.home_latitude if current_user.patient_profile else None,
        "home_longitude": current_user.patient_profile.home_longitude if current_user.patient_profile else None,
        "home_address": current_user.patient_profile.home_address if current_user.patient_profile else None,
    })


@router.put("/profile", response_model=UserRead)
async def update_profile(
    body: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Foydalanuvchi asosiy ma'lumotlarini yangilash."""
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.phone is not None:
        current_user.phone = body.phone
    await db.flush()
    return UserRead.model_validate(current_user)


@router.put("/medical-info", response_model=UserWithProfile)
async def update_medical_info(
    body: PatientProfileUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Bemorning tibbiy ma'lumotlarini yangilash."""
    if not current_user.patient_profile:
        patient = Patient(user_id=current_user.id)
        db.add(patient)
        await db.flush()
        current_user.patient_profile = patient
        
    if body.blood_type is not None:
        current_user.patient_profile.blood_type = body.blood_type
    if body.allergies is not None:
        current_user.patient_profile.allergies = body.allergies
    if body.chronic_conditions is not None:
        current_user.patient_profile.chronic_conditions = body.chronic_conditions
    if body.home_latitude is not None:
        current_user.patient_profile.home_latitude = body.home_latitude
    if body.home_longitude is not None:
        current_user.patient_profile.home_longitude = body.home_longitude
    if body.home_address is not None:
        current_user.patient_profile.home_address = body.home_address
        
    await db.flush()
    
    return UserWithProfile.model_validate({
        "id": current_user.id,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "role": current_user.role.value,
        "created_at": current_user.created_at,
        "blood_type": current_user.patient_profile.blood_type,
        "allergies": current_user.patient_profile.allergies,
        "chronic_conditions": current_user.patient_profile.chronic_conditions,
        "home_latitude": current_user.patient_profile.home_latitude,
        "home_longitude": current_user.patient_profile.home_longitude,
        "home_address": current_user.patient_profile.home_address,
    })


# --- Admin yo'llari ---

from app.core.dependencies import AdminUser

@router.get("/users", response_model=list[UserRead])
async def list_users(
    current_user: AdminUser,
    db: DbSession,
    skip: int = 0,
    limit: int = 50,
):
    """Barcha foydalanuvchilar ro'yxati (Faqat Admin)."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return [UserRead.model_validate(u) for u in users]


@router.patch("/users/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: str,
    body: UserRoleUpdate,
    current_user: AdminUser,
    db: DbSession,
):
    """Foydalanuvchi rolini o'zgartirish (Faqat Admin)."""
    import uuid
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Noto'g'ri UUID formati")
        
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
        
    user.role = UserRole(body.role)
    await db.flush()
    
    return UserRead.model_validate(user)
