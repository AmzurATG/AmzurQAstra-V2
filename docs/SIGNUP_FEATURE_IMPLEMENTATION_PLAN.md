# Signup Feature — V2 Implementation Plan

## Overview

Add a multi-step signup flow to QAstra V2, adapted from the old version's implementation. The app is distributed as a local executable, so no Redis or external services beyond PostgreSQL and SMTP (already configured).

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| OTP Storage | PostgreSQL table | Survives restart; no new deps; uses existing DB |
| Pending Registrations | PostgreSQL table | Same as above; in-memory is risky for exe restarts |
| Lockout Tracking | Same DB table (attempts + locked_until) | Persistent; can't bypass by restarting |
| Email Service | Existing `smtp_mailer.py` | Already configured with Gmail SMTP in `.env` |
| Frontend Framework | TypeScript + React (Vite) | Matches current V2 frontend stack |
| State Management | Zustand `authStore` | Existing pattern in V2 |
| API Client | Axios with interceptors | Existing pattern in V2 |

---

## User Flow

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  Step 1:        │     │  Step 2:            │     │  Step 3:        │
│  SignupForm     │────▶│  SecurityQuestions   │────▶│  VerifyEmail    │
│                 │     │                     │     │                 │
│  • First Name   │     │  • Question 1       │     │  • 6-digit OTP  │
│  • Last Name    │     │  • Answer 1         │     │  • Auto-focus   │
│  • Company      │     │  • Question 2       │     │  • Paste support│
│  • Email        │     │  • Answer 2         │     │  • 30s resend   │
│  • Phone (opt)  │     │                     │     │  • 3-attempt    │
│  • Password     │     │                     │     │    lockout      │
└─────────────────┘     └─────────────────────┘     └─────────────────┘
        │                        │                         │
   POST /check-email        POST /signup             POST /verify-otp
