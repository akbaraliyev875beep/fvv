# arxitektura.md

# Tez Yordam EMS — Tizim Arxitekturasi

## 1. Umumiy Ko'rinish

**Loyiha nomi:** Tez Yordam EMS (Emergency Medical Services)
**Maqsad:** O'zbekiston hududida favqulodda tibbiy holatlarda bemor va dispetcherni real vaqt rejimida bog'lash, OneID orqali shaxsni tasdiqlash, sun'iy intellekt yordamida xavf darajasini avtomatik baholash.

**Asosiy tamoyillar:**
- **Security First** — har bir endpoint autentifikatsiya, avtorizatsiya va validatsiyadan o'tadi
- **SOS-fokusli UX** — bemor uchun 1 tugma bilan chaqiruv, minimal harakat
- **Real-time** — WebSocket orqali dispetcher-bemor-brigada uch tomonlama aloqa
- **AI-assisted triage** — Whisper STT + LLM risk scoring, lekin yakuniy qaror har doim inson (dispetcher) tomonidan
- **Data Minimization** — tashqi AI xizmatlarga faqat zarur minimal ma'lumot yuboriladi

---

## 2. Yuqori Darajadagi Arxitektura Diagrammasi
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Bemor (Web/     │     │   Dispetcher      │     │   Tez Yordam      │
│   Mobile Client)   │     │   Dashboard       │     │   Brigada App     │
└─────────┬─────────┘     └────────┬──────────┘     └────────┬─────────┘
│  HTTPS / WSS            │  HTTPS / WSS             │  HTTPS / WSS
└────────────┬────────────┴────────────┬─────────────┘
│                          │
┌─────────▼──────────────────────────▼─────────┐
│        NGINX (Reverse Proxy + TLS +           │
│        Rate Limiting + Load Balancing)        │
└─────────────────────┬──────────────────────────┘
│
┌──────────────────────▼───────────────────────┐
│         FastAPI Application Server            │
│  ┌───────────────────────────────────────────┐ │
│  │ 1. Auth Module (OneID OAuth2/OIDC + JWT)   │ │
│  ├───────────────────────────────────────────┤ │
│  │ 2. SOS/Chaqiruv Module (REST + WebSocket)  │ │
│  ├───────────────────────────────────────────┤ │
│  │ 3. AI Module (Whisper STT + Risk Scorer)   │ │
│  ├───────────────────────────────────────────┤ │
│  │ 4. Dispatcher Module (Geolokatsiya + Rank) │ │
│  ├───────────────────────────────────────────┤ │
│  │ 5. Notification Module (SMS/Push)          │ │
│  ├───────────────────────────────────────────┤ │
│  │ 6. Audit & Logging Module                  │ │
│  └───────────────────────────────────────────┘ │
└──────┬──────────────┬──────────────┬────────────┘
│              │              │
┌────────────▼──┐   ┌──────▼──────┐  ┌────▼─────────────┐
│  PostgreSQL     │  │  Redis      │  │  OpenAI Whisper   │
│  + PostGIS      │  │  (Pub/Sub + │  │  API (STT)        │
│  (Asosiy DB)    │  │  Session)   │  │                    │
└─────────────────┘  └─────────────┘  └─────────┬──────────┘
│
┌────────▼──────────┐
│  LLM Provider      │
│  (Risk Scoring     │
│  Engine)           │
└─────────────────────┘

---

## 3. Texnologik Stek va Asoslash

