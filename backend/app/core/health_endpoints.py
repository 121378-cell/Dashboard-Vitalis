"""
ATLAS Health Endpoints
=======================
Endpoints de salud para Fly.io, Kubernetes y monitoreo.
 Diseñados para diferentes niveles de profundidad:
- /health        : Básico (para Fly.io native checks)
- /health/ready  : Readiness probes (verifica dependencias)
- /health/deep   : Deep health (verifica conectividad real)
"""

import logging
import os
import time
from typing import Dict, Any

logger = logging.getLogger("app.core.health_endpoints")

_start_time = time.time()


def _get_uptime() -> int:
    return int(time.time() - _start_time)


def basic_health() -> Dict[str, Any]:
    """
    Health check básico — solo DB connectivity.
    Usado por Fly.io para determinar si la VM está viva.
    Muy rápido, sin side-effects.
    """
    db_status = "error"
    try:
        from app.db.session import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_status = "ok"
    except Exception as e:
        logger.error(f"basic_health DB error: {e}")

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "uptime_seconds": _get_uptime(),
    }


def ready_health() -> Dict[str, Any]:
    """
    Readiness probe — verifica todas las dependencias críticas.
    Usado por Kubernetes/Fly.io para decidir si rotear tráfico.
    Incluye DB + config de AI + credenciales Garmin.
    """
    checks = {}
    overall_status = "ok"

    from app.db.session import SessionLocal
    from sqlalchemy import text

    db_ok = False
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.error(f"ready_health DB error: {e}")
    checks["database"] = "ok" if db_ok else "error"
    if not db_ok:
        overall_status = "degraded"

    from app.core.config import settings
    ai_ok = bool(settings.GROQ_API_KEY or settings.GEMINI_API_KEY)
    checks["ai_configured"] = "ok" if ai_ok else "not_configured"
    if not ai_ok:
        overall_status = "degraded"

    try:
        from app.db.session import SessionLocal
        from app.models.token import Token
        with SessionLocal() as db:
            token = db.query(Token).filter(Token.user_id == "default_user").first()
            has_garmin = bool(token and (token.garmin_email or token.garmin_password))
        checks["garmin_credentials"] = "ok" if has_garmin else "missing"
        if not has_garmin:
            overall_status = "degraded"
    except Exception as e:
        logger.warning(f"ready_health Garmin check error: {e}")
        checks["garmin_credentials"] = "unknown"

    return {
        "status": overall_status,
        "checks": checks,
        "uptime_seconds": _get_uptime(),
    }


def deep_health() -> Dict[str, Any]:
    """
    Deep health check — verifica conectividad real con servicios externos.
    Solo lo llama el operador/admin, no Fly.io ni K8s.
    Mide latencia real a AI providers.
    """
    from app.core.config import settings
    checks = {}
    overall_status = "ok"

    from app.db.session import SessionLocal
    from sqlalchemy import text
    db_ok = False
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.error(f"deep_health DB error: {e}")
    checks["database"] = "ok" if db_ok else "error"
    if not db_ok:
        overall_status = "degraded"

    if settings.GROQ_API_KEY:
        try:
            import requests
            import time as t
            start = t.time()
            resp = requests.head(
                "https://api.groq.com",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                timeout=5,
            )
            latency_ms = int((t.time() - start) * 1000)
            checks["groq_api"] = f"ok ({resp.status_code}) - {latency_ms}ms"
        except Exception as e:
            checks["groq_api"] = f"error: {str(e)[:50]}"
            overall_status = "degraded"
    elif settings.GEMINI_API_KEY:
        try:
            import requests
            import time as t
            start = t.time()
            resp = requests.head(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.GEMINI_API_KEY}",
                timeout=5,
            )
            latency_ms = int((t.time() - start) * 1000)
            checks["gemini_api"] = f"ok ({resp.status_code}) - {latency_ms}ms"
        except Exception as e:
            checks["gemini_api"] = f"error: {str(e)[:50]}"
            overall_status = "degraded"
    else:
        checks["ai_provider"] = "not_configured"

    try:
        from app.db.session import SessionLocal
        from app.models.token import Token
        with SessionLocal() as db:
            token = db.query(Token).filter(Token.user_id == "default_user").first()
            has_garmin = bool(token and (token.garmin_email or token.garmin_password))
        checks["garmin_credentials"] = "ok" if has_garmin else "missing"
        if not has_garmin:
            overall_status = "degraded"
    except Exception as e:
        logger.warning(f"deep_health Garmin check error: {e}")
        checks["garmin_credentials"] = "unknown"

    return {
        "status": overall_status,
        "checks": checks,
        "uptime_seconds": _get_uptime(),
    }