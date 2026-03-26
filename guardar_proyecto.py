# guardar_proyecto.py
import os

def guardar_estructura(ruta, output="proyecto_completo.txt"):
    with open(output, "w", encoding="utf-8") as f:
        for root, dirs, files in os.walk(ruta):
            # Ignorar carpetas virtuales o de sistema
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv']]
            level = root.replace(ruta, '').count(os.sep)
            indent = ' ' * 2 * level
            f.write(f"{indent}{os.path.basename(root)}/\n")
            for file in files:
                if file.endswith(('.py', '.js', '.json', '.yml', '.yaml', '.toml', '.txt')):
                    filepath = os.path.join(root, file)
                    f.write(f"{indent}  📄 {file}\n")
                    try:
                        with open(filepath, 'r', encoding="utf-8") as src:
                            contenido = src.read()
                            f.write(f"```{file.split('.')[-1]}\n{contenido}\n```\n\n")
                    except Exception as e:
                        f.write(f"⚠️ Error leyendo {file}: {e}\n\n")

if __name__ == "__main__":
    guardar_estructura(".")
    print("✅ Archivo 'proyecto_completo.txt' generado correctamente.")