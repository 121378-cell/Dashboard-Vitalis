"""
ATLAS AI Personal Trainer Launcher
====================================
Script principal que inicia toda la aplicación ATLAS.
Se compila a ejecutable .exe con PyInstaller.
"""

import subprocess
import sys
import os
import time
import webbrowser
import signal
from pathlib import Path
import urllib.request
import ctypes


def set_console_title(title):
    """Establece el título de la ventana de consola."""
    ctypes.windll.kernel32.SetConsoleTitleW(title)


def find_project_root():
    """Encuentra la raíz del proyecto."""
    # Si está compilado (frozen), usar el directorio del .exe
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.absolute()


def find_npm():
    """Busca npm en rutas típicas de Windows."""
    import shutil
    
    # Primero intentar en PATH normal
    npm = shutil.which('npm')
    if npm:
        return npm
    
    # Rutas típicas de Node.js en Windows
    common_paths = [
        r"C:\Program Files\nodejs\npm.cmd",
        r"C:\Program Files\nodejs\npm",
        r"C:\Program Files (x86)\nodejs\npm.cmd",
        os.path.expanduser(r"~\AppData\Roaming\npm\npm.cmd"),
        os.path.expanduser(r"~\AppData\Local\Programs\nodejs\npm.cmd"),
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None


def kill_process_by_name(name):
    """Mata procesos por nombre."""
    try:
        subprocess.run(
            ['taskkill', '/F', '/IM', f'{name}.exe'],
            capture_output=True,
            text=True
        )
    except:
        pass


def kill_port(port):
    """Mata el proceso que está escuchando en un puerto específico."""
    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True, text=True, encoding='utf-8', errors='ignore'
        )
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        subprocess.run(
                            ['taskkill', '/F', '/PID', pid],
                            capture_output=True
                        )
                        print(f"   ✓ Proceso en puerto {port} (PID {pid}) terminado")
                    except:
                        pass
    except Exception as e:
        print(f"   ⚠ No se pudo liberar puerto {port}: {e}")


def wait_for_backend(url, timeout=30):
    """Espera a que el backend responda."""
    for i in range(timeout):
        try:
            response = urllib.request.urlopen(url, timeout=2)
            if response.status == 200:
                return True
        except:
            pass
        time.sleep(1)
        print(f"   Esperando... ({i + 1}/{timeout}s)", end='\r')
    print()  # Nueva línea después del progreso
    return False


