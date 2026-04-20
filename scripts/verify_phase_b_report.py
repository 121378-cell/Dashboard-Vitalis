#!/usr/bin/env python3
"""Verifica requisitos del informe 'Proyecto Vitalis — Fase B (ATLAS Proactivo)'."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def check(name: str, ok: bool, detail: str) -> tuple[bool, str]:
    status = "✅" if ok else "❌"
    return ok, f"{status} {name}: {detail}"


def main() -> int:
    results: list[tuple[bool, str]] = []

    app_text = read_text("src/App.tsx")
    context_text = read_text("backend/app/services/context_service.py")
    ai_endpoint_text = read_text("backend/app/api/api_v1/endpoints/ai.py")
    ws_hook_text = read_text("src/hooks/useReadinessWebSocket.ts")
    config_text = read_text("backend/app/core/config.py")
    biometrics_model = read_text("backend/app/models/biometrics.py")
    package_json = read_text("package.json")
    strava_text = read_text("backend/app/api/api_v1/endpoints/strava.py")

    results.append(
        check(
            "Identidad real Sergi",
            all(token in app_text for token in ["Sergi", "47-48", "Banca 50kg", "Prensa 100kg"]),
            "Perfil y hitos presentes en prompt/contexto del frontend.",
        )
    )
    results.append(
        check(
            "Briefing matutino proactivo",
            "daily-briefing" in app_text and "@router.get(\"/daily-briefing\")" in ai_endpoint_text,
            "Frontend invoca briefing y backend expone endpoint dedicado.",
        )
    )
    results.append(
        check(
            "Protocolo de adaptabilidad",
            "readiness" in app_text and "HRV" in app_text,
            "Prompt y métricas incluyen readiness + HRV.",
        )
    )
    results.append(
        check(
            "Puerto unificado 8005",
            "localhost:8005" in ws_hook_text and "8005" in config_text,
            "Defaults de WebSocket y callback Strava en 8005.",
        )
    )
    results.append(
        check(
            "Esquema biometrics actualizado",
            all(col in biometrics_model for col in ["recovery_time", "training_status", "hrv_status"]),
            "Campos críticos de recuperación/estado presentes en modelo SQLAlchemy.",
        )
    )
    results.append(
        check(
            "Cerebro dual Groq/Gemini",
            all(key in config_text for key in ["GROQ_API_KEY", "GEMINI_API_KEY"]),
            "Config incluye ambas claves de proveedor IA.",
        )
    )
    results.append(
        check(
            "Limpieza etiqueta 'Atleta ATLAS'",
            "Atleta ATLAS" not in strava_text,
            "No quedan placeholders genéricos en endpoint Strava.",
        )
    )
    results.append(
        check(
            "Metodología McGill/Stoppani/Bompa",
            all(name in context_text for name in ["McGill", "Stoppani", "Bompa"]),
            "Contexto del coach contiene marco metodológico completo.",
        )
    )

    # Hevy exercises count
    csv_path = ROOT / "knowledge_base" / "HEVY APP exercises.csv"
    with csv_path.open(newline="", encoding="utf-8") as f:
        count = sum(1 for _ in csv.DictReader(f))
    results.append(
        check(
            "Biblia Hevy (434 ejercicios)",
            count >= 434,
            f"Encontrados {count} ejercicios en CSV.",
        )
    )

    pdf_count = len(list((ROOT / "knowledge_base" / "raw_pdfs").glob("*.pdf")))
    results.append(
        check(
            "Biblioteca académica (27 PDFs)",
            pdf_count >= 27,
            f"Detectados {pdf_count} PDFs en knowledge_base/raw_pdfs.",
        )
    )

    results.append(
        check(
            "Nota técnica de sincronización móvil",
            "npm run build" in package_json and "npx cap sync" in package_json,
            "Scripts build/sync definidos en package.json.",
        )
    )

    print("\n=== Verificación Informe Fase B ===")
    for _, line in results:
        print(line)

    failed = sum(1 for ok, _ in results if not ok)
    print(f"\nResumen: {len(results) - failed}/{len(results)} requisitos verificados.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