| Qatlam | Texnologiya | Sabab |
|---|---|---|
| Backend Framework | Python 3.12 + FastAPI | Native async/await, WebSocket qo'llab-quvvatlash, avtomatik OpenAPI hujjatlashtirish |
| Frontend | HTML/Jinja2 + Tailwind CSS + Vanilla JS | Yengil, tez yuklanadigan, mobil-birinchi, SOS holatida internet sekin bo'lsa ham ishlaydigan |
| Ma'lumotlar bazasi | PostgreSQL 16 + PostGIS kengaytmasi | Geolokatsiya asosida eng yaqin brigadani topish (`ST_Distance`) kritik funksionallik |
| Kesh / Pub-Sub | Redis 7 | WebSocket xabarlarini bir nechta server instance orasida sinxronlash, sessiya keshi |
| STT (Speech-to-Text) | OpenAI Whisper API | Yuqori aniqlik, ko'p tillilik, shovqinli muhitda ham barqaror natija |
| Risk Scoring | LLM (GPT-4 / Claude klassi model) | Tabiiy tilda yozilgan simptomlarni tuzilgan xavf balliga aylantirish |
| Real-time aloqa | FastAPI native WebSockets | Qo'shimcha kutubxonasiz, kam kechikish (low latency) |
| Autentifikatsiya | OneID (OAuth2 Authorization Code + OIDC) | O'zbekistonning rasmiy davlat identifikatsiya tizimi |
| Konteynerlash | Docker + Docker Compose | Dev/staging/prod muhitlarida bir xillik |
| Reverse Proxy | NGINX | TLS termination, rate limiting, static fayllarni tarqatish |

---

## 4. Modullar Batafsil Tavsifi

### 4.1. Auth Module (OneID Integratsiyasi)

**Oqim (Flow):**
1. Foydalanuvchi "OneID orqali kirish" tugmasini bosadi
2. Backend OneID authorization endpointiga redirect qiladi (`state` va `nonce` parametrlari bilan CSRF himoyasi)
3. OneID foydalanuvchini tasdiqlagach, `authorization_code` bilan qaytaradi
4. Backend kodni OneID token endpointiga almashtiradi, `id_token` va foydalanuvchi ma'lumotlarini oladi
5. Backend **o'zining** qisqa muddatli JWT juftligini (access + refresh) generatsiya qiladi

**Rollar (RBAC):**
- `patient` — faqat o'z chaqiruvlarini ko'ra oladi, SOS yubora oladi
- `dispatcher` — barcha faol chaqiruvlarni ko'radi, brigada tayinlaydi
- `brigade` — o'ziga tayinlangan chaqiruv holatini yangilaydi
- `admin` — tizim boshqaruvi, statistika

**Xavfsizlik izohi:** OneID'dan kelgan `id_token` faqat bir martalik shaxsni tasdiqlash uchun ishlatiladi va saqlanmaydi. API'ga kirish uchun faqat backend generatsiya qilgan JWT qo'llaniladi (access token TTL — 15 daqiqa, refresh token — 7 kun, rotatsiya bilan).

### 4.2. SOS/Chaqiruv Module

**Asosiy endpoint:** `POST /api/v1/emergency/sos`

**Ish jarayoni:**
1. Bemor bitta tugmani bosadi → brauzer/ilova geolokatsiyani avtomatik oladi
2. Ixtiyoriy ravishda ovozli xabar yozib yuborish mumkin
3. Chaqiruv `pending` statusda yaratiladi va darhol dispetcher dashboardiga WebSocket orqali push qilinadi
4. Status o'zgarishlari: `pending` → `assigned` → `en_route` → `arrived` → `completed` / `cancelled`

**Xavfsizlik izohi:** SOS endpointi maxsus yumshoq rate-limitga ega — DDoS hujumidan himoyalanadi, lekin haqiqiy shoshilinch chaqiruvni hech qachon bloklamaydi (bitta foydalanuvchidan max N ta so'rov/daqiqa, lekin `emergency=true` flag'i bilan kelgan so'rovlar prioritet oladi).

### 4.3. AI Module

**A) Speech-to-Text (Whisper):**
- Bemor yozib yuborgan audio fayl vaqtinchalik xotira/diskda saqlanadi
- Whisper API'ga yuboriladi, matn (transkripsiya) qaytariladi
- Tahlildan so'ng audio fayl **darhol** (yoki maksimal 24 soat ichida) diskdan fizik o'chiriladi, faqat matn saqlanadi

**B) Risk Scorer (LLM):**
- Kirish: transkripsiya matni + tuzilgan simptom belgilari (yosh, jins, asosiy shikoyat)
- Chiqish: `risk_level` (`LOW` / `MEDIUM` / `HIGH` / `CRITICAL`) + `recommended_action` + `confidence_score`
- Natija dispetcher ekraniga **tavsiya** sifatida ko'rsatiladi, avtomatik qaror qabul qilinmaydi

