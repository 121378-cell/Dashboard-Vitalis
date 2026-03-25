# 🛡️ Vitalis AI Coach - Plan de Implementación (Fase B+)

Este plan detalla la evolución del Dashboard Vitalis integrando las capacidades avanzadas de análisis de datos y contexto de IA extraídas del ecosistema **AI_Fitness**.

---

## 📊 Estado Actual del Sistema
- **Conectividad:** Credenciales reales configuradas (`.env`).
- **Sincronización:** Lógica robusta implementada (HRV, VO2 Max, Zonas FC).
- **Limitación actual:** Bloqueo temporal Garmin (Error 429) por falta de persistencia de tokens.

---

## 🚀 Sprint 1: Infraestructura de Datos Proactiva (Core)
*Objetivo: Estabilizar la conexión y enriquecer la base de datos para análisis profundo.*

- [x] **1.1 Refactorización de Persistencia (Garth + DB)**
  - Guardar el estado completo de la sesión de `garth` en la columna `garmin_session`.
  - Implementar lógica de "Resume" prioritaria para evitar logins innecesarios y saltar el Error 429.
- [x] **1.2 Ampliación del Modelo de Datos**
  - Añadir campos de `recovery_time`, `training_status` y `hrv_status` en la tabla `biometrics`.
  - Asegurar que el `SyncService` pueble estos campos desde la API de Garmin.
- [x] **1.3 Implementación de Línea Base (Baseline)**
  - Crear lógica para calcular la media móvil de 7 días para HRV y RHR (Frecuencia Cardíaca en Reposo).

---

## 🧠 Sprint 2: El "Motor de Contexto Vitalis" (Lógica AI)
*Objetivo: Traducir datos fríos en insights narrativos para que la IA actúe como un coach real.*

- [x] **2.1 Servicio de Traducción de Métricas (`context_service.py`)**
  - Desarrollar el motor que convierte JSON de Garmin en lenguaje natural para Gemini.
- [x] **2.2 Algoritmo de Carga Aguda vs Crónica (ACWR)**
  - Calcular el ratio de carga de entrenamiento para predecir riesgos de lesión.
- [x] **2.3 Integración de "Daily Briefing"**
  - Inyectar el resumen de recuperación y carga en el prompt del Chat de IA automáticamente.

---

## 🎨 Sprint 3: UI de Insights Avanzados (Frontend)
*Objetivo: Visualización clara de la preparación y el rendimiento del atleta.*

- [x] **3.1 Widgets de Tendencia (Dashboard)**
  - Mostrar indicadores visuales (flechas/colores) comparando el día actual con la media semanal.
- [x] **3.2 Dial de Readiness (Preparación)**
  - Implementar un indicador visual de "Puntuación de Preparación" basado en HRV, Sueño y Carga.
- [ ] **3.3 Visualizador de Zonas de FC**
  - Añadir gráficos de distribución de intensidad (Z1-Z5) en el detalle de los entrenamientos.

---

## ✅ Tareas Completadas
- [x] Análisis profundo de arquitectura AI_Fitness.
- [x] Mejora de `SyncService` con fallbacks de métricas (HRV, VO2 Max, Respiration).
- [x] Corrección de esquema de DB (`tokens`, `biometrics`).
- [x] Verificación de credenciales reales en entorno local.
