import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface Exercise {
  name: string;
  sets: number;
  reps: string;
  weight_kg: number;
  rest_seconds: number;
  muscle_group: string;
  notes: string;
}

interface RunningDetails {
  type: string;
  distance_km: number;
  target_pace_min_km: string;
  heart_rate_zone: string;
  structure: string;
}

interface MobilityDetails {
  focus: string;
  techniques: string[];
  key_exercises: string[];
}

interface Session {
  id?: number;
  date: string;
  day_of_week: string;
  session_type: 'strength' | 'running' | 'trail_running' | 'mobility' | 'hiit' | 'rest' | 'active_recovery';
  title: string;
  description: string;
  duration_minutes?: number;
  intensity?: 'low' | 'medium' | 'high';
  exercises?: Exercise[];
  running_details?: RunningDetails;
  mobility_details?: MobilityDetails;
  completed?: boolean;
  garmin_activity_id?: string;
  user_notes?: string;
  modified_by_user?: boolean;
  adaptation_reason?: string;
}

interface WeeklyPlan {
  plan_id: number;
  week_start: string;
  week_end: string;
  goal: string;
  status: string;
  created_at: string;
  ai_reasoning: string;
  progress: {
    completed: number;
    total: number;
    percentage: number;
  };
  plan: {
    weekly_goal: string;
    reasoning: string;
    total_planned_minutes: number;
    sessions: Session[];
    weekly_notes: string;
    nutrition_focus: string;
    sleep_reminder: string;
  };
}

