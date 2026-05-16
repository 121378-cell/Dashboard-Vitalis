"""
FastAPI Error Handler
=====================
Middleware y handlers para capturar excepciones de ATLAS
y devolver respuestas JSON estructuradas al cliente.
"""

import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import AtlasBaseException

logger = logging.getLogger("app.core.error_handler")


async def atlas_exception_handler(request: Request, exc: AtlasBaseException) -> JSONResponse:
    """
    Maneja excepciones del dominio ATLAS.
    Devuelve respuesta JSON con estructura consistente.
    """
    logger.exception(f"ATLAS Exception: {exc.message}")

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Sobrescribe el handler de validación de FastAPI para formato consistente.
    """
    errors = []
    for err in exc.errors():
        errors.append(
            {
                "field": " ".join(str(x) for x in err["loc"]),
                "message": err["msg"],
                "type": err["type"],
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "ValidationError",
                "message": "Error de validación en los datos enviados",
                "status_code": 422,
                "detail": {"errors": errors},
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler de último recurso para excepciones no capturadas.
    """
    tb = traceback.format_exc()
    logger.critical(f"Unhandled exception: {str(exc)}\n{tb}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "Error interno del servidor. El equipo ha sido notificado.",
                "status_code": 500,
                "detail": {},
            }
        },
    )


def register_error_handlers(app):
    """
    Registra todos los handlers de excepciones en la app FastAPI.
    Debe llamarse en app/main.py después de crear la app.
    """
    app.add_exception_handler(AtlasBaseException, atlas_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    logger.info("Handlers de errores registrados correctamente")
