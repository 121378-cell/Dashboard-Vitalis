import logging
import os
import requests
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger("app.core.health_check")

def check_all_services() -> Dict[str, Any]:
    """Check health of all required services and log their status."""
    results = {}
    
    logger.info("=" * 60)
    logger.info("ATLAS Health Check - Starting service verification...")
    logger.info("=" * 60)
    
    # 1. Check Groq API
    try:
        logger.info("Checking Groq API...")
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            },
            timeout=10
        )
        if response.status_code == 200:
            results["groq"] = {"status": "✅ OK", "response_time_ms": response.elapsed.total_seconds() * 1000}
        else:
            results["groq"] = {"status": f"❌ Failed ({response.status_code})", "error": response.text[:200]}
    except Exception as e:
        results["groq"] = {"status": "❌ Not available", "error": str(e)}
    
    logger.info(f"Groq API: {results['groq']['status']}")
    
    # 2. Check Garmin tokens
    try:
        logger.info("Checking Garmin tokens...")
        token_dir = ".garth"
        oauth1_exists = os.path.exists(os.path.join(token_dir, "oauth1_token.json"))
        oauth2_exists = os.path.exists(os.path.join(token_dir, "oauth2_token.json"))
        
        if oauth1_exists and oauth2_exists:
            results["garmin_tokens"] = {"status": "✅ OK", "token_dir": token_dir}
        else:
            missing = []
            if not oauth1_exists:
                missing.append("oauth1_token.json")
            if not oauth2_exists:
                missing.append("oauth2_token.json")
            results["garmin_tokens"] = {"status": "❌ Missing", "missing_files": missing}
    except Exception as e:
        results["garmin_tokens"] = {"status": "❌ Error", "error": str(e)}
    
    logger.info(f"Garmin Tokens: {results['garmin_tokens']['status']}")
    
    # 3. Check SQLite Database
    try:
        logger.info("Checking SQLite database...")
        import sqlite3
        db_path = "atlas_v2.db"
        
        if not os.path.exists(db_path):
            results["database"] = {"status": "❌ Not found", "path": db_path}
        else:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if tables exist
            required_tables = ["users", "tokens", "biometrics", "workouts", "training_sessions"]
            existing_tables = cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            existing_tables = [t[0] for t in existing_tables]
            
            missing_tables = [t for t in required_tables if t not in existing_tables]
            
            if missing_tables:
                results["database"] = {"status": "⚠️ Partial", "missing_tables": missing_tables}
            else:
                results["database"] = {"status": "✅ OK", "tables": len(existing_tables)}
            
            conn.close()
    except Exception as e:
        results["database"] = {"status": "❌ Error", "error": str(e)}
    
    logger.info(f"Database: {results['database']['status']}")
    
    # 4. Check Ollama
    try:
        logger.info("Checking Ollama...")
        response = requests.get(
            f"{settings.OLLAMA_BASE_URL}/api/tags",
            timeout=3
        )
        if response.status_code == 200:
            models = response.json().get("models", [])
            results["ollama"] = {"status": "✅ OK", "models_available": len(models)}
        else:
            results["ollama"] = {"status": f"❌ Not responding ({response.status_code})"}
    except Exception as e:
        results["ollama"] = {"status": "❌ Not running", "error": str(e)}
    
    logger.info(f"Ollama: {results['ollama']['status']}")
    
    # Summary
    logger.info("=" * 60)
    healthy = sum(1 for r in results.values() if "✅" in str(r.get("status", "")))
    total = len(results)
    logger.info(f"Health Check Complete: {healthy}/{total} services healthy")
    logger.info("=" * 60)
    
    return results
