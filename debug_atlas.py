from app.core.config import settings
from app.services.ai_service import AIService
import os

def debug_ai():
    print("--- DIAGNOSTICO DE ATLAS ---")
    print(f"Cargando llaves desde .env...")
    print(f"GROQ_KEY detectada: {'SI' if settings.GROQ_API_KEY else 'NO'}")
    print(f"GEMINI_KEY detectada: {'SI' if settings.GEMINI_API_KEY else 'NO'}")
    
    if not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY:
        print("ERROR: El servidor no está leyendo el archivo .env.")
        return

    print("\nIntentando generar un briefing de prueba (esto puede tardar 10s)...")
    service = AIService()
    try:
        res = service.generate_response("Hola ATLAS, genera un briefing de prueba corto.", "Eres ATLAS.")
        print("\n--- RESPUESTA DE LA IA ---")
        print(res)
        print("\nDIAGNOSTICO EXITOSO: El cerebro de ATLAS funciona.")
    except Exception as e:
        print(f"\nDIAGNOSTICO FALLIDO: Error al conectar con la IA: {e}")

if __name__ == "__main__":
    debug_ai()
