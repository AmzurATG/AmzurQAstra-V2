# -*- mode: python ; coding: utf-8 -*-
"""
QAstra PyInstaller Spec File
Bundles the launcher + backend (including static React build and Alembic migrations)
into a single QAstra.exe.
"""
block_cipher = None

import os
SPEC_DIR = os.path.dirname(os.path.abspath(SPECPATH if 'SPECPATH' in dir() else '__file__'))
PROJECT_ROOT = os.path.normpath(os.path.join(SPEC_DIR, '..', '..'))

a = Analysis(
    [os.path.join(SPEC_DIR, 'launcher.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        # Backend code + static React build + alembic migrations
        (os.path.join(PROJECT_ROOT, 'backend'), 'backend'),
    ],
    hiddenimports=[
        # =====================================================================
        # Complete hidden imports — derived from a clean venv install of
        # backend/requirements.txt (170 packages, direct + transitive).
        # =====================================================================

        # ── Uvicorn & ASGI ──────────────────────────────────────
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'watchfiles',
        'websockets',
        'httptools',

        # ── FastAPI / Starlette ─────────────────────────────────
        'fastapi',
        'fastapi.staticfiles',
        'fastapi.responses',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'starlette',
        'starlette.staticfiles',
        'starlette.responses',
        'starlette.middleware',
        'sse_starlette',

        # ── Pydantic ────────────────────────────────────────────
        'pydantic',
        'pydantic.fields',
        'pydantic_core',
        'pydantic_settings',
        'annotated_types',
        'typing_extensions',
        'typing_inspection',

        # ── Database ────────────────────────────────────────────
        'sqlalchemy',
        'sqlalchemy.ext.asyncio',
        'sqlalchemy.dialects.postgresql',
        'sqlalchemy.pool',
        'greenlet',
        'asyncpg',
        'psycopg2',
        'alembic',
        'alembic.config',
        'alembic.command',

        # ── Auth & Security ─────────────────────────────────────
        'jose',
        'jose.jwt',
        'python_jose',
        'passlib',
        'passlib.hash',
        'bcrypt',
        'cryptography',
        'cffi',
        'pycparser',
        'multipart',
        'python_multipart',
        'ecdsa',
        'rsa',
        'pyasn1',
        'pyasn1_modules',
        'pyjwt',
        'pyotp',
        'oauthlib',
        'requests_oauthlib',

        # ── HTTP Clients ────────────────────────────────────────
        'httpx',
        'httpx_sse',
        'httpcore',
        'h11',
        'httplib2',
        'aiohttp',
        'aiosignal',
        'aiohappyeyeballs',
        'multidict',
        'yarl',
        'frozenlist',
        'propcache',
        'requests',
        'requests_toolbelt',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'idna',

        # ── LLM Integrations ───────────────────────────────────
        'openai',
        'anthropic',
        'litellm',
        'tiktoken',
        'tokenizers',
        'ollama',
        'groq',

        # ── LiteLLM Ecosystem (transitive) ─────────────────────
        'posthog',
        'cloudpickle',
        'jiter',
        'distro',
        'sniffio',
        'anyio',
        'backoff',
        'docstring_parser',
        'inquirerpy',
        'pfzy',
        'prompt_toolkit',
        'wcwidth',

        # ── MCP ─────────────────────────────────────────────────
        'mcp',

        # ── Google / Gemini (litellm transitive) ───────────────
        'google.genai',
        'google.api_core',
        'google.auth',
        'google.auth.transport',
        'google.auth.oauthlib',
        'google_auth_httplib2',
        'googleapis_common_protos',
        'google_api_python_client',
        'proto',
        'protobuf',
        'uritemplate',

        # ── Browser Automation ──────────────────────────────────
        'browser_use',
        'browser_use_sdk',
        'cdp_use',
        'bubus',
        'playwright',
        'pyee',
        'screeninfo',

        # ── Document Handling ───────────────────────────────────
        'fpdf2',
        'reportlab',
        'PyPDF2',
        'pypdf',
        'docx',
        'markdown',
        'markdownify',
        'markdown_it',
        'mdurl',
        'lxml',
        'beautifulsoup4',
        'bs4',
        'soupsieve',
        'defusedxml',

        # ── File I/O & Storage ─────────────────────────────────
        'aiofiles',
        'fsspec',
        'pillow',
        'PIL',
        'fonttools',
        'python_magic',
        'filelock',

        # ── AWS / S3 ───────────────────────────────────────────
        'aioboto3',
        'aiobotocore',
        'aioitertools',
        'boto3',
        'botocore',
        's3transfer',
        'jmespath',

        # ── Jira Integration ───────────────────────────────────
        'jira',
        'portalocker',

        # ── Redis / Celery ─────────────────────────────────────
        'redis',
        'celery',
        'kombu',
        'amqp',
        'vine',
        'billiard',
        'click',
        'click_didyoumean',
        'click_plugins',
        'click_repl',

        # ── HuggingFace ────────────────────────────────────────
        'huggingface_hub',
        'hf_xet',
        'tqdm',

        # ── CLI & Output ───────────────────────────────────────
        'typer',
        'rich',
        'pygments',
        'shellingham',
        'colorama',

        # ── Environment & Config ───────────────────────────────
        'dotenv',
        'python_dotenv',
        'email_validator',
        'dnspython',

        # ── Template Engines ───────────────────────────────────
        'jinja2',
        'markupsafe',
        'mako',

        # ── Validation & Serialization ─────────────────────────
        'jsonschema',
        'jsonschema_specifications',
        'referencing',
        'rpds',
        'regex',
        'yaml',
        'tenacity',
        'packaging',
        'six',

        # ── Date / Time / UUID ─────────────────────────────────
        'dateutil',
        'tzdata',
        'uuid7',

        # ── Windows-Specific ───────────────────────────────────
        'pywin32',
        'win32api',
        'win32con',
        'pywintypes',

        # ── Misc Transitive ────────────────────────────────────
        'importlib_metadata',
        'zipp',
        'fastuuid',
        'annotated_doc',
        'psutil',
        'attrs',
        'wrapt',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='QAstra',
    debug=False,
    strip=False,
    upx=True,
    console=False,       # No terminal window
    icon='icon.ico',     # Optional — remove if no icon file exists
)
