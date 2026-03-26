#!/usr/bin/env python3
"""
Resumen completo de datos Garmin para contexto de IA - ATLAS AI
450 días de datos (1 Ene 2025 - 26 Mar 2026)
"""
import sys
import os
import json
import statistics
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.db.session import SessionLocal
from app.models.biometrics import Biometrics
from app.models.workout import Workout

db = SessionLocal()

print("=" * 80)
print("RESUMEN COMPLETO DE DATOS GARMIN - CONTEXTO PARA IA")
print("Período: 1 de Enero 2025 - 26 de Marzo 2026 (450 días)")
print("Usuario: Sergi Márquez Brugal (sergi.marquez.brugal@gmail.com)")
print("Dispositivo: Garmin Forerunner 245")
print("=" * 80)

# === BIOMETRICS ANALYSIS ===
print("\n" + "=" * 80)
print("📊 ANÁLISIS DE BIOMÉTRICOS (450 días)")
print("=" * 80)

biometrics = db.query(Biometrics).filter(Biometrics.user_id == "default_user").order_by(Biometrics.date).all()

heart_rates = []
stress_levels = []
sleep_hours = []
steps_daily = []
respiration_rates = []
spo2_values = []
dates_with_data = []

for b in biometrics:
    if b.data:
        try:
            data = json.loads(b.data)
            if data.get("heartRate") and data["heartRate"] > 0:
                heart_rates.append(data["heartRate"])
            if data.get("stress") and data["stress"] > 0:
                stress_levels.append(data["stress"])
            if data.get("sleep") and data["sleep"] > 0:
                sleep_hours.append(data["sleep"])
            if data.get("steps") and data["steps"] > 0:
                steps_daily.append(data["steps"])
            if data.get("respiration") and data["respiration"] > 0:
                respiration_rates.append(data["respiration"])
            if data.get("spo2") and data["spo2"] > 0:
                spo2_values.append(data["spo2"])
            dates_with_data.append(b.date)
        except:
            pass

print(f"\nTotal registros: {len(biometrics)}")
print(f"Días con datos completos: {len(set(dates_with_data))}")

# Heart Rate
if heart_rates:
    print(f"\n❤️  FRECUENCIA CARDIACA EN REPOSO:")
    print(f"  Promedio: {statistics.mean(heart_rates):.1f} bpm")
    print(f"  Mediana: {statistics.median(heart_rates):.1f} bpm")
    print(f"  Mínimo: {min(heart_rates)} bpm")
    print(f"  Máximo: {max(heart_rates)} bpm")
    print(f"  Desviación estándar: {statistics.stdev(heart_rates):.1f}")
    # Rango percentil 10-90
    sorted_hr = sorted(heart_rates)
    p10 = sorted_hr[int(len(sorted_hr) * 0.1)]
    p90 = sorted_hr[int(len(sorted_hr) * 0.9)]
    print(f"  Rango percentil 10-90: {p10} - {p90} bpm")

# Stress
if stress_levels:
    print(f"\n😰 NIVEL DE ESTRÉS:")
    print(f"  Promedio: {statistics.mean(stress_levels):.1f}")
    print(f"  Mediana: {statistics.median(stress_levels):.1f}")
    print(f"  Mínimo: {min(stress_levels)}")
    print(f"  Máximo: {max(stress_levels)}")
    low_stress = sum(1 for s in stress_levels if s < 25)
    high_stress = sum(1 for s in stress_levels if s > 50)
    print(f"  Días con estrés bajo (<25): {low_stress} ({low_stress/len(stress_levels)*100:.1f}%)")
    print(f"  Días con estrés alto (>50): {high_stress} ({high_stress/len(stress_levels)*100:.1f}%)")

# Sleep
if sleep_hours:
    print(f"\n😴 HORAS DE SUEÑO:")
    print(f"  Promedio: {statistics.mean(sleep_hours):.2f} horas")
    print(f"  Mediana: {statistics.median(sleep_hours):.2f} horas")
    print(f"  Mínimo: {min(sleep_hours):.2f} horas")
    print(f"  Máximo: {max(sleep_hours):.2f} horas")
    good_sleep = sum(1 for s in sleep_hours if s >= 7)
    poor_sleep = sum(1 for s in sleep_hours if s < 5)
    print(f"  Días con buen sueño (≥7h): {good_sleep} ({good_sleep/len(sleep_hours)*100:.1f}%)")
    print(f"  Días con sueño deficiente (<5h): {poor_sleep} ({poor_sleep/len(sleep_hours)*100:.1f}%)")

