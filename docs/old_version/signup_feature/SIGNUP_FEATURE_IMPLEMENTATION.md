# Signup Feature — End-to-End Implementation

## File Structure

```
AmzurQAstra/
│
├── backend/
│   ├── main.py                                       # Route registration
│   ├── config.py                                     # Email/SMTP, JWT, Supabase config
│   ├── models.py                                     # UserCreate, SecurityQuestion, OTPVerify models
│   ├── db.py                                         # Database operations (create_user, verify_user, email_exists)
│   ├── schema.sql                                    # users, security_questions, reset_tokens tables
│   │
│   ├── routes/
│   │   └── auth_routes.py                            # Signup API endpoints (~500 lines)
│   │       ├── POST /signup                          #   → Create pending user + send OTP
│   │       ├── POST /verify-otp                      #   → Verify OTP + create user in DB
│   │       ├── POST /resend-otp                      #   → Regenerate and resend OTP
│   │       └── POST /check-email                     #   → Check if email already registered
│   │
│   └── services/
│       └── authentication.py                         # OTP generation, storage, email sending (~300 lines)
│
└── frontend/
    └── src/
        ├── App.js                                    # Route mapping
        │
        ├── components/
        │   ├── SignupForm.js                         # Step 1: Registration form + validation
        │   ├── SecurityQuestions.js                   # Step 2: Security Q&A collection
        │   └── VerifyEmail.js                        # Step 3: 6-digit OTP verification
        │
        └── utils/
            └── routes/
                └── routes.js                         # /signup, /security-questions, /verify-email
```

---

## User Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          SIGNUP FLOW (3 STEPS)                           │
│                                                                          │
│  Step 1                  Step 2                  Step 3                   │
│  ┌──────────────┐       ┌──────────────────┐    ┌──────────────────┐    │
│  │ SignupForm.js │──────▶│SecurityQuestions  │───▶│  VerifyEmail.js  │    │
│  │              │       │     .js           │    │                  │    │
│  │ • First Name │       │ • Question 1     │    │ • 6-digit OTP    │    │
│  │ • Last Name  │       │ • Answer 1       │    │ • Auto-focus     │    │
│  │ • Company    │       │ • Question 2     │    │ • Paste support  │    │
│  │ • Email      │       │ • Answer 2       │    │ • 30s resend     │    │
│  │ • Phone      │       │                  │    │ • 3-attempt lock │    │
│  │ • Password   │       │                  │    │                  │    │
│  └──────┬───────┘       └────────┬─────────┘    └────────┬─────────┘    │
│         │                        │                       │               │
│    POST /check-email        POST /signup           POST /verify-otp     │
│         │                        │                       │               │
└─────────┼────────────────────────┼───────────────────────┼───────────────┘
          │                        │                       │
          ▼                        ▼                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ BACKEND (auth_routes.py + authentication.py)                             │
│                                                                          │
│  /check-email          /signup                    /verify-otp            │
│       │                    │                           │                 │
│  Check users table    ┌────┴─────┐              ┌─────┴──────┐          │
│       │               │ Lockout? │              │ Lockout?   │          │
│       ▼               └────┬─────┘              └─────┬──────┘          │
│  {exists: bool}            │                          │                 │
│                    Store in pending_user       Verify OTP (5-min TTL)   │
│                    _registrations{}                    │                 │
│                            │                   Create user in DB        │
│                    Generate 6-digit OTP        (bcrypt password)        │
│                            │                          │                 │
│                    Send email via SMTP         Store security Q&A       │
│                            │                   (answers bcrypt hashed)  │
│                            ▼                          │                 │
│                    {message: "OTP sent"}       Mark is_verified = true  │
│                                                       │                 │
│                                                Clean up pending data    │
│                                                       │                 │
│                                                {success: true}          │
└──────────────────────────────────────────────────────────────────────────┘
          │                        │                       │
          ▼                        ▼                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ DATABASE (Supabase/PostgreSQL)                                           │