**Xavfsizlik izohi:** LLM'ga yuboriladigan promptga bemorning F.I.Sh, pasport seriyasi yoki telefon raqami **hech qachon** kiritilmaydi — faqat anonimlashtirilgan tibbiy kontekst yuboriladi. Bu prompt injection va uchinchi tomon PII leak xavfini minimallashtiradi.

### 4.4. Dispatcher Module

- PostGIS `ST_Distance` funksiyasi orqali bemorga eng yaqin **bo'sh** brigadalarni topadi
- Risk darajasiga qarab avtomatik tavsiya beriladi, lekin yakuniy tayinlashni dispetcher tasdiqlaydi
- Brigada holati real vaqtda WebSocket orqali yangilanib turadi (`available`, `busy`, `en_route`, `offline`)

### 4.5. Notification Module

- SMS: mahalliy provayderlar (Eskiz.uz yoki Play Mobile) orqali — internet yo'q holatlarda ham ishlashi uchun
- Push: Firebase Cloud Messaging orqali mobil ilovalarga
- Ishlatilish holati: brigada tayinlanganda bemorga SMS, brigada a'zolariga push

### 4.6. Audit & Logging Module

- Har bir kritik amal alohida `audit_logs` jadvaliga yoziladi: `sos_created`, `risk_score_generated`, `brigade_assigned`, `call_completed`
- Kim, qachon, qaysi IP'dan, qanday amal bajarganini saqlaydi — keyinchalik tekshiruv (compliance) uchun zarur

---

