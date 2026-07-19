# 📋 Ertangi Ishlar — 2026-yil 17-iyul

## 🚀 YANGI KATTA G'OYA: Yagona Favqulodda Xizmatlar Platformasi

> **Eski konsept:** Faqat Tez Yordam (103)
> **Yangi konsept:** Barcha favqulodda xizmatlarni bitta platformada birlashtirish

### Platformaga kiritiladigan xizmatlar:

| # | Xizmat | Raqam | Rangi | Ikona |
|---|--------|-------|-------|-------|
| 🚑 | Tez Yordam | 103 | 🔴 Qizil | Ambulans |
| 🚒 | O't o'chirish | 101 | 🟠 To'q sariq | Yong'in mashinasi |
| 🚔 | Militsiya | 102 | 🔵 Ko'k | Politsiya mashinasi |
| 🏛️ | FVV (Favqulodda Vaziyatlar Vazirligi) | 112 | 🟡 Sariq | Qalqon |
| 🔥 | Gaz xizmati | 104 | 🟤 Jigarrang | Gaz alangasi |

---

## 🏗️ Arxitektura O'zgarishlari

### 1. Yagona SOS tizimi — "Bitta tugma, barcha xizmatlar"

Bemor SOS bosganida:
```
┌──────────────────────────────────────────────────┐
│              🆘 FAVQULODDA CHAQIRUV              │
│                                                   │
│   ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  │
│   │ 🚑  │  │ 🚒  │  │ 🚔  │  │ 🏛️  │  │ 🔥  │  │
│   │ Tez  │  │ O't  │  │Milit│  │ FVV  │  │ Gaz  │  │
│   │Yordam│  │O'chir│  │siya │  │ 112  │  │      │  │
│   └─────┘  └─────┘  └─────┘  └─────┘  └─────┘  │
│                                                   │
│          [ 🆘 UMUMIY SOS — BARCHASI ]            │
│                                                   │
└──────────────────────────────────────────────────┘
```