```

---

## Backend Changes

### 1. New Database Tables (Alembic Migration)

#### `email_verifications` table
```sql
CREATE TABLE email_verifications (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    otp_hash VARCHAR(255) NOT NULL,
    user_data JSONB NOT NULL,              -- Stores pending registration data
    security_questions JSONB,              -- Stores security Q&A (answers hashed)
    expires_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_email_verifications_email ON email_verifications(email);
CREATE INDEX idx_email_verifications_expires ON email_verifications(expires_at);
```

#### `security_questions` table
```sql
CREATE TABLE security_questions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    question_text VARCHAR(500) NOT NULL,
    answer_hash VARCHAR(255) NOT NULL,     -- bcrypt hashed (case-insensitive)
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_security_questions_user ON security_questions(user_id);
```

#### `password_reset_tokens` table
```sql
CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_reset_tokens_user ON password_reset_tokens(user_id);
```

#### User model additions (ALTER TABLE)
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS company_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS country_code VARCHAR(10);
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);
```

> Note: `is_verified` defaults to TRUE so existing users remain unaffected.

---

### 2. New Files

| File | Purpose |
|------|---------|
| `backend/common/db/models/email_verification.py` | SQLAlchemy model for `email_verifications` |
| `backend/common/db/models/security_question.py` | SQLAlchemy model for `security_questions` |
| `backend/common/db/models/password_reset_token.py` | SQLAlchemy model for `password_reset_tokens` |
| `backend/common/services/otp_service.py` | OTP generation, storage, verification, email sending |
| `backend/common/services/signup_service.py` | Signup business logic (pending registrations, user creation) |
| `backend/common/schemas/signup.py` | Pydantic schemas: `SignupRequest`, `OTPVerifyRequest`, etc. |
| `backend/api/v1/common/signup.py` | API router with signup endpoints |
| `backend/alembic/versions/XXXX_add_signup_tables.py` | Migration for new tables + user model changes |

### 3. New API Endpoints

| Method | Path | Purpose | Auth Required |
|--------|------|---------|---------------|
| POST | `/api/v1/auth/check-email` | Check if email is registered | No |
| POST | `/api/v1/auth/signup` | Submit registration + send OTP | No |
| POST | `/api/v1/auth/verify-otp` | Verify OTP + create user | No |
| POST | `/api/v1/auth/resend-otp` | Resend OTP email | No |

### 4. OTP Service Logic (`otp_service.py`)

```python
# Core functions:
- generate_otp(length=6) -> str
- create_verification(email, user_data, security_questions) -> None
    # Stores hashed OTP + pending data in email_verifications table
    # Sends OTP via existing smtp_mailer
- verify_otp(email, otp) -> "valid" | "invalid" | "expired" | "locked"
    # Checks attempts, lockout, expiry, hash match
- resend_otp(email) -> None
    # Generates new OTP, resets attempts (if not locked), sends email
- cleanup_expired() -> None
    # Deletes rows where expires_at < NOW() (call on app startup or periodically)
```

### 5. Signup Service Logic (`signup_service.py`)

```python
- check_email_exists(email) -> bool
- initiate_signup(signup_data: SignupRequest) -> dict
    # Validates business email, password strength
    # Stores pending data in email_verifications via otp_service
    # Returns {"message": "...", "email": "..."}
- complete_signup(email, otp) -> User
    # Verifies OTP
    # Creates user in users table (hashed password)
    # Stores security questions (hashed answers)
    # Marks is_verified = True
    # Cleans up email_verifications row
    # Returns created user
```

### 6. Email Template

Simple HTML OTP email using existing SMTP config:
```
Subject: "Your QAstra Verification Code"
Body: Welcome message + 6-digit code + 5-minute expiry notice
```

---

## Frontend Changes

### 1. New Files

| File | Purpose |
|------|---------|
| `frontend/src/common/pages/Signup.tsx` | Step 1: Registration form |
| `frontend/src/common/pages/SecurityQuestions.tsx` | Step 2: Security Q&A |
| `frontend/src/common/pages/VerifyEmail.tsx` | Step 3: OTP verification |
| `frontend/src/common/api/signup.ts` | API calls: checkEmail, signup, verifyOtp, resendOtp |

### 2. Modified Files

| File | Change |
|------|--------|
| `frontend/src/App.tsx` | Add routes: `/signup`, `/security-questions`, `/verify-email` |
| `frontend/src/common/pages/Login.tsx` | Add "Sign up" link |
| `frontend/src/common/types/auth.ts` | Add signup-related types |

### 3. Route Structure

```typescript
// Public routes (no auth required)
<Route path="/login" element={<Login />} />
<Route path="/signup" element={<Signup />} />
<Route path="/security-questions" element={<SecurityQuestions />} />
<Route path="/verify-email" element={<VerifyEmail />} />
```

### 4. Form Validations (SignupForm)

| Field | Rules |
|-------|-------|
| First Name | Required, max 50 chars, letters/spaces/hyphens |
| Last Name | Required, max 50 chars, letters/spaces/hyphens |
| Company Name | Required, 2-100 chars |
| Email | Business email only; domain must match company name; block free providers |
| Phone | Optional, country-specific digit count |
| Password | 8-64 chars, uppercase + lowercase + number + special char |
| Confirm Password | Must match password |

### 5. OTP Verification UX

- 6 individual input fields with auto-focus
- Paste support (full 6-digit code)
- Arrow key + backspace navigation
- 30-second resend cooldown timer
- 3-attempt lockout with countdown display
- Lockout state persisted in localStorage

---

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| OTP brute force | 3-attempt lockout + 5-min cooldown (DB-backed) |
| OTP in DB | Stored as bcrypt hash, not plaintext |
| Security answers | bcrypt hashed, case-insensitive (`.lower()` before hash) |
| Password storage | bcrypt with salt (existing V2 pattern) |
| Email enumeration | `check-email` endpoint exists; acceptable for business app |
| Pending data cleanup | Expired verifications deleted on app startup + periodically |
| Business email enforcement | Block free providers (gmail, yahoo, etc.) |

---

## Implementation Order

### Phase 1: Backend
1. [ ] Create Alembic migration (new tables + user model fields)
2. [ ] Create SQLAlchemy models (`email_verification`, `security_question`, `password_reset_token`)
3. [ ] Create Pydantic schemas (`signup.py`)
4. [ ] Create OTP service (`otp_service.py`) — uses existing `smtp_mailer.py`
5. [ ] Create signup service (`signup_service.py`)
6. [ ] Create API router (`signup.py`) with endpoints
7. [ ] Register router in `api/v1/router.py`
8. [ ] Test endpoints manually

### Phase 2: Frontend
9. [ ] Create signup API client (`signup.ts`)
10. [ ] Create `Signup.tsx` (Step 1 form with validations)
11. [ ] Create `SecurityQuestions.tsx` (Step 2)
12. [ ] Create `VerifyEmail.tsx` (Step 3 OTP input)
13. [ ] Add routes in `App.tsx`
14. [ ] Add "Sign up" link on Login page
15. [ ] Test full flow end-to-end

### Phase 3: Polish
16. [ ] Expired verification cleanup on startup
17. [ ] Error handling edge cases
18. [ ] Loading states and toast notifications

---

## Config Required (Already in `.env`)

```env
# Already configured — no changes needed:
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=qastra-dev@amzur.com
SMTP_PASSWORD=aigajtdozwyauyip
EMAIL_FROM_ADDRESS=qastra-dev@amzur.com
EMAIL_FROM_NAME=QAstra
DATABASE_URL=postgresql+asyncpg://qastra:qastra123@localhost:5432/qastra
```

---

## Reference Files

- Old implementation: `docs/old_version/signup_feature/`
- Current auth system: `backend/api/v1/common/auth.py`, `backend/common/services/auth_service.py`
- Email service: `backend/common/services/smtp_mailer.py`
- User model: `backend/common/db/models/user.py`
- Auth store (frontend): `frontend/src/common/store/authStore.ts`
- API client: `frontend/src/common/api/auth.ts`
