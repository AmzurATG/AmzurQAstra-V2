# QAstra — Windows EXE Build Guide

## Prerequisites

| Tool       | Version   | Download |
|------------|-----------|----------|
| Python     | 3.11+     | https://www.python.org/downloads/ |
| Node.js    | 18+       | https://nodejs.org/ |
| PostgreSQL | 14+       | https://www.postgresql.org/download/ |
| Git        | latest    | https://git-scm.com/ |

---

## Step-by-Step Setup

### 1. Clone the repository

```powershell
git clone https://github.com/AmzurATG/AmzurQAstra-V2.git
cd AmzurQAstra-V2
```

### 2. Create and activate the Python virtual environment

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```powershell
pip install -r requirements.txt
pip install pyinstaller
```

### 4. Install Playwright browsers (required for browser automation)

```powershell
playwright install chromium
```

### 5. Configure environment variables

Copy the `.env.template` and fill in your values:

```powershell
copy .env.template .env
```

Edit `backend/.env` with your database credentials, secret keys, and LLM provider settings.

### 6. Set up the database

```powershell
# From the project root (with venv active)
cd ..
python database/setup_local_database.py
```

This creates the `qastra` database and application user in PostgreSQL.

### 7. Run Alembic migrations

```powershell
cd backend
alembic upgrade head
```

### 8. Create or reset the admin account

```powershell
cd ..
python database/create_or_reset_admin.py
```

### 9. Install frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

---

## Build the EXE

```powershell
cd build_exe\build_windows_exe
.\build.ps1
```

The script will:
1. Build the React frontend (`npm run build`)
2. Run PyInstaller with `qastra.spec`
3. Copy the `.env` template to `dist/`
4. Output `dist/QAstra.exe`

---

## Distribute

Copy these two files together to the target machine:

```
dist/QAstra.exe
dist/.env          # user must configure before running
```

The user edits `.env` with their database URL, secret keys, and LLM config, then double-clicks `QAstra.exe`.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `No virtual environment detected` | Run `.\venv\Scripts\Activate.ps1` first |
| `PyInstaller not found` | Run `pip install pyinstaller` |
| `PermissionError` on `QAstra.exe` during build | Kill any running QAstra process, then rebuild |
| `startup_error.log` next to the exe | Check the log — usually a missing module or data file |
| `ModuleNotFoundError` at runtime | Add the module to `hiddenimports` in `qastra.spec` and rebuild |
| Database connection errors | Verify `DATABASE_URL` in `.env` and that PostgreSQL is running |