## 5. Ma'lumotlar Bazasi — Yuqori Darajadagi Sxema
users
├── id (PK, UUID)
├── oneid_pin (UNIQUE, shifrlangan)
├── full_name
├── phone (UNIQUE)
├── role (ENUM: patient/dispatcher/brigade/admin)
└── created_at, updated_at
patients (1:1 users bilan)
├── user_id (FK → users.id)
├── blood_type
├── allergies (TEXT[])
└── chronic_conditions (TEXT[])
brigades
├── id (PK, UUID)
├── vehicle_number
├── status (ENUM: available/busy/en_route/offline)
├── current_location (GEOGRAPHY — PostGIS)
└── updated_at
brigade_members
├── brigade_id (FK → brigades.id)
└── user_id (FK → users.id)
emergency_calls
├── id (PK, UUID)
├── patient_id (FK → users.id)
├── brigade_id (FK → brigades.id, NULLABLE)
├── status (ENUM: pending/assigned/en_route/arrived/completed/cancelled)
├── location (GEOGRAPHY — PostGIS)
├── transcript (TEXT, NULLABLE)
├── risk_level (ENUM: LOW/MEDIUM/HIGH/CRITICAL, NULLABLE)
├── risk_confidence (FLOAT, NULLABLE)
├── created_at, assigned_at, resolved_at
call_audio_logs
├── id (PK, UUID)
├── call_id (FK → emergency_calls.id)
├── storage_path (NULLABLE — o'chirilgandan keyin NULL)
├── duration_sec
├── processed_at
└── deleted_at
audit_logs
├── id (PK, UUID)
├── user_id (FK → users.id, NULLABLE)
├── action (VARCHAR)
├── entity_type, entity_id
├── ip_address
└── created_at

**Xavfsizlik izohi:** `emergency_calls` va `patients` jadvallaridagi tibbiy ma'lumotlar uchun **soft delete** (`deleted_at` ustuni) qo'llaniladi — qonuniy audit talablariga ko'ra yozuv butunlay o'chirilmaydi. Ammo `call_audio_logs.storage_path` haqiqiy audio faylga ishora qiladi va STT tahlilidan so'ng bu fayl fizik diskdan o'chiriladi, faqat metadata (`duration_sec`, `processed_at`) qoladi.

---

## 6. Real-Time (WebSocket) Arxitekturasi

**Kanal turlari:**
- `/ws/patient/{call_id}` — bemor o'z chaqiruvi statusini kuzatadi
- `/ws/dispatcher` — dispetcher barcha faol chaqiruvlarni real vaqtda ko'radi
- `/ws/brigade/{brigade_id}` — brigada o'ziga tayinlangan vazifalarni oladi

**Scale qilish:** Bitta serverdan ortiq instance ishlagan holatlarda, Redis Pub/Sub orqali xabarlar barcha instance'larga tarqatiladi — shu orqali qaysi instance'da qaysi foydalanuvchi ulanganidan qat'iy nazar xabar yetib boradi.

**Xavfsizlik izohi:** Har bir WebSocket ulanishi handshake vaqtida JWT token orqali autentifikatsiya qilinadi (`?token=` query param emas, balki `Authorization` header yoki dastlabki subprotocol xabar orqali — token URL loglarida qolib ketmasligi uchun).

---

## 7. Xavfsizlik Arxitekturasi (Cross-Cutting Concerns)

| Qatlam | Chora |
|---|---|
| Transport xavfsizligi | TLS 1.3 majburiy, barcha HTTP so'rovlar HTTPS'ga redirect qilinadi |
| Autentifikatsiya | OneID OIDC + backend JWT (access 15 daqiqa, refresh 7 kun, rotatsiya bilan) |
| Avtorizatsiya | RBAC — FastAPI `Depends()` orqali har bir endpointda rol tekshiruvi |
| Ma'lumotlar shifrlash | PII maydonlar (pasport, telefon) at-rest AES-256 bilan shifrlanadi |
| Audio maxfiyligi | Whisper tahlilidan keyin audio fayllar 24 soat ichida fizik o'chiriladi |
| Kirish nazorati (Rate Limiting) | NGINX + SlowAPI darajasida, SOS endpointi uchun alohida yumshoq siyosat |
| Kod xavfsizligi | Faqat SQLAlchemy ORM / parametrized query (SQL Injection'ga qarshi), Pydantic orqali qat'iy input validatsiya |
| Prompt xavfsizligi | LLM'ga PII yuborilmaydi, system prompt orqali prompt injection'ga qarshi filtrlash |
| Audit | Kritik amallar (`sos_created`, `risk_score_generated`, `brigade_assigned`) alohida audit jadvaliga yoziladi |
| Sessiya boshqaruvi | Redis'da saqlangan sessiyalar, logout vaqtida token blacklist'ga qo'shiladi |
| CORS | Faqat ma'lum domenlar (frontend production URL) uchun ochiq |

---

## 8. Papka Strukturasi (Loyiha Darajasida)
tez-yordam-ems/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── emergency.py
│   │   │       ├── dispatcher.py
│   │   │       └── ai.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── dependencies.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── emergency_call.py
│   │   │   └── brigade.py
│   │   ├── schemas/
│   │   │   ├── user_schema.py
│   │   │   └── emergency_schema.py
│   │   ├── services/
│   │   │   ├── whisper_service.py
│   │   │   ├── risk_scorer_service.py
│   │   │   └── dispatcher_service.py
│   │   └── websockets/
│   │       └── connection_manager.py
│   ├── alembic/
│   │   └── versions/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
│       ├── index.html
│       └── dashboard.html
├── docker-compose.yml
├── .env.example
└── arxitektura.md

---

## 9. Keyingi Bosqichlar (Roadmap)

Ushbu arxitektura hujjati asosida quyidagi qismlarni alohida so'rov sifatida ishlab chiqish tavsiya etiladi:

1. **Database Layer** — to'liq SQLAlchemy modellari + Alembic migratsiya fayllari
2. **API Layer** — FastAPI router'lar, Pydantic sxemalar, dependency injection
3. **WebSocket Connection Manager** — to'liq ishlaydigan real-time kod
4. **AI Service Layer** — Whisper STT integratsiyasi + Risk Scorer prompt engineering
5. **Frontend SOS UI** — Tailwind CSS asosidagi minimalistik bemor interfeysi
6. **Dispatcher Dashboard** — real-time xarita va chaqiruvlar ro'yxati