# Steps
if steps_daily:
    print(f"\n👟 PASOS DIARIOS:")
    print(f"  Promedio: {statistics.mean(steps_daily):.0f} pasos")
    print(f"  Mediana: {statistics.median(steps_daily):.0f} pasos")
    print(f"  Mínimo: {min(steps_daily):,} pasos")
    print(f"  Máximo: {max(steps_daily):,} pasos")
    active_days = sum(1 for s in steps_daily if s >= 10000)
    sedentary_days = sum(1 for s in steps_daily if s < 5000)
    print(f"  Días activos (≥10k): {active_days} ({active_days/len(steps_daily)*100:.1f}%)")
    print(f"  Días sedentarios (<5k): {sedentary_days} ({sedentary_days/len(steps_daily)*100:.1f}%)")
    total_steps = sum(steps_daily)
    print(f"  Total acumulado: {total_steps:,} pasos")

# Respiration
if respiration_rates:
    print(f"\n🫁 RESPIRACIÓN:")
    print(f"  Promedio: {statistics.mean(respiration_rates):.1f} rpm")
    print(f"  Mediana: {statistics.median(respiration_rates):.1f} rpm")
    print(f"  Rango: {min(respiration_rates)} - {max(respiration_rates)} rpm")

# SpO2
if spo2_values:
    print(f"\n🩸 SP02 (Saturación Oxígeno):")
    print(f"  Promedio: {statistics.mean(spo2_values):.1f}%")
    print(f"  Mediana: {statistics.median(spo2_values):.1f}%")
    print(f"  Mínimo: {min(spo2_values)}%")
    print(f"  Máximo: {max(spo2_values)}%")
    low_spo2 = sum(1 for s in spo2_values if s < 90)
    if low_spo2 > 0:
        print(f"  ⚠️  Lecturas bajas (<90%): {low_spo2}")

# === WORKOUTS ANALYSIS ===
print("\n" + "=" * 80)
print("🏃 ANÁLISIS DE ENTRENAMIENTOS (284 actividades)")
print("=" * 80)

workouts = db.query(Workout).filter(Workout.user_id == "default_user").order_by(Workout.date).all()

print(f"\nTotal actividades: {len(workouts)}")

# Group by source
sources = {}
for w in workouts:
    src = w.source or "unknown"
    sources[src] = sources.get(src, 0) + 1

print(f"\nPor fuente:")
for src, count in sources.items():
    print(f"  {src}: {count} actividades")

# Activity types analysis
activities_by_name = {}
for w in workouts:
    name = w.name or "Unknown"
    if "Fuerza" in name:
        cat = "Fuerza"
    elif "Correr" in name or "Running" in name:
        cat = "Running"
    elif "Caminar" in name or "Walk" in name:
        cat = "Caminata"
    elif "Hevy" in name:
        cat = "Hevy (Mock)"
    else:
        cat = name
    activities_by_name[cat] = activities_by_name.get(cat, 0) + 1

print(f"\nPor tipo de actividad:")
for activity, count in sorted(activities_by_name.items(), key=lambda x: -x[1]):
    print(f"  {activity}: {count}")

# Duration analysis
durations = [w.duration for w in workouts if w.duration and w.duration > 0]
if durations:
    print(f"\n⏱️  DURACIÓN DE ENTRENAMIENTOS:")
    print(f"  Promedio: {statistics.mean(durations)/60:.1f} minutos")
    print(f"  Mediana: {statistics.median(durations)/60:.1f} minutos")
    print(f"  Más corto: {min(durations)/60:.1f} minutos")
    print(f"  Más largo: {max(durations)/60:.1f} minutos")
    total_hours = sum(durations) / 3600
    print(f"  Total entrenado: {total_hours:.1f} horas")

# Calories analysis
calories_list = [w.calories for w in workouts if w.calories and w.calories > 0]
if calories_list:
    print(f"\n🔥 CALORÍAS QUEMADAS:")
    print(f"  Promedio por sesión: {statistics.mean(calories_list):.0f} cal")
    print(f"  Mediana: {statistics.median(calories_list):.0f} cal")
    print(f"  Máximo: {max(calories_list)} cal")
    total_calories = sum(calories_list)
    print(f"  Total acumulado: {total_calories:,} calorías")

