"""
Dashboard-Vitalis - Garmin Client Manager v2.0
==============================================

Sistema resiliente de gestión de sesiones Garmin con:
- Persistencia de sesiones en base de datos
- Rate limiting protection con cooldown
- Validación de sesiones antes de login
- Logging profesional
- Anti-spam protection

Autor: Dashboard-Vitalis Team
Versión: 2.0.0
"""

import os
import json
import garth
from garminconnect import Garmin
from typing import Any, Optional, Tuple, Union
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
import logging
import time

from app.utils.garmin_exceptions import GarminRateLimitError, GarminSessionError, GarminAuthError

logger = logging.getLogger("app.utils.garmin")

# Constantes de configuración
MIN_LOGIN_INTERVAL_SECONDS = 60  # Mínimo 60 segundos entre intentos de login
DEFAULT_COOLDOWN_MINUTES = 15    # Cooldown por defecto tras 429
MAX_LOGIN_ATTEMPTS = 3           # Máximo intentos antes de cooldown forzoso


def safe_get(data: Any, *keys: str, default: Any = None) -> Any:
    """Safely navigate nested dictionaries or lists."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        elif isinstance(data, list) and isinstance(key, int):
            try:
                data = data[key]
            except IndexError:
                return default
        else:
            return default
    return data if data is not None else default


def _read_session_json(token_dir: str) -> str:
    """Lee los tokens OAuth del directorio y los devuelve como string JSON."""
    session_dict = {}
    for filename in ["oauth1_token.json", "oauth2_token.json"]:
        filepath = os.path.join(token_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    session_dict[filename] = json.load(f)
            except Exception as e:
                logger.warning(f"[GARMIN] Error leyendo {filename}: {e}")
    
    result = json.dumps(session_dict) if session_dict else ""
    if result:
        logger.debug(f"[GARMIN] Session JSON read successfully ({len(result)} chars)")
    return result


def _check_cooldown(db: Session, user_id: str) -> Optional[datetime]:
    """Verifica si hay un cooldown activo para el usuario."""
    from app.models.token import Token
    
    creds = db.query(Token).filter(Token.user_id == user_id).first()
    if not creds:
        return None
    
    if creds.garmin_rate_limited_until:
        now = datetime.utcnow()
        if now < creds.garmin_rate_limited_until:
            logger.warning(f"[GARMIN] Cooldown activo hasta {creds.garmin_rate_limited_until}")
            return creds.garmin_rate_limited_until
        else:
            # Cooldown expirado, limpiar
            creds.garmin_rate_limited_until = None
            db.commit()
            logger.info("[GARMIN] Cooldown expirado, limpiando estado")
    
    return None


def _set_cooldown(db: Session, user_id: str, minutes: int = DEFAULT_COOLDOWN_MINUTES):
    """Establece un cooldown tras recibir error 429."""
    from app.models.token import Token
    
    creds = db.query(Token).filter(Token.user_id == user_id).first()
    if creds:
        creds.garmin_rate_limited_until = datetime.utcnow() + timedelta(minutes=minutes)
        creds.login_attempts_count = 0  # Resetear contador
        db.commit()
        logger.error(f"[GARMIN] 🔒 RATE LIMITED - Cooldown iniciado por {minutes} minutos")


def _check_anti_spam(db: Session, user_id: str) -> bool:
    """Verifica protección anti-spam (mínimo 60 segundos entre intentos)."""
    from app.models.token import Token
    
    creds = db.query(Token).filter(Token.user_id == user_id).first()
    if not creds or not creds.last_login_attempt:
        return True
    
    elapsed = (datetime.utcnow() - creds.last_login_attempt).total_seconds()
    if elapsed < MIN_LOGIN_INTERVAL_SECONDS:
        wait = MIN_LOGIN_INTERVAL_SECONDS - elapsed
        logger.warning(f"[GARMIN] Anti-spam: esperar {wait:.0f}s antes de reintentar")
        return False
    
    return True


def _update_login_attempt(db: Session, user_id: str, increment: bool = True):
    """Actualiza el registro de intento de login."""
    from app.models.token import Token
    
    creds = db.query(Token).filter(Token.user_id == user_id).first()
    if creds:
        creds.last_login_attempt = datetime.utcnow()
        if increment:
            creds.login_attempts_count = (creds.login_attempts_count or 0) + 1
        db.commit()


def _validate_session(client: Garmin) -> bool:
    """Valida que una sesión de Garmin esté activa haciendo una petición de prueba."""
    try:
        # Intentar obtener resumen del día actual como prueba
        today = date.today().strftime("%Y-%m-%d")
        client.get_user_summary(today)
        logger.debug("[GARMIN] Session validation passed")
        return True
    except Exception as e:
        logger.warning(f"[GARMIN] Session validation failed: {e}")
        return False


def get_garmin_client(
    email: str,
    password: str,
    token_dir: str = None,
    session_data: str = None,
    user_id: str = None,
    db: Session = None
) -> Tuple[Optional[Garmin], Union[bool, str]]:
    """
    Obtiene un cliente de Garmin con gestión completa de sesiones y rate limiting.
    
    FLUJO:
    1. Verificar cooldown activo
    2. Intentar reutilizar sesión existente
    3. Validar sesión con petición de prueba
    4. Si falla: verificar anti-spam y hacer login
    5. Si 429: establecer cooldown
    
    Args:
        email: Email de Garmin Connect
        password: Password de Garmin Connect
        token_dir: Directorio de tokens (auto-generado si es None)
        session_data: String JSON con tokens de sesión previa
        user_id: ID de usuario para directorio único
        db: Sesión de base de datos para persistencia
        
    Returns:
        Tuple (cliente, session_data):
        - cliente: Instancia Garmin o None si falló
        - session_data: String JSON con tokens a persistir, o False si no hay cambios
        
    Raises:
        GarminRateLimitError: Si hay cooldown activo o se recibe 429
    """
    if not email or not password:
        logger.error("[GARMIN] Email o password no proporcionados")
        return None, False
    
    # Generar directorio único por usuario
    if token_dir is None:
        if user_id:
            token_dir = f".garth_{user_id}"
        else:
            token_dir = ".garth"
    
    logger.info(f"[GARMIN] Iniciando conexión para usuario: {user_id or 'unknown'}")
    
    # PASO 1: Verificar cooldown activo
    if db and user_id:
        cooldown_until = _check_cooldown(db, user_id)
        if cooldown_until:
            raise GarminRateLimitError(
                f"Rate limited hasta {cooldown_until.isoformat()}",
                retry_after=cooldown_until
            )
    
    # Crear directorio si no existe
    if not os.path.exists(token_dir):
        os.makedirs(token_dir, exist_ok=True)
    
    # PASO 2: Restaurar sesión desde DB si existe
    if session_data:
        try:
            tokens = json.loads(session_data)
            for filename, content in tokens.items():
                filepath = os.path.join(token_dir, filename)
                with open(filepath, "w") as f:
                    json.dump(content, f)
            logger.info("[GARMIN] Sesión restaurada desde base de datos")
        except Exception as e:
            logger.warning(f"[GARMIN] No se pudo restaurar sesión desde DB: {e}")
    
    # PASO 3: Intentar resume de sesión existente
    oauth1_path = os.path.join(token_dir, "oauth1_token.json")
    oauth2_path = os.path.join(token_dir, "oauth2_token.json")
    tokens_exist = os.path.exists(oauth1_path) and os.path.exists(oauth2_path)
    
    if tokens_exist:
        try:
            logger.info("[GARMIN] Intentando resume de sesión...")
            garth.resume(token_dir)
            client = Garmin(email=email, password=password)
            client.garth = garth.client
            
            # Validar sesión con petición real
            if _validate_session(client):
                session_json = _read_session_json(token_dir)
                logger.info("[GARMIN] Sesión reutilizada exitosamente (sin login)")
                
                # Resetear contadores de login al tener éxito
                if db and user_id:
                    _update_login_attempt(db, user_id, increment=False)
                
                return client, session_json
            else:
                logger.warning("[GARMIN] Sesión existente inválida, requiere login")
                client = None
                
        except Exception as e:
            logger.warning(f"[GARMIN] Resume falló: {e}")
            client = None
    else:
        logger.info("[GARMIN] No hay tokens existentes, se requiere login")
        client = None
    
    # PASO 4: Login fresco (solo si no hay sesión válida)
    if client is None:
        # Verificar anti-spam
        if db and user_id:
            if not _check_anti_spam(db, user_id):
                logger.error("[GARMIN] Bloqueado por protección anti-spam")
                return None, False
            _update_login_attempt(db, user_id)
        
        # Verificar límite de intentos
        if db and user_id:
            from app.models.token import Token
            creds = db.query(Token).filter(Token.user_id == user_id).first()
            if creds and creds.login_attempts_count >= MAX_LOGIN_ATTEMPTS:
                logger.error(f"[GARMIN] Máximo de intentos ({MAX_LOGIN_ATTEMPTS}) alcanzado")
                _set_cooldown(db, user_id, minutes=30)
                raise GarminRateLimitError(
                    "Máximo de intentos de login alcanzado",
                    retry_after=datetime.utcnow() + timedelta(minutes=30)
                )
        
        try:
            logger.info("[GARMIN] Iniciando login fresco...")
            client = Garmin(email=email, password=password)
            client.login()
            garth.save(token_dir)
            
            session_json = _read_session_json(token_dir)
            logger.info("[GARMIN] Login exitoso, sesión guardada")
            
            # Resetear contador de intentos
            if db and user_id:
                from app.models.token import Token
                creds = db.query(Token).filter(Token.user_id == user_id).first()
                if creds:
                    creds.login_attempts_count = 0
                    db.commit()
            
            return client, session_json
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"[GARMIN] Login failed: {error_str}")
            
            # Detectar 429 y establecer cooldown
            if "429" in error_str or "Too Many Requests" in error_str:
                if db and user_id:
                    _set_cooldown(db, user_id)
                raise GarminRateLimitError(
                    "Garmin rate limit detectado (429)",
                    retry_after=datetime.utcnow() + timedelta(minutes=DEFAULT_COOLDOWN_MINUTES)
                )
            
            raise GarminAuthError(f"Autenticación fallida: {error_str}")
    
    return None, False
