# -*- mode: python ; coding: utf-8 -*-
"""
QAstra PyInstaller Spec File
Bundles the launcher + backend (including static React build and Alembic migrations)
into a single QAstra.exe.
"""
block_cipher = None

import os
import sys

# SPECPATH is a PyInstaller built-in — the directory containing this .spec file
SPEC_DIR = SPECPATH
PROJECT_ROOT = os.path.normpath(os.path.join(SPEC_DIR, '..', '..'))
# Use the interpreter that runs PyInstaller (e.g. project .venv, backend\venv, or uv env)
_SITE_PACKAGES = os.path.join(sys.prefix, "Lib", "site-packages")

a = Analysis(
    [os.path.join(SPEC_DIR, 'launcher.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        # Backend code + static React build + alembic migrations
        (os.path.join(PROJECT_ROOT, 'backend'), 'backend'),
        # litellm needs its JSON data files (model cost maps, tokenizers, etc.)
        (os.path.join(_SITE_PACKAGES, 'litellm'), 'litellm'),
        # browser_use needs .md prompt templates in agent/system_prompts/
        (os.path.join(_SITE_PACKAGES, 'browser_use'), 'browser_use'),
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
        'fastapi.security',
        'fastapi.exceptions',
        'starlette',
        'starlette.staticfiles',
        'starlette.responses',
        'starlette.middleware',
        'starlette.middleware.base',
        'starlette.requests',
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
        'sqlalchemy.ext.declarative',
        'sqlalchemy.dialects.postgresql',
        'sqlalchemy.pool',
        'greenlet',
        'asyncpg',
        'asyncpg.pgproto.pgproto',
        'asyncpg.protocol.protocol',
        'psycopg2',
        'alembic',
        'alembic.config',
        'alembic.command',

        # ── Auth & Security ─────────────────────────────────────
        'jose',
        'jose.jwt',
        'passlib',
        'passlib.hash',
        'bcrypt',
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.ciphers',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.primitives.hmac',
        'cryptography.hazmat.primitives.padding',
        'cryptography.hazmat.primitives.kdf',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.openssl',
        'cffi',
        '_cffi_backend',
        'pycparser',
        'multipart',
        'python_multipart',
        'ecdsa',
        'rsa',
        'pyasn1',
        'pyasn1_modules',
        'jwt',                    # PyJWT import name
        'pyotp',
        'oauthlib',
        'requests_oauthlib',

        # ── HTTP Clients ────────────────────────────────────────
        'httpx',
        'httpx_sse',
        'httpcore',
        'h11',
        'httplib2',        'pyparsing',        'aiohttp',
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
        'tiktoken_ext',
        'tiktoken_ext.openai_public',
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
        'InquirerPy',             # correct import name for inquirerpy
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
        'google_auth_oauthlib',   # correct import name
        'google_auth_httplib2',
        'google.api',             # googleapis-common-protos import name
        'googleapiclient',        # google-api-python-client import name
        'google.protobuf',        # protobuf import name
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
        'fpdf',                   # fpdf2 import name
        'fpdf.enums',
        'reportlab',
        'PyPDF2',
        'pypdf',
        'docx',
        'markdown',
        'markdownify',
        'markdown_it',
        'mdurl',
        'lxml',
        'bs4',                    # beautifulsoup4 import name
        'soupsieve',
        'defusedxml',

        # ── File I/O & Storage ─────────────────────────────────
        'aiofiles',
        'fsspec',
        'PIL',                    # pillow import name
        'fontTools',              # fonttools import name
        'magic',                  # python-magic import name
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
        'jira',        'jira.exceptions',        'portalocker',

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
        'dotenv',                 # python-dotenv import name
        'email_validator',
        'dns',                    # dnspython import name

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

        'proto',                  # proto-plus import name
        # ── Date / Time / UUID ─────────────────────────────────
        'dateutil',
        'tzdata',
        'uuid_extensions',        # uuid7 package import name

        # ── Windows-Specific ───────────────────────────────────
        'win32api',
        'win32con',
        'pywintypes',

        # ── Python Stdlib (email) ──────────────────────────────
        'email',
        'email.mime',
        'email.mime.application',
        'email.mime.audio',
        'email.mime.base',
        'email.mime.image',
        'email.mime.message',
        'email.mime.multipart',
        'email.mime.nonmultipart',
        'email.mime.text',
        'email.message',
        'email.policy',
        'email.contentmanager',
        'email.encoders',
        'email.utils',

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
    console=True,        # Temporarily True for debugging; set False for release
    # icon='icon.ico',   # Uncomment when an icon file is added
)
