"""
Dashboard-Vitalis - Backend FastAPI
====================================

Este es el punto de entrada principal para el backend de Dashboard-Vitalis.
Proporciona una API RESTful construida con FastAPI para servir datos de
biometría, readiness scores y gestión de usuarios.

Ejecución:
    uvicorn app.main:app --reload --port 8001

Endpoints principales:
    - GET /           : Health check básico
    - GET /docs       : Documentación interactiva (Swagger UI)
    - GET /redoc      : Documentación alternativa (ReDoc)

Dependencias:
    - fastapi
    - uvicorn[standard]
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ============================================================================
# CREACIÓN DE LA APLICACIÓN FASTAPI
# ============================================================================

# Instancia principal de la aplicación FastAPI
# - title: Nombre que aparece en la documentación
# - description: Descripción detallada de la API
# - version: Versión semántica de la API
app = FastAPI(
    title="Dashboard-Vitalis API",
    description="API para Dashboard-Vitalis - Sistema de gestión de biometría y readiness scores",
    version="1.0.0",
)

# ============================================================================
# CONFIGURACIÓN CORS (Cross-Origin Resource Sharing)
# ============================================================================

# Permite que el frontend (Vite en puerto 5173) se comunique con el backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],  # Todos los métodos HTTP (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Todos los headers permitidos
)

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """
    Endpoint raíz - Health check básico.
    
    Returns:
        dict: Mensaje confirmando que el backend está funcionando.
    """
    return {"message": "Backend funcionando"}


@app.get("/health")
async def health_check():
    """
    Endpoint de verificación de salud del sistema.
    
    Returns:
        dict: Estado del sistema y timestamp.
    """
    from datetime import datetime
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "Dashboard-Vitalis API"
    }


# ============================================================================
# INCLUIR RUTAS ADICIONALES (cuando existan)
# ============================================================================

# Ejemplo de cómo incluir routers adicionales:
# from app.api.api_v1.api import api_router
# app.include_router(api_router, prefix="/api/v1")

# ============================================================================
# PUNTO DE ENTRADA PARA EJECUCIÓN DIRECTA
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    # Ejecutar directamente: python -m app.main
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
