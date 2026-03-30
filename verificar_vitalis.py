#!/usr/bin/env python3
"""
VITALIS - Script de Verificación Automatizada
==============================================
Verifica que todos los componentes estén configurados correctamente.
"""

import os
import sys
import json
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime

# Colores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text):
    print(f"{BLUE}ℹ️  {text}{RESET}")

def check_python():
    """Verifica versión de Python"""
    print_header("1. Verificando Python")
    
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 8:
        print_success(f"Python {version.major}.{version.minor} es compatible")
        return True
    else:
        print_error(f"Requiere Python 3.8+, tienes {version.major}.{version.minor}")
        return False

def check_node():
    """Verifica Node.js"""
    print_header("2. Verificando Node.js/npm")
    
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
        print(f"Node: {result.stdout.strip()}")
        print_success("Node.js encontrado")
        
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True, timeout=5)
        print(f"npm: {result.stdout.strip()}")
        print_success("npm encontrado")
        return True
    except Exception as e:
        print_error(f"Node.js o npm no encontrado: {e}")
        return False

def check_dependencies():
    """Verifica dependencias Python"""
    print_header("3. Verificando Dependencias Python")
    
    required = [
        'fastapi',
        'sqlalchemy',
        'garminconnect',
        'garth',
        'pydantic',
        'uvicorn'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
            print_success(package)
        except ImportError:
            print_error(f"{package} NO INSTALADO")
            missing.append(package)
    
    if missing:
        print_warning(f"Falta instalar: {', '.join(missing)}")
        print_info("Ejecuta: pip install -r backend/requirements.txt")
        return False
    
    print_success("Todas las dependencias Python instaladas")
    return True

def check_env_file():
    """Verifica archivo .env"""
    print_header("4. Verificando Credenciales (.env)")
    
    env_path = Path("backend/.env")
    
    if not env_path.exists():
        print_error(".env NO EXISTE")
        print_warning("Crea backend/.env con:")
        print("""
GROQ_API_KEY=tu_clave_aqui
# O
GEMINI_API_KEY=tu_clave_aqui
# O deja en blanco para usar Ollama local
OLLAMA_BASE_URL=http://localhost:11434
""")
        return False
    
    # Leer y verificar
    with open(env_path) as f:
        content = f.read()
    
    has_groq = 'GROQ_API_KEY' in content and len(content.split('GROQ_API_KEY=')[1].split('\n')[0].strip()) > 10
    has_gemini = 'GEMINI_API_KEY' in content and len(content.split('GEMINI_API_KEY=')[1].split('\n')[0].strip()) > 10
    
    if has_groq:
        print_success(".env contiene Groq API Key (válida)")
        return True
    elif has_gemini:
        print_success(".env contiene Gemini API Key (válida)")
        return True
    else:
        print_warning(".env existe pero no tiene credenciales de IA válidas")
        print_info("Configurará fallback a Ollama local (más lento)")
        return True

def check_garmin_tokens():
    """Verifica tokens de Garmin"""
    print_header("5. Verificando Tokens Garmin (.garth)")
    
    garth_dir = Path("backend/.garth")
    
    if not garth_dir.exists():
        print_error(".garth NO EXISTE")
        print_warning("No podrá sincronizar con Garmin")
        print_info("Debes obtener tokens de Connect.Garmin.com y guardarlos en backend/.garth/")
        return False
    
    oauth1 = garth_dir / "oauth1_token.json"
    oauth2 = garth_dir / "oauth2_token.json"
    
    if oauth1.exists() and oauth2.exists():
        print_success("Tokens Garmin encontrados")
        return True
    else:
        print_error("Faltan tokens en .garth/")
        if not oauth1.exists():
            print_error("  - oauth1_token.json")
        if not oauth2.exists():
            print_error("  - oauth2_token.json")
        return False

def check_database():
    """Verifica base de datos"""
    print_header("6. Verificando Base de Datos")
    
    db_path = Path("atlas_v2.db")
    
    if not db_path.exists():
        print_error("atlas_v2.db NO EXISTE")
        print_info("Ejecuta: python backend/init_db_script.py")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['user', 'biometrics', 'workout', 'training_session']
        missing = [t for t in required_tables if t not in tables]
        
        if missing:
            print_error(f"Tablas faltantes: {missing}")
            conn.close()
            return False
        
        print_success(f"Base de datos con {len(tables)} tablas ✓")
        
        # Verificar usuarios
        cursor.execute("SELECT COUNT(*) FROM user;")
        user_count = cursor.fetchone()[0]
        if user_count > 0:
            print_success(f"Usuarios en DB: {user_count}")
        else:
            print_warning("No hay usuarios en la base de datos")
        
        conn.close()
        return True
        
    except Exception as e:
        print_error(f"Error accediendo a DB: {e}")
        return False

def check_ports():
    """Verifica si puertos están disponibles"""
    print_header("7. Verificando Puertos Disponibles")
    
    ports_to_check = {
        8001: "Backend FastAPI",
        5173: "Frontend Vite",
        11434: "Ollama (opcional)"
    }
    
    all_available = True
    for port, name in ports_to_check.items():
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                print_warning(f"Puerto {port} ({name}) YA EN USO")
                all_available = False
            else:
                print_success(f"Puerto {port} ({name}) disponible")
        except Exception as e:
            print_error(f"Error verificando puerto {port}: {e}")
            all_available = False
    
    return all_available

def check_npm_packages():
    """Verifica paquetes npm"""
    print_header("8. Verificando Paquetes npm")
    
    package_json = Path("package.json")
    
    if not package_json.exists():
        print_error("package.json NO EXISTE")
        return False
    
    try:
        with open(package_json) as f:
            data = json.load(f)
        
        deps = len(data.get('dependencies', {}))
        devdeps = len(data.get('devDependencies', {}))
        
        node_modules = Path("node_modules")
        
        if not node_modules.exists():
            print_error("node_modules NO EXISTE - run npm install")
            return False
        
        print_success(f"package.json OK: {deps} dependencies, {devdeps} devDependencies")
        return True
        
    except Exception as e:
        print_error(f"Error verificando package.json: {e}")
        return False

def check_backend_structure():
    """Verifica estructura del backend"""
    print_header("9. Verificando Estructura Backend")
    
    required_files = [
        "backend/app/main.py",
        "backend/app/core/config.py",
        "backend/app/db/session.py",
        "backend/app/models/user.py",
        "backend/app/services/ai_service.py",
        "backend/app/api/api_v1/endpoints/ai.py",
        "backend/app/api/api_v1/endpoints/sync.py",
        "backend/auto_sync.py"
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print_success(file_path)
        else:
            print_error(f"{file_path} NO EXISTE")
            all_exist = False
    
    return all_exist

def check_frontend_structure():
    """Verifica estructura del frontend"""
    print_header("10. Verificando Estructura Frontend")
    
    required_files = [
        "src/App.tsx",
        "src/main.tsx",
        "src/components/Chat.tsx",
        "src/services/aiService.ts",
        "src/types.ts",
        "vite.config.ts"
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print_success(file_path)
        else:
            print_error(f"{file_path} NO EXISTE")
            all_exist = False
    
    return all_exist

def run_all_checks():
    """Ejecuta toda la verificación"""
    print(f"{BOLD}{BLUE}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║      VITALIS - VERIFICACIÓN DE SISTEMA COMPLETO         ║")
    print(f"║      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                        ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{RESET}")
    
    results = {
        "Python": check_python(),
        "Node.js": check_node(),
        "Dependencias Python": check_dependencies(),
        ".env Credenciales": check_env_file(),
        "Tokens Garmin": check_garmin_tokens(),
        "Base de Datos": check_database(),
        "Puertos Disponibles": check_ports(),
        "Paquetes npm": check_npm_packages(),
        "Backend Estructura": check_backend_structure(),
        "Frontend Estructura": check_frontend_structure()
    }
    
    # Resumen final
    print_header("RESUMEN FINAL")
    
    print(f"\n{BOLD}Estado de Componentes:{RESET}\n")
    for component, status in results.items():
        if status:
            print(f"  {GREEN}✓{RESET} {component}")
        else:
            print(f"  {RED}✗{RESET} {component}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    percentage = (passed / total) * 100
    
    print(f"\n{BOLD}Resultado: {passed}/{total} correctos ({percentage:.0f}%){RESET}\n")
    
    if passed == total:
        print(f"{GREEN}{BOLD}🎉 SISTEMA COMPLETAMENTE OPERATIVO!{RESET}")
        print(f"{GREEN}Puedes ejecutar: start_vitalis.bat{RESET}\n")
        return 0
    elif passed >= 8:
        print(f"{YELLOW}{BOLD}⚠️  SISTEMA PARCIALMENTE OPERATIVO{RESET}")
        print(f"{YELLOW}Faltan configuraciones menores. Revisa arriba.{RESET}\n")
        return 1
    else:
        print(f"{RED}{BOLD}❌ SISTEMA NO OPERATIVO{RESET}")
        print(f"{RED}Requiere configuración significativa.{RESET}\n")
        return 2

if __name__ == "__main__":
    exit_code = run_all_checks()
    sys.exit(exit_code)