# Monthly distribution
monthly_counts = {}
for w in workouts:
    if w.date:
        month_key = w.date.strftime("%Y-%m") if hasattr(w.date, 'strftime') else str(w.date)[:7]
        monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1

print(f"\n📅 DISTRIBUCIÓN MENSUAL:")
for month in sorted(monthly_counts.keys()):
    count = monthly_counts[month]
    bar = "█" * count
    print(f"  {month}: {count:3d} {bar}")

# === DERIVED INSIGHTS ===
print("\n" + "=" * 80)
print("💡 INSIGHTS DERIVADOS PARA LA IA")
print("=" * 80)

print("\n1. PATRÓN DE ENTRENAMIENTO:")
if "Fuerza" in activities_by_name:
    strength_count = activities_by_name["Fuerza"]
    print(f"   - Atleta enfocado en entrenamiento de fuerza ({strength_count} sesiones)")
    print(f"   - Frecuencia: ~{strength_count/14.5:.1f} sesiones/semana promedio")

if heart_rates and statistics.mean(heart_rates) < 50:
    print(f"   - FC en reposo muy baja ({statistics.mean(heart_rates):.0f} bpm) indica excelente condición cardiovascular")

if sleep_hours and statistics.mean(sleep_hours) < 6:
    print(f"   - ⚠️  Patrón de sueño insuficiente ({statistics.mean(sleep_hours):.1f}h promedio)")
    print(f"   - Recomendación: Priorizar recuperación y descanso")

print("\n2. INDICADORES DE RECUPERACIÓN:")
if stress_levels:
    avg_stress = statistics.mean(stress_levels)
    if avg_stress > 40:
        print(f"   - Nivel de estrés promedio elevado ({avg_stress:.0f}/100)")
        print(f"   - Sugerencia: Incorporar técnicas de recuperación activa")
    else:
        print(f"   - Nivel de estrés controlado ({avg_stress:.0f}/100)")

print("\n3. VOLUMEN DE ACTIVIDAD:")
if steps_daily:
    avg_steps = statistics.mean(steps_daily)
    if avg_steps > 15000:
        print(f"   - Volumen de actividad diaria muy alto ({avg_steps:,.0f} pasos)")
        print(f"   - Atleta muy activo, monitorear sobreentrenamiento")
    elif avg_steps > 10000:
        print(f"   - Actividad diaria saludable ({avg_steps:,.0f} pasos)")

print("\n4. CONSISTENCIA:")
if len(workouts) > 200:
    print(f"   - Alta consistencia: {len(workouts)} entrenamientos en 450 días")
    print(f"   - Ratio: {len(workouts)/450*100:.1f}% de días con actividad registrada")

# === CONTEXT FOR AI PROMPT ===
print("\n" + "=" * 80)
print("🤖 CONTEXTO PARA PROMPT DE IA (copiar y pegar)")
print("=" * 80)

context = f"""
CONTEXTO DEL ATLETA - SERGI MÁRQUEZ BRUGAL
==========================================
Período analizado: 450 días (1 Ene 2025 - 26 Mar 2026)
Dispositivo: Garmin Forerunner 245

PERFIL FISIOLÓGICO:
- FC reposo promedio: {statistics.mean(heart_rates):.0f} bpm (muy buena condición)
- Estrés promedio: {statistics.mean(stress_levels):.0f}/100
- Sueño promedio: {statistics.mean(sleep_hours):.1f}h ({'⚠️ insuficiente' if statistics.mean(sleep_hours) < 6 else 'adecuado'})
- Pasos diarios: {statistics.mean(steps_daily):,.0f}
- SpO2 promedio: {statistics.mean(spo2_values):.0f}%

HISTORIAL DE ENTRENAMIENTO:
- Total sesiones: {len(workouts)}
- Fuerza: {activities_by_name.get('Fuerza', 0)} sesiones
- Tiempo total: {sum(durations)/3600:.1f} horas
- Calorías totales: {sum(calories_list):,} cal
- Consistencia: {len(workouts)/450*100:.1f}% días activos

RECOMENDACIONES BASE:
- Priorizar aumentar sueño a 7-8h (actual {statistics.mean(sleep_hours):.1f}h)
- Mantener volumen de fuerza, monitorizar estrés
- FC reposo excelente, indicador de buena forma cardiovascular
"""

print(context)

db.close()
print("\n" + "=" * 80)
print("✅ RESUMEN COMPLETADO - Datos listos para contexto de IA")
print("=" * 80)
