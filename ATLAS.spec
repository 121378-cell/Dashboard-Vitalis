# -*- mode: python ; coding: utf-8 -*-
"""
ATLAS.spec - PyInstaller Configuration for ATLAS AI Dashboard
Compila launcher.py y todo el proyecto a un ejecutable independiente
"""

import sys
from pathlib import Path

# Ruta base del proyecto
project_root = Path('C:\\Users\\sergi\\Nueva carpeta\\Dashboard-Vitalis')
backend_dir = project_root / 'backend'

a = Analysis(
    [str(project_root / 'launcher.py')],
    pathex=[
        str(project_root),
        str(backend_dir),
    ],
    binaries=[],
    datas=[
        # Incluir todo el backend
        (str(backend_dir), 'backend'),
        # Incluir archivos de configuración y datos
        (str(project_root / 'package.json'), '.'),
        (str(project_root / '.env'), '.'),
    ],
    hiddenimports=[
        # FastAPI y dependencias
        'fastapi',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'uvicorn',
        'uvicorn.config',
        'uvicorn.logging',
        'uvicorn.server',
        
        # Pydantic
        'pydantic',
        'pydantic.main',
        'pydantic_core',
        
        # SQLAlchemy
        'sqlalchemy',
        'sqlalchemy.orm',
        'sqlalchemy.pool',
        'sqlalchemy.engine',
        
        # Database drivers
        'sqlite3',
        
        # API y HTTP
        'urllib',
        'urllib.request',
        'urllib.parse',
        'http.server',
        'json',
        'requests',
        
        # Modules del proyecto
        'app',
        'app.main',
        'app.core',
        'app.core.config',
        'app.core.health_check',
        'app.api',
        'app.api.api_v1',
        'app.db',
        'app.models',
        'app.services',
        'app.utils',
        
        # Google GenAI (si se usa)
        'google',
        'google.generativeai',
        
        # Otros módulos
        'dotenv',
        'pathlib',
        'logging',
        'traceback',
        'ctypes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',        # No necesario
        'asyncio',        # Incluído por defecto
        'matplotlib',     # No necesario
        'numpy',          # Solo si no se usa
        'pandas',         # Solo si no se usa
        'scipy',          # Solo si no se usa
        'pytest',         # No incluir tests
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ATLAS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ATLAS'
)