const WeeklyPlanBoard: React.FC = () => {
  const [plan, setPlan] = useState<WeeklyPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [goal, setGoal] = useState('');
  const [generating, setGenerating] = useState(false);
  const [expandedSession, setExpandedSession] = useState<string | null>(null);
  const [editingSession, setEditingSession] = useState<{ id: number; field: string; value: any } | null>(null);

  useEffect(() => {
    fetchCurrentPlan();
  }, []);

  const fetchCurrentPlan = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/plans/current');
      const data = await response.json();

      if (data.has_plan) {
        setPlan(data.data);
        setShowOnboarding(false);
      } else {
        setShowOnboarding(true);
      }
    } catch (err) {
      setError('Error cargando el plan');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const generatePlan = async () => {
    if (!goal.trim()) {
      setError('Por favor ingresa un objetivo para la semana');
      return;
    }

    try {
      setGenerating(true);
      setError(null);

      const response = await fetch('/api/v1/plans/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal }),
      });

      const data = await response.json();

      if (response.ok) {
        setPlan(data.data);
        setShowOnboarding(false);
      } else {
        setError(data.detail || 'Error generando el plan');
      }
    } catch (err) {
      setError('Error generando el plan');
      console.error(err);
    } finally {
      setGenerating(false);
    }
  };

  const updateSession = async (sessionId: number, updates: any) => {
    try {
      const response = await fetch(`/api/v1/plans/sessions/${sessionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });

      if (response.ok) {
        // Refresh plan
        fetchCurrentPlan();
      } else {
        setError('Error actualizando la sesión');
      }
    } catch (err) {
      setError('Error actualizando la sesión');
      console.error(err);
    }
  };

  const toggleComplete = async (sessionId: number, currentCompleted: boolean) => {
    await updateSession(sessionId, { completed: !currentCompleted });
  };

  const detectCompletedSessions = async () => {
    try {
      const response = await fetch('/api/v1/plans/detect-completed', {
        method: 'POST',
      });

      if (response.ok) {
        const data = await response.json();
        alert(`${data.data.detected_count} sesiones detectadas como completadas`);
        fetchCurrentPlan();
      }
    } catch (err) {
      setError('Error detectando sesiones completadas');
      console.error(err);
    }
  };

  const getSessionIcon = (type: string) => {
    const icons: Record<string, string> = {
      strength: '💪',
      running: '🏃',
      trail_running: '🏔️',
      mobility: '🧘',
      hiit: '⚡',
      rest: '😴',
      active_recovery: '🔄',
    };
    return icons[type] || '📋';
  };

  const getIntensityColor = (intensity?: string) => {
    const colors: Record<string, string> = {
      low: 'bg-blue-100 text-blue-800',
      medium: 'bg-yellow-100 text-yellow-800',
      high: 'bg-red-100 text-red-800',
    };
    return colors[intensity || 'medium'] || colors.medium;
  };

  const getHeartRateZoneColor = (zone?: string) => {
    const colors: Record<string, string> = {
      Z1: 'bg-blue-500',
      Z2: 'bg-green-500',
      Z3: 'bg-yellow-500',
      Z4: 'bg-orange-500',
      Z5: 'bg-red-500',
    };
    return colors[zone || 'Z2'] || colors.Z2;
  };

  const isToday = (dateStr: string) => {
    const today = new Date().toISOString().split('T')[0];
    return dateStr === today;
  };

  const SessionCard: React.FC<{ session: Session }> = ({ session }) => {
    const isExpanded = expandedSession === session.date;
    const isSessionToday = isToday(session.date);

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`bg-white rounded-lg shadow-sm border-2 transition-all ${
          session.completed
            ? 'border-green-500 bg-green-50'
            : isSessionToday
            ? 'border-blue-500'
            : 'border-gray-200'
        }`}
      >
        <div className="p-4">
          <div className="flex items-start justify-between mb-2">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-2xl">{getSessionIcon(session.session_type)}</span>
                <h3 className="font-semibold text-gray-900">{session.title}</h3>
                {isSessionToday && (
                  <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                    HOY
                  </span>
                )}
                {session.adaptation_reason && (
                  <span className="px-2 py-0.5 text-xs font-medium bg-orange-100 text-orange-800 rounded-full" title={session.adaptation_reason}>
                    Adaptado
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-600 line-clamp-2">{session.description}</p>
            </div>
            <button
              onClick={() => toggleComplete(session.id!, session.completed || false)}
              className={`p-2 rounded-full transition-colors ${
                session.completed
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {session.completed ? '✓' : '○'}
            </button>
          </div>

          <div className="flex items-center gap-2 text-sm text-gray-500 mb-3">
            {session.duration_minutes && (
              <span>⏱️ {session.duration_minutes} min</span>
            )}
            {session.intensity && (
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getIntensityColor(session.intensity)}`}>
                {session.intensity}
              </span>
            )}
            {session.running_details?.heart_rate_zone && (
              <span className={`w-3 h-3 rounded-full ${getHeartRateZoneColor(session.running_details.heart_rate_zone)}`} title={`Zona ${session.running_details.heart_rate_zone}`} />
            )}
          </div>

          <button
            onClick={() => setExpandedSession(isExpanded ? null : session.date)}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            {isExpanded ? 'Ocultar detalles' : 'Ver detalles'}
          </button>

          <AnimatePresence>
            {isExpanded && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-4 pt-4 border-t border-gray-200"
              >
                {session.session_type === 'strength' && session.exercises && (
                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-900">Ejercicios</h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left py-2">Ejercicio</th>
                            <th className="text-center py-2">Series</th>
                            <th className="text-center py-2">Reps</th>
                            <th className="text-center py-2">Peso (kg)</th>
                            <th className="text-center py-2">Descanso</th>
                          </tr>
                        </thead>
                        <tbody>
                          {session.exercises.map((exercise, idx) => (
                            <tr key={idx} className="border-b">
                              <td className="py-2">{exercise.name}</td>
                              <td className="text-center py-2">{exercise.sets}</td>
                              <td className="text-center py-2">{exercise.reps}</td>
                              <td className="text-center py-2">{exercise.weight_kg || '-'}</td>
                              <td className="text-center py-2">{exercise.rest_seconds}s</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {session.running_details && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-gray-900">Detalles de Running</h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-gray-500">Tipo:</span>
                        <span className="ml-1 font-medium">{session.running_details.type}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Distancia:</span>
                        <span className="ml-1 font-medium">{session.running_details.distance_km} km</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Ritmo objetivo:</span>
                        <span className="ml-1 font-medium">{session.running_details.target_pace_min_km} min/km</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Zona HR:</span>
                        <span className={`ml-1 px-2 py-0.5 rounded-full text-xs font-medium ${getHeartRateZoneColor(session.running_details.heart_rate_zone)}`}>
                          {session.running_details.heart_rate_zone}
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 mt-2">{session.running_details.structure}</p>
                  </div>
                )}

                {session.mobility_details && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-gray-900">Detalles de Movilidad</h4>
                    <div className="text-sm">
                      <div>
                        <span className="text-gray-500">Enfoque:</span>
                        <span className="ml-1 font-medium">{session.mobility_details.focus}</span>
                      </div>
                      <div className="mt-2">
                        <span className="text-gray-500">Técnicas:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {session.mobility_details.techniques.map((tech, idx) => (
                            <span key={idx} className="px-2 py-0.5 bg-gray-100 rounded-full text-xs">
                              {tech}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="mt-2">
                        <span className="text-gray-500">Ejercicios clave:</span>
                        <ul className="list-disc list-inside mt-1">
                          {session.mobility_details.key_exercises.map((ex, idx) => (
                            <li key={idx}>{ex}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}

                {session.user_notes && (
                  <div className="mt-3 p-3 bg-yellow-50 rounded-lg">
                    <p className="text-sm text-gray-700">
                      <span className="font-medium">Notas:</span> {session.user_notes}
                    </p>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (showOnboarding) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            🎯 Genera tu Plan Semanal con IA
          </h2>
          <p className="text-gray-600 mb-6">
            ATLAS analizará tu perfil atlético, historial de entrenamiento y datos biométricos
            para crear un plan personalizado para esta semana.
          </p>

          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              ¿Cuál es tu objetivo para esta semana?
            </label>
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="Ej: Mejorar fuerza en piernas, preparar carrera de 10km, recuperar después de semana intensa..."
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={4}
            />
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}

          <button
            onClick={generatePlan}
            disabled={generating}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {generating ? (
              <span className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                Generando plan...
              </span>
            ) : (
              'Generar Plan con IA'
            )}
          </button>

          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-800">
              💡 <strong>Tip:</strong> El plan se basará en tu perfil atlético actual, incluyendo
              tu nivel de fitness, patrones de sueño, capacidad de recuperación y riesgo de
              sobreentrenamiento.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No hay plan disponible</p>
      </div>
    );
  }

  const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
  const weekDates = Array.from({ length: 7 }, (_, i) => {
    const date = new Date(plan.week_start);
    date.setDate(date.getDate() + i);
    return date.toISOString().split('T')[0];
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">{plan.plan.weekly_goal}</h2>
            <p className="text-gray-600 mt-1">{plan.plan.reasoning}</p>
          </div>
          <button
            onClick={detectCompletedSessions}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            Detectar Completadas
          </button>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">
                Progreso: {plan.progress.completed}/{plan.progress.total} sesiones
              </span>
              <span className="text-sm font-medium text-gray-700">
                {plan.progress.percentage.toFixed(0)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${plan.progress.percentage}%` }}
              />
            </div>
          </div>
        </div>

        {plan.ai_reasoning && (
          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-800">
              <strong>🤖 Razonamiento de IA:</strong> {plan.ai_reasoning}
            </p>
          </div>
        )}
      </div>

      {/* Weekly Notes */}
      {plan.plan.weekly_notes && (
        <div className="bg-white rounded-lg shadow-sm p-4">
          <h3 className="font-medium text-gray-900 mb-2">📝 Notas de la Semana</h3>
          <p className="text-sm text-gray-600">{plan.plan.weekly_notes}</p>
        </div>
      )}

      {/* Nutrition & Sleep Reminders */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {plan.plan.nutrition_focus && (
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h3 className="font-medium text-gray-900 mb-2">🥗 Enfoque Nutricional</h3>
            <p className="text-sm text-gray-600">{plan.plan.nutrition_focus}</p>
          </div>
        )}
        {plan.plan.sleep_reminder && (
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h3 className="font-medium text-gray-900 mb-2">😴 Recordatorio de Sueño</h3>
            <p className="text-sm text-gray-600">{plan.plan.sleep_reminder}</p>
          </div>
        )}
      </div>

      {/* Weekly Grid */}
      <div className="grid grid-cols-1 md:grid-cols-7 gap-4">
        {days.map((day, idx) => {
          const dateStr = weekDates[idx];
          const session = plan.plan.sessions.find((s) => s.date === dateStr);

          return (
            <div key={day} className="space-y-2">
              <div className="text-center">
                <h3 className="font-semibold text-gray-900">{day}</h3>
                <p className="text-xs text-gray-500">
                  {new Date(dateStr).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })}
                </p>
              </div>
              {session ? (
                <SessionCard key={session.id} session={session} />
              ) : (
                <div className="bg-gray-50 rounded-lg p-4 text-center text-gray-400 text-sm">
                  Sin sesión
                </div>
              )}
            </div>
          );
        })}
      </div>

      {error && (
        <div className="fixed bottom-4 right-4 p-4 bg-red-500 text-white rounded-lg shadow-lg">
          {error}
        </div>
      )}
    </div>
  );
};

export default WeeklyPlanBoard;