- Bemor aniq xizmatni tanlashi mumkin
- Yoki "UMUMIY SOS" bosib, AI avtomatik tahlil qiladi va kerakli xizmatlarni chaqiradi
- Bir vaqtda bir nechta xizmatni tanlash mumkin (masalan: yong'in + tez yordam)

### 2. Yangi Database Schema

```
service_types (YANGI jadval)
├── id (PK)
├── code (UNIQUE: "ambulance", "fire", "police", "fvv", "gas")
├── name_uz ("Tez Yordam", "O't o'chirish", ...)
├── name_ru
├── phone_number ("103", "101", ...)
├── color_hex ("#DC2626", "#EA580C", ...)
├── icon
└── is_active (BOOLEAN)

brigades (YANGILASH)
├── ...mavjud maydonlar...
├── service_type_id (FK → service_types.id)  ← YANGI
└── specialization (TEXT)                     ← YANGI

emergency_calls (YANGILASH)
├── ...mavjud maydonlar...
├── service_type_id (FK → service_types.id)  ← YANGI
├── is_multi_service (BOOLEAN)               ← YANGI
└── parent_call_id (FK → self, NULLABLE)     ← YANGI (bitta hodisa, bir nechta xizmat)

dispatchers (YANGI jadval)
├── user_id (FK → users.id)
├── service_type_id (FK → service_types.id)  ← qaysi xizmat dispetcheri
└── is_on_duty (BOOLEAN)
```

### 3. Multi-Service Call Flow (Bir nechta xizmat chaqiruvi)

```
Bemor: "Uyda yong'in, odamlar jarohatli!"
        │
        ▼
   AI tahlil qiladi:
   ✅ O't o'chirish — yong'in
   ✅ Tez Yordam — jarohatlilar
   ⬜ Militsiya — hozircha kerak emas
   ⬜ Gaz — tekshirish tavsiya etiladi
        │
        ▼
   Bitta parent_call yaratiladi
   ├── child_call → O't o'chirish dispetcheriga
   ├── child_call → Tez Yordam dispetcheriga
   └── child_call → Gaz xizmati (tavsiya)
```

---

## 📋 Ertangi Ishlar Rejasi (Ustuvorlik bo'yicha)

### 🔴 BIRINCHI QADAM — Asosiy tuzilma (2-3 soat)

#### 1.1. Service Types modeli va seed data
- [x] `service_type.py` model yaratish
- [x] Seed data — 5 ta xizmat turini bazaga qo'shish
- [x] Alembic migratsiya

#### 1.2. Database modellarni yangilash
- [x] `Brigade` modeliga `service_type_id` qo'shish
- [x] `EmergencyCall` modeliga `service_type_id`, `is_multi_service`, `parent_call_id` qo'shish
- [x] `Dispatcher` profil modeli — qaysi xizmatga tegishli
- [x] Alembic migratsiyalar

#### 1.3. Pydantic schemalarni yangilash
- [x] `ServiceTypeSchema` yaratish
- [x] `EmergencyCallCreate` ga `service_type` qo'shish
- [x] `BrigadeSchema` yangilash

### 🟡 IKKINCHI QADAM — API va Backend (3-4 soat)

#### 2.1. Service Types API
- [x] `GET /api/v1/services` — barcha xizmat turlari ro'yxati
- [x] `GET /api/v1/services/{code}` — bitta xizmat ma'lumoti

#### 2.2. Emergency API yangilash
- [x] `POST /api/v1/emergency/sos` — `service_type` parametri qo'shish
- [x] Multi-service SOS — bir vaqtda bir nechta xizmat chaqirish
- [x] AI auto-detect — ovozli xabar asosida kerakli xizmatlarni aniqlash
- [x] Har bir xizmat uchun alohida dispetcher WebSocket kanali

#### 2.3. Dispatcher API yangilash
- [x] Dispetcher faqat o'z xizmat turidagi chaqiruvlarni ko'radi
- [x] Brigada tayinlash — faqat mos xizmat turdagi brigadalar
- [x] Cross-service koordinatsiya — bir nechta xizmat ishtirok etganda

#### 2.4. WebSocket kanallarni kengaytirish
- [x] `/ws/dispatcher/{service_type}` — xizmat bo'yicha ajratilgan kanal
- [x] `/ws/brigade/{brigade_id}` — brigadalar uchun (mavjud, yangilash)
- [x] `/ws/coordination/{call_id}` — YANGI: multi-service holatlarda xizmatlar aro aloqa

### 🟢 UCHINCHI QADAM — Frontend (3-4 soat)

#### 3.1. SOS sahifasini yangilash
- [x] 5 ta xizmat tugmasi — rangli, ikonkali, animatsiyali
- [x] "UMUMIY SOS" tugmasi — barchasi uchun
- [x] Multi-select rejimi — bir nechta xizmatni tanlash
- [x] Har bir xizmat uchun o'ziga xos UI rangi

#### 3.2. Dispetcher Dashboard yangilash
- [x] Xizmat turi bo'yicha filter
- [x] Har bir xizmat o'z rangida ko'rsatiladi
- [x] Multi-service chaqiruvlar uchun maxsus ko'rinish
- [x] Boshqa xizmatlar bilan koordinatsiya paneli

#### 3.3. Admin panel yangilash
- [x] Xizmat turlarini boshqarish (CRUD)
- [x] Har xizmat bo'yicha statistika
- [x] Brigadalarni xizmat turiga biriktirish

#### 3.4. Umumiy UI
- [x] Landing page — barcha xizmatlar ko'rsatilgan
- [x] Xizmat turiga qarab rang sxemasi o'zgaradi
- [x] Animatsiyali xizmat tanlash

### 🔵 TO'RTINCHI QADAM — AI yaxshilash (2 soat)

#### 4.1. Multi-service AI triage
- [x] AI promptni yangilash — xizmat turini avtomatik aniqlash
- [x] Bir xabardan bir nechta xizmat tavsiya qilish
- [x] Risk level har xizmat uchun alohida

#### 4.2. Xizmatga xos savollar
- [x] Tez Yordam: "Nafas olishi bormi? Qon ketayaptimi?"
- [x] O't o'chirish: "Yong'in qayerda? Necha qavatli bino?"
- [x] Militsiya: "Qurollanganmi? Necha kishi?"
- [x] Gaz: "Gaz hidi sezilayaptimi? Qaysi manzil?"

---

## 📊 Hozirgi Loyiha Holati

| Modul | Holat | Ertaga qilish kerak |
|-------|-------|---------------------|
| Auth API | ✅ Tayyor | OneID integratsiya |
| Emergency API | ✅ Tayyor | Multi-service qo'shish |
| Dispatcher API | ✅ Tayyor | Service filter qo'shish |
| AI API | ⚠️ Skeleton | Multi-service triage |
| WebSocket | ✅ Asosiy tayyor | Service-based kanallar |
| DB Models | ✅ Tayyor | ServiceType model, yangi fieldlar |
| Frontend SOS | ✅ Tayyor | 5 ta xizmat tugmasi |
| Frontend Dashboard | ✅ Tayyor | Service filter, rang |
| Frontend Admin | ✅ Tayyor | Service boshqaruvi |
| DB | ⚠️ SQLite | PostgreSQL ga o'tish |

---

## 🎯 Ertangi Kun Maqsadi

**Minimal tayyor mahsulot (MVP):**
> Foydalanuvchi SOS sahifasida 5 ta xizmatdan birini (yoki bir nechtasini) tanlab,
> chaqiruv yubora oladi. Har bir xizmatning o'z dispetcheri bor.
> AI ovozli xabarni tahlil qilib, qaysi xizmatlar kerakligini tavsiya qiladi.

**Nomi:** ~~Tez Yordam~~ → **112 Yagona Favqulodda Xizmatlar Platformasi**

---

## 💡 Kelajakdagi G'oyalar (keyingi kunlar uchun)

- 📍 GPS tracking — brigada harakatini real vaqtda kuzatish
- 📊 Analitika dashboard — shahar bo'yicha hodisalar xaritasi
- 🗣️ Ko'p tillilik — o'zbek, rus, ingliz
- 📱 Mobil ilova (React Native / Flutter)
- 🤝 Xizmatlar aro chat — yong'inda tez yordam va o't o'chirish birgalikda ishlashi
- 🎙️ Real-time audio stream — dispetcher bemor bilan gaplashishi
- 🏥 Kasalxonalar bazasi — eng yaqin kasalxonaga yo'naltirish

---

*Yaratildi: 2026-yil 17-iyul, 00:32*
*Loyiha: 112 — Yagona Favqulodda Xizmatlar Platformasi*