def check_dependencies():
    """Verifica que Python y Node.js estén disponibles."""
    print("\n🔍 Verificando dependencias...")
    
    # Verificar Python
    try:
        result = subprocess.run(
            ['python', '--version'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"   ✓ Python: {result.stdout.strip()}")
        else:
            print("   ⚠️ Python no encontrado en PATH")
            return False
    except FileNotFoundError:
        print("   ❌ Python no está instalado o no está en PATH")
        return False
    
    # Verificar Node.js
    try:
        result = subprocess.run(
            ['node', '--version'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"   ✓ Node.js: {result.stdout.strip()}")
        else:
            print("   ⚠️ Node.js no encontrado en PATH")
            return False
    except FileNotFoundError:
        print("   ❌ Node.js no está instalado o no está en PATH")
        return False
    
    # Verificar npm
    npm_path = find_npm()
    if npm_path:
        try:
            result = subprocess.run(
                [npm_path, '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"   ✓ npm: {result.stdout.strip()}")
            else:
                print("   ⚠️ npm no responde correctamente")
                return False
        except Exception as e:
            print(f"   ⚠️ Error verificando npm: {e}")
            return False
    else:
        print("   ❌ npm no encontrado en PATH ni en rutas típicas")
        return False
    
    return True


def main():
    # Establecer título de la ventana
    set_console_title("ATLAS — Iniciando...")
    
    # Encontrar raíz del proyecto
    root = find_project_root()
    backend_dir = root / "backend"
    
    # Banner
    print("=" * 50)
    print("   🤖 ATLAS AI Personal Trainer")
    print("   Iniciando sistema...")
    print("=" * 50)
    
    # Verificar estructura del proyecto
    if not backend_dir.exists():
        print(f"\n❌ Error: No se encontró el directorio backend en {root}")
        print("   Asegúrate de que ATLAS.exe está en la raíz del proyecto.")
        input("\nPresiona Enter para salir...")
        return 1
    
    if not (backend_dir / "app" / "main.py").exists():
        print(f"\n❌ Error: No se encontró backend/app/main.py")
        print("   El proyecto parece estar incompleto.")
        input("\nPresiona Enter para salir...")
        return 1
    
    # Verificar dependencias
    if not check_dependencies():
        print("\n❌ Faltan dependencias necesarias.")
        print("   Instala Python y Node.js para continuar.")
        input("\nPresiona Enter para salir...")
        return 1
    
    # Matar procesos previos
    print("\n🔄 Liberando puertos...")
    print("   Terminando procesos Python previos...")
    kill_process_by_name('python')
    print("   Terminando procesos Node previos...")
    kill_process_by_name('node')
    time.sleep(1)
    
    # Matar procesos en puertos específicos
    kill_port(8005)
    kill_port(5173)
    time.sleep(1)
    
    # Variables para procesos
    backend_proc = None
    frontend_proc = None
    
    try:
        # Arrancar backend
        print("\n🚀 Arrancando backend FastAPI...")
        print(f"   Directorio: {backend_dir}")
        print("   Puerto: 8005")
        
        backend_proc = subprocess.Popen(
            ['python', '-m', 'uvicorn', 'app.main:app', '--port', '8005', '--host', '127.0.0.1'],
            cwd=str(backend_dir),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Esperar backend
        print("\n⏳ Esperando que el backend esté listo...")
        if wait_for_backend("http://localhost:8005/health"):
            print("   ✅ Backend listo y respondiendo")
        else:
            print("   ⚠️  Backend tardando más de lo esperado, continuando...")
        
        # Arrancar frontend
        print("\n🚀 Arrancando frontend Vite...")
        print(f"   Directorio: {root}")
        print("   Puerto: 5173")
        
        npm_path = find_npm()
        if not npm_path:
            print("❌ npm no encontrado. No se puede iniciar el frontend.")
            return 1
        
        frontend_proc = subprocess.Popen(
            [npm_path, 'run', 'dev'],
            cwd=str(root),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Esperar frontend
        print("\n⏳ Esperando que el frontend arranque...")
        time.sleep(4)
        print("   ✅ Frontend iniciado")
        
        # Abrir navegador
        print("\n🌐 Abriendo navegador...")
        webbrowser.open("http://localhost:5173")
        
        # Cambiar título de ventana
        set_console_title("ATLAS — En ejecución")
        
        # Mostrar resumen
        print("\n" + "=" * 50)
        print("   ✅ ATLAS está corriendo")
        print(f"   📡 Backend:  http://localhost:8005")
        print(f"   🎨 Frontend: http://localhost:5173")
        print(f"   📚 API Docs: http://localhost:8005/docs")
        print("\n   💡 Cierra esta ventana para detener ATLAS")
        print("=" * 50)
        
        # Mantener vivo y manejar cierre
        print("\n   (Presiona Ctrl+C para detener)\n")
        
        while True:
            time.sleep(1)
            # Verificar que los procesos siguen vivos
            if backend_proc.poll() is not None:
                print("\n⚠️  Backend se detuvo inesperadamente")
                break
            if frontend_proc.poll() is not None:
                print("\n⚠️  Frontend se detuvo inesperadamente")
                break
                
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupción detectada...")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("\n🧹 Deteniendo procesos...")
        
        if backend_proc:
            print("   Terminando backend...")
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=5)
            except:
                backend_proc.kill()
        
        if frontend_proc:
            print("   Terminando frontend...")
            frontend_proc.terminate()
            try:
                frontend_proc.wait(timeout=5)
            except:
                frontend_proc.kill()
        
        # Asegurar que no queden procesos huérfanos
        kill_process_by_name('python')
        kill_process_by_name('node')
        kill_port(8005)
        kill_port(5173)
        
        print("\n👋 ATLAS se ha detenido. ¡Hasta pronto!")
        time.sleep(2)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
