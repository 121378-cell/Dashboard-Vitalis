"""
ATLAS Build Script
==================
Script para compilar launcher.py a ejecutable .exe con PyInstaller.
Ejecutar: python build_launcher.py
"""

import subprocess
import sys
import os
from pathlib import Path
import shutil


def build():
    """Compila launcher.py a ejecutable .exe."""
    
    print("=" * 60)
    print("   🔨 ATLAS Build System")
    print("   Compilando launcher a ejecutable...")
    print("=" * 60)
    
    root = Path(__file__).parent.absolute()
    launcher = root / "launcher.py"
    
    # Verificar que launcher.py existe
    if not launcher.exists():
        print(f"\n❌ Error: No se encontró {launcher}")
        print("   Asegúrate de que launcher.py está en la misma carpeta.")
        return 1
    
    print(f"\n📁 Proyecto: {root}")
    print(f"📄 Launcher: {launcher}")
    
    # Instalar PyInstaller si no está instalado
    print("\n📦 Verificando PyInstaller...")
    try:
        import PyInstaller
        print("   ✓ PyInstaller ya está instalado")
    except ImportError:
        print("   🔧 Instalando PyInstaller...")
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', 'pyinstaller'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("   ✓ PyInstaller instalado correctamente")
            else:
                print(f"   ⚠️ Error instalando PyInstaller: {result.stderr}")
                print("   Intentando con --break-system-packages...")
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', 'pyinstaller', '--break-system-packages'],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"   ❌ Error: {result.stderr}")
                    return 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return 1
    
    # Limpiar builds anteriores
    print("\n🧹 Limpiando builds anteriores...")
    for folder in ['build', 'dist']:
        folder_path = root / folder
        if folder_path.exists():
            try:
                shutil.rmtree(folder_path)
                print(f"   ✓ Eliminado {folder}/")
            except:
                pass
    
    # Archivos .spec antiguos
    for spec_file in root.glob('*.spec'):
        try:
            spec_file.unlink()
            print(f"   ✓ Eliminado {spec_file.name}")
        except:
            pass
    
    # Compilar
    print("\n🔨 Compilando ATLAS.exe...")
    print("   Esto puede tomar unos minutos...")
    print()
    
    try:
        result = subprocess.run(
            [
                sys.executable, '-m', 'PyInstaller',
                '--onefile',
                '--console',
                '--name', 'ATLAS',
                '--noconfirm',
                '--clean',
                str(launcher)
            ],
            cwd=str(root),
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error compilando: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        return 1
    
    # Verificar que se creó el .exe
    exe_path = root / "dist" / "ATLAS.exe"
    
    if exe_path.exists():
        # Copiar a la raíz para fácil acceso
        final_path = root / "ATLAS.exe"
        try:
            shutil.copy(exe_path, final_path)
            print(f"\n" + "=" * 60)
            print(f"   ✅ ÉXITO")
            print(f"=" * 60)
            print(f"\n   📦 Ejecutable creado:")
            print(f"      {final_path}")
            print(f"\n   🚀 Para iniciar ATLAS:")
            print(f"      Haz doble clic en ATLAS.exe")
            print(f"\n   📋 Resumen:")
            print(f"      - Backend: http://localhost:8001")
            print(f"      - Frontend: http://localhost:5173")
            print(f"      - API Docs: http://localhost:8001/docs")
            print(f"\n   💡 El ejecutable incluye:")
            print(f"      - Verificación de dependencias")
            print(f"      - Auto-limpieza de puertos")
            print(f"      - Auto-apertura de navegador")
            print(f"      - Gestión de procesos")
            print()
            return 0
        except Exception as e:
            print(f"\n⚠️  ATLAS.exe creado en dist/ pero no se pudo copiar a raíz: {e}")
            print(f"   Ubicación: {exe_path}")
            return 0
    else:
        print(f"\n❌ Error: No se encontró ATLAS.exe después de compilar")
        print("   Revisa la salida de PyInstaller para más detalles.")
        return 1


def cleanup():
    """Limpia archivos temporales de build."""
    root = Path(__file__).parent
    
    print("\n🧹 Limpiando archivos temporales...")
    
    for folder in ['build', '__pycache__']:
        folder_path = root / folder
        if folder_path.exists():
            try:
                shutil.rmtree(folder_path)
                print(f"   ✓ Eliminado {folder}/")
            except:
                pass
    
    for spec_file in root.glob('*.spec'):
        try:
            spec_file.unlink()
            print(f"   ✓ Eliminado {spec_file.name}")
        except:
            pass


if __name__ == "__main__":
    result = build()
    
    if result == 0:
        # Preguntar si limpiar
        print("¿Deseas limpiar archivos temporales de build? (s/n): ", end='')
        try:
            response = input().strip().lower()
            if response in ('s', 'si', 'sí', 'y', 'yes'):
                cleanup()
        except:
            pass
    
    input("\nPresiona Enter para salir...")
    sys.exit(result)