│                                                                          │
│  users                     security_questions        reset_tokens        │
│  ├─ id (UUID PK)           ├─ id (UUID PK)          ├─ id (UUID PK)    │
│  ├─ first_name             ├─ user_id (FK→users)    ├─ user_id (FK)    │
│  ├─ last_name              ├─ question               ├─ token           │
│  ├─ company_name           ├─ answer (hashed)        ├─ expires_at      │
│  ├─ email (UNIQUE)         └─ created_at             ├─ used            │
│  ├─ country_code                                     └─ created_at      │
│  ├─ phone_number                                                        │
│  ├─ password (hashed)                                                   │
│  ├─ is_verified                                                         │
│  ├─ created_at                                                          │
│  └─ updated_at                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### POST `/check-email`

**Purpose:** Pre-signup check if email is already registered

**Input:**
```json
{ "email": "user@company.com" }
```

**Output:**
```json
{ "exists": true, "email": "user@company.com" }
```

---

### POST `/signup`

**Purpose:** Register pending user and send OTP email

**Input:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "company_name": "Acme Corp",
  "email": "john@acme.com",
  "country_code": "+1",
  "phone_number": "5551234567",
  "password": "P@ssw0rd!",
  "confirm_password": "P@ssw0rd!",
  "security_questions": [
    { "question": "What was the name of your first pet?", "answer": "Rex" },
    { "question": "What city were you born in?", "answer": "Austin" }
  ]
}
```

**Output:**
```json
{ "message": "Verification code sent to john@acme.com", "email": "john@acme.com" }
```

**Process:**
1. Check OTP lockout status (3 attempts → 5-min cooldown)
2. Check if email already registered in DB
3. Store user data in `pending_user_registrations` (in-memory dict)
4. Generate 6-digit OTP, store with 5-min expiry
5. Send OTP via SMTP email

---

### POST `/verify-otp`

**Purpose:** Verify OTP and create the user in the database

**Input:**
```json
{ "email": "john@acme.com", "otp": "482915" }
```

**Output (success):**
```json
{ "detail": "Email verified successfully", "success": true }
```

**Output (failure):**
```json
{ "detail": "Invalid verification code. 2 attempts remaining.", "success": false }
```

**Process:**
1. Check lockout (3 wrong attempts = 5-min lockout)
2. Verify OTP matches and hasn't expired (5-min TTL)
3. Retrieve pending user data
4. Create user in DB with bcrypt-hashed password
5. Store security questions (answers hashed with bcrypt)
6. Mark `is_verified = true`
7. Clean up pending registration and OTP data

---

### POST `/resend-otp`

**Purpose:** Generate and send a new OTP

**Input:**
```json
{ "email": "john@acme.com" }
```

**Output:**
```json
{ "message": "New verification code sent", "email": "john@acme.com" }
```

---

## Data Models

### UserCreate (Pydantic)

```python
class UserCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    email: EmailStr
    country_code: Optional[str] = None
    phone_number: Optional[str] = None
    password: str
    confirm_password: str
    security_questions: Optional[List[SecurityQuestion]] = []
```

**Validators:**

| Field | Rule |
|-------|------|
| `email` | Business only — blocks gmail.com, yahoo.com, hotmail.com, outlook.com, aol.com; domain must match company name |
| `password` | 8-64 chars, must include uppercase + lowercase + number + special char |
| `confirm_password` | Must match `password` |
| `phone_number` | Country-specific digit count (e.g., 10 for India, 7-15 range) |
| `company_name` | 2-100 chars, allows alphanumeric + special chars |

### SecurityQuestion (Pydantic)

```python
class SecurityQuestion(BaseModel):
    id: Optional[str] = None
    question: str
    answer: str
```

### OTPVerify (Pydantic)

```python
class OTPVerify(BaseModel):
    email: EmailStr
    otp: str       # Must be exactly 6 digits

    @validator('otp')
    def validate_otp(cls, v):
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError('OTP must be exactly 6 digits')
        return v
```

---

## Database Schema

### users

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  company_name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  country_code TEXT,
  phone_number TEXT,
  password TEXT NOT NULL,
  is_verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_users_email ON users(email);
```

### security_questions

