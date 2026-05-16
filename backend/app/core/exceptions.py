"""
ATLAS Custom Exceptions
==========================
Jerarquía de excepciones para el dominio de fitness.
Permite manejo granular de errores y respuestas HTTP consistentes.
"""

from fastapi import HTTPException, status
from typing import Optional, Dict, Any


class AtlasBaseException(Exception):
    """Base para todas las excepciones de ATLAS."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "type": self.__class__.__name__,
                "message": self.message,
                "status_code": self.status_code,
                "detail": self.detail,
            }
        }


# ─────────────────────────────────────────────────────────────────────────────
# Excepciones del Dominio: Biometría
# ─────────────────────────────────────────────────────────────────────────────

class BiometricDataError(AtlasBaseException):
    """Error al obtener o procesar datos biométricos."""

    def __init__(self, message: str = "Error en datos biométricos", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class BiometricDataNotFoundError(AtlasBaseException):
    """No se encontraron datos biométricos para el usuario o fecha."""

    def __init__(self, message: str = "Datos biométricos no encontrados", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BiometricDataCorruptedError(AtlasBaseException):
    """Los datos biométricos están corruptos o incompletos."""

    def __init__(self, message: str = "Datos biométricos corruptos", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


# ─────────────────────────────────────────────────────────────────────────────
# Excepciones del Dominio: Calendario de Entrenamiento (Planner)
# ─────────────────────────────────────────────────────────────────────────────

class TrainingPlanError(AtlasBaseException):
    """Error general en la generación o gestión de planes de entrenamiento."""

    def __init__(self, message: str = "Error en plan de entrenamiento", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class PlanGenerationError(AtlasBaseException):
    """Error específico al generar un nuevo plan de entrenamiento."""

    def __init__(self, message: str = "Error generando plan de entrenamiento", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class SessionNotFoundError(AtlasBaseException):
    """No se encontró una sesión de entrenamiento específica."""

    def __init__(self, message: str = "Sesión no encontrada", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class PlanSessionNotFound(AtlasBaseException):
    """No se encontró una sesión planificada."""

    def __init__(self, message: str = "Sesión planificada no encontrada", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, detail=detail)


# ─────────────────────────────────────────────────────────────────────────────
# Excepciones del Dominio: Readiness (Preparación)
# ─────────────────────────────────────────────────────────────────────────────

class ReadinessCalculationError(AtlasBaseException):
    """Error al calcular el puntaje de preparación (readiness)."""

    def __init__(self, message: str = "Error calculando readiness", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class ReadinessDataInsufficientError(AtlasBaseException):
    """Datos insuficientes para calcular readiness."""

    def __init__(self, message: str = "Datos insuficientes para readiness", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


# ─────────────────────────────────────────────────────────────────────────────
# Excepciones del Dominio: Sincronización (Sync)
# ─────────────────────────────────────────────────────────────────────────────

class SyncServiceError(AtlasBaseException):
    """Error general en el servicio de sincronización."""

    def __init__(self, message: str = "Error en servicio de sincronización", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class GarminSyncError(SyncServiceError):
    """Error específico al sincronizar con Garmin."""

    def __init__(self, message: str = "Error sincronizando con Garmin", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


class GarminCredentialsError(SyncServiceError):
    """Error con las credenciales de Garmin."""

    def __init__(self, message: str = "Credenciales de Garmin inválidas", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class HevySyncError(SyncServiceError):
    """Error específico al sincronizar con Hevy."""

    def __init__(self, message: str = "Error sincronizando con Hevy", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


# ─────────────────────────────────────────────────────────────────────────────
# Excepciones del Dominio: Inteligencia Artificial
# ─────────────────────────────────────────────────────────────────────────────

class AIProviderError(AtlasBaseException):
    """Error al comunicarse con el proveedor de IA."""

    def __init__(self, message: str = "Error de proveedor de IA", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


class AIResponseError(AtlasBaseException):
    """Error en la respuesta de la IA (malformada o inesperada)."""

    def __init__(self, message: str = "Respuesta de IA inválida", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


class AIContextLengthError(AtlasBaseException):
    """El contexto es demasiado largo para la IA."""

    def __init__(self, message: str = "Contexto demasiado largo para IA", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=detail)


# ─────────────────────────────────────────────────────────────────────────────
# Excepciones del Dominio: Autenticación
# ─────────────────────────────────────────────────────────────────────────────

class AuthenticationError(AtlasBaseException):
    """Error de autenticación."""

    def __init__(self, message: str = "Error de autenticación", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class AuthorizationError(AtlasBaseException):
    """Error de autorización."""

    def __init__(self, message: str = "No autorizado", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN, detail=detail)


# ─────────────────────────────────────────────────────────────────────────────
# Excepciones del Dominio: Memoria (Memory)
# ─────────────────────────────────────────────────────────────────────────────

class MemoryServiceError(AtlasBaseException):
    """Error en el servicio de memoria/memorias del atleta."""

    def __init__(self, message: str = "Error en servicio de memoria", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class MemoryNotFoundError(AtlasBaseException):
    """No se encontró una memoria específica."""

    def __init__(self, message: str = "Memoria no encontrada", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, detail=detail)


# ─────────────────────────────────────────────────────────────────────────────
# Excepciones del Dominio: Perfil Deportivo del Atleta
# ─────────────────────────────────────────────────────────────────────────────

class AthleteProfileError(AtlasBaseException):
    """Error relacionado con el perfil deportivo del atleta."""

    def __init__(self, message: str = "Error en perfil de atleta", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class BaselineNotFoundError(AtlasBaseException):
    """No se encontró una línea base (baseline) para el atleta."""

    def __init__(self, message: str = "Baseline no encontrado", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, detail=detail)


# ─────────────────────────────────────────────────────────────────────────────
# Excepciones del Dominio: Notificaciones
# ─────────────────────────────────────────────────────────────────────────────

class NotificationServiceError(AtlasBaseException):
    """Error en el servicio de notificaciones."""

    def __init__(self, message: str = "Error en servicio de notificaciones", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


# ─────────────────────────────────────────────────────────────────────────────
# Utilitario: Decorador para manejo de excepciones en servicios
# ─────────────────────────────────────────────────────────────────────────────

import functools
import logging

logger = logging.getLogger("app.core.exceptions")


def handle_service_errors(func):
    """
    Decorator para funciones de servicio.
    Captura excepciones AtlasBaseException y las propaga.
    Captura excepciones generales y las envuelve en AtlasBaseException.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AtlasBaseException:
            raise  # Ya es del dominio, propagar sin tocar
        except Exception as e:
            logger.exception(f"Excepción no manejada en {func.__name__}: {e}")
            raise AtlasBaseException(
                message=f"Error interno en {func.__name__}: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"original_error": str(e)},
            )
    return wrapper
