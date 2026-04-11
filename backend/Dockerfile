# Usaremos una imagen oficial de Python en su versión estable 3.12 (Ajustado según requirements.txt)
FROM python:3.12-slim

# Evitamos que Python escriba archivos .pyc y forzamos a que el log salga directamente en consola
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Instalamos primero los requirements para que Docker cachee la descarga si el código cambia
COPY requirements.txt .

# Actualizamos pip e instalamos dependencias
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiamos todo el backend
COPY . .

# Exponemos el puerto 8080 que usará Uvicorn por defecto en Fly.io
EXPOSE 8080

# Variable de entorno necesaria para indicar dónde guardará la BD. 
# Importante: Esto concuerda con nuestro nuevo os.getenv("DATABASE_URL") en config.py
ENV DATABASE_URL="sqlite:////data/atlas_v2.db"
ENV KNOWLEDGE_DB_PATH="/data/knowledge.db"

# Comando de arranque. Asumimos que application.py y app.main:app son válidos.
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "application:app", "--bind", "0.0.0.0:8080", "--timeout", "120"]