```sql
CREATE TABLE security_questions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,          -- bcrypt hashed
  created_at TIMESTAMP DEFAULT NOW()
);
```

### reset_tokens

```sql
CREATE TABLE reset_tokens (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  token TEXT NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  used BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Backend Services

### OTP Management (`authentication.py`)

**In-memory storage:**
```python
otp_store: Dict[str, Dict] = {}
# Structure: { "email": { "otp": "123456", "expiry": datetime } }
```

| Function | Purpose |
|----------|---------|
| `generate_otp(length=6)` | Returns random 6-digit string |
| `store_otp(email, otp)` | Stores OTP with 5-min expiry (from `OTP_EXPIRY_MINUTES` config) |
| `verify_otp(email, otp)` | Returns `True`, `"invalid"`, or `"expired"` |

### Email Sending (`authentication.py`)

```python
def send_otp_email(to_email: str, otp: str):
    """Sends HTML email with verification code via SMTP"""
```

**Email Template:**
```html
<h2>Welcome to QAstra!</h2>
<p>Thank you for signing up. Please use the verification code below:</p>
<h1 style="background-color: #f0f0f0; padding: 10px;
           font-family: monospace;">123456</h1>
<p>This code will expire in 5 minutes.</p>
```

### Pending Registration Storage (`auth_routes.py`)

```python
pending_user_registrations = {}
# Structure: { "email": { full UserCreate data + security_questions } }
```

### Account Lockout Tracking (`auth_routes.py`)

```python
otp_attempts = {}
# Structure: { "email": { "count": 2, "locked_until": datetime } }

MAX_OTP_ATTEMPTS = 3
OTP_LOCKOUT_DURATION = 5  # minutes
```

---

## Frontend Validation Details

### SignupForm.js — Step 1

| Field | Validation |
|-------|------------|
| First / Last Name | Required |
| Company Name | 2-100 chars |
| Email | Business domain only; domain must match company name (e.g., company "test" → email must be `*@test.com`) |
| Phone | Country-specific digit count |
| Password | 8+ chars, uppercase, lowercase, number, special char, max 64 |
| Confirm Password | Must match password |

**Blocked email domains:** gmail.com, yahoo.com, hotmail.com, outlook.com, aol.com, icloud.com, protonmail.com, mail.com, zoho.com, yandex.com

### SecurityQuestions.js — Step 2

**Available questions (choose 2):**
1. What was the name of your first pet?
2. What city were you born in?
3. What was your mother's maiden name?
4. What was the name of your elementary school?
5. What is your favorite color?

- Both questions must be different
- Answers are required

### VerifyEmail.js — Step 3

| Feature | Detail |
|---------|--------|
| Input | 6 individual digit fields with auto-focus |
| Paste | Supports pasting full OTP code |
| Auto-submit | Submits when all 6 digits entered |
| Navigation | Backspace + arrow key support |
| Resend cooldown | 30-second timer between resends |
| Lockout | 3 failed attempts → 5-minute lockout with countdown |
| Persistence | Lockout state saved in localStorage |

---

## Security Summary

| Feature | Implementation |
|---------|----------------|
| Password hashing | bcrypt with salt |
| Security question answers | bcrypt hashed (case-insensitive comparison) |
| OTP | 6-digit random, 5-minute expiry |
| Lockout | 3 failed OTP attempts → 5-minute server-side + client-side lockout |
| Email validation | Business domains only; free providers blocked |
| Phone validation | Country-specific digit count enforcement |
| Pending data | In-memory dict (cleared on server restart) |
| JWT | 30-day expiry after login; contains user_id + email |

---

## Configuration (`config.py`)

```python
# Email / SMTP
EMAIL_HOST     = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT     = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM     = os.getenv("EMAIL_FROM")
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", 5))

# Auth
JWT_SECRET         = os.getenv("JWT_SECRET", "...")
SUPABASE_URL       = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE")
```

---

## Notes

- OTP and pending registrations are stored **in-memory** — a server restart clears unverified signups. Use Redis or a persistent store for production.
- No LLM prompts are used in the signup flow.
- The `reset_tokens` table supports a separate password-reset flow (not part of signup, but related).
