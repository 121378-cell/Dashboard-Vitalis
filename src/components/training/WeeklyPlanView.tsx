import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Calendar, Dumbbell, CheckCircle, PlayCircle, AlertCircle, Target, TrendingUp } from 'lucide-react';

interface Exercise {
  name: string;
  sets: number;
  reps: number | string;
  target_weight: number;
  target_reps: number;
  rpe_target?: number;
  intensity_percentage?: number;
  progression_note?: string;
  rest?: string;
  tempo?: string;
  notes?: string;
}

interface TrainingSession {
  id: number;
  day: number;
  day_name: string;
  scheduled_date: string;
  exercises: Exercise[];
  completed: boolean;
  actual_data?: any;
  skipped?: boolean;
}

interface WeeklyPlan {
  id: number;
  user_id: string;
  week_start: string;
  week_end: string;
  generated_at: string;
  status: string;
  objective: string;
  structure_name: string;
  sessions: TrainingSession[];
  plan_data: any;
}

interface WeeklyPlanViewProps {
  userId?: string;
  autoRefresh?: boolean;
}

const WeeklyPlanView: React.FC<WeeklyPlanViewProps> = ({ 
  userId = 'default_user',
  autoRefresh = true 
}) => {
  const queryClient = useQueryClient();
  const [selectedDay, setSelectedDay] = useState<TrainingSession | null>(null);
  const [showWorkoutLogger, setShowWorkoutLogger] = useState(false);
  const [currentSession, setCurrentSession] = useState<TrainingSession | null>(null);

  const { data: planData, isLoading, error, refetch } = useQuery<{
    status: string;
    data: WeeklyPlan;
    message: string;
  }>({
    queryKey: ['weekly-plan', userId],
    queryFn: async () => {
      const response = await axios.get(`/api/v1/planner/current-week`);
      return response.data;
    },
    enabled: !!userId,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (!autoRefresh) return;
    const checkRegenerate = () => {
      const now = new Date();
      const day = now.getDay();
      const hour = now.getHours();
      const minute = now.getMinutes();
      if (day === 0 && hour === 20 && minute === 0) {
        regeneratePlan();
      }
    };
    const interval = setInterval(checkRegenerate, 60000);
    return () => clearInterval(interval);
  }, [autoRefresh, userId]);

  const generateMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post('/api/v1/planner/generate-week');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['weekly-plan', userId] });
    },
  });

  const completeSessionMutation = useMutation({
    mutationFn: async ({ sessionId, actualData }: { sessionId: number; actualData: any }) => {
      const response = await axios.post('/api/v1/planner/complete-session', {
        session_id: sessionId,
        actual_data: actualData,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['weekly-plan', userId] });
      setShowWorkoutLogger(false);
      setCurrentSession(null);
    },
  });

  const skipSessionMutation = useMutation({
    mutationFn: async ({ sessionId, reason }: { sessionId: number; reason?: string }) => {
      const response = await axios.post('/api/v1/planner/skip-session', {
        session_id: sessionId,
        reason,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['weekly-plan', userId] });
    },
  });

  const regeneratePlan = async () => {
    await generateMutation.mutateAsync();
  };

  const handleSessionClick = (session: TrainingSession) => {
    setSelectedDay(session);
    setCurrentSession(session);
  };

  const handleStartWorkout = (session: TrainingSession) => {
    setCurrentSession(session);
    setShowWorkoutLogger(true);
  };

  const handleCompleteSession = async (actualData: any) => {
    if (currentSession) {
      await completeSessionMutation.mutateAsync({
        sessionId: currentSession.id,
        actualData,
      });
    }
  };

  const handleSkipSession = async (reason?: string) => {
    if (currentSession) {
      await skipSessionMutation.mutateAsync({
        sessionId: currentSession.id,
        reason,
      });
      setSelectedDay(null);
      setCurrentSession(null);
    }
  };

  const getDifficultyColor = (session: TrainingSession) => {
    if (session.completed) return 'bg-green-100 text-green-800 border-green-200';
    if (session.skipped) return 'bg-gray-100 text-gray-500 border-gray-200';
    const compoundCount = session.exercises.filter(ex => 
      ['Squat', 'Deadlift', 'Bench Press', 'Overhead Press', 'Barbell Row', 'Pull-Up'].includes(ex.name)
    ).length;
    if (compoundCount >= 3) return 'bg-red-50 text-red-700 border-red-200';
    if (compoundCount >= 2) return 'bg-orange-50 text-orange-700 border-orange-200';
    return 'bg-blue-50 text-blue-700 border-blue-200';
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short' });
  };

  const getDayStatus = (session: TrainingSession) => {
    if (session.completed) return { icon: <CheckCircle className="w-5 h-5" />, label: 'Completado', color: 'text-green-600' };
    if (session.skipped) return { icon: <AlertCircle className="w-5 h-5" />, label: 'Omitido', color: 'text-gray-400' };
    return { icon: <PlayCircle className="w-5 h-5" />, label: 'Pendiente', color: 'text-blue-500' };
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="text-center text-red-500">
          <AlertCircle className="w-12 h-12 mx-auto mb-4" />
          <p>Error al cargar el plan. <button onClick={() => refetch()} className="text-indigo-600 underline">Reintentar</button></p>
        </div>
      </div>
    );
  }

  if (!planData?.data) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="text-center">
          <Calendar className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-xl font-semibold text-gray-700 mb-2">No hay plan de entrenamiento</h3>
          <p className="text-gray-500 mb-6">Genera tu primer plan semanal para empezar a entrenar</p>
          <button
            onClick={regeneratePlan}
            disabled={generateMutation.isPending}
            className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
          >
            {generateMutation.isPending ? 'Generando...' : 'Generar Plan Semanal'}
          </button>
        </div>
      </div>
    );
  }

  const plan = planData.data;
  const weekStart = new Date(plan.week_start);
  const weekEnd = new Date(plan.week_end);
  const completedCount = plan.sessions.filter((s: TrainingSession) => s.completed).length;
  const totalCount = plan.sessions.length;
  const completionRate = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl shadow-lg p-6 text-white">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold">Plan Semanal</h2>
            <p className="text-indigo-100">
              {weekStart.toLocaleDateString('es-ES', { day: '2-digit', month: 'long' })} -{' '}
              {weekEnd.toLocaleDateString('es-ES', { day: '2-digit', month: 'long', year: 'numeric' })}
            </p>
          </div>
          <div className="text-right">
            <div className="flex items-center justify-end gap-2">
              <Target className="w-5 h-5" />
              <span className="font-medium">{plan.objective}</span>
            </div>
            <div className="flex items-center justify-end gap-2 mt-1">
              <TrendingUp className="w-4 h-4" />
              <span className="text-sm text-indigo-200">{plan.structure_name}</span>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 mt-6">
          <div className="bg-white/10 rounded-lg p-3">
            <div className="text-2xl font-bold">{completedCount}</div>
            <div className="text-sm text-indigo-200">Sesiones Completadas</div>
          </div>
          <div className="bg-white/10 rounded-lg p-3">
            <div className="text-2xl font-bold">{completionRate}%</div>
            <div className="text-sm text-indigo-200">Progreso</div>
          </div>
          <div className="bg-white/10 rounded-lg p-3">
            <div className="text-2xl font-bold">{totalCount - completedCount}</div>
            <div className="text-sm text-indigo-200">Pendientes</div>
          </div>
        </div>
        <div className="flex gap-3 mt-4">
          <button
            onClick={regeneratePlan}
            disabled={generateMutation.isPending}
            className="flex-1 bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {generateMutation.isPending ? 'Generando...' : '↻ Regenerar Plan'}
          </button>
          <button
            onClick={() => setSelectedDay(null)}
            className="flex-1 bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            Ver Detalles
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {plan.sessions.map((session: TrainingSession) => {
          const status = getDayStatus(session);
          const difficultyColor = getDifficultyColor(session);
          return (
            <div
              key={session.id}
              onClick={() => handleSessionClick(session)}
              className={`rounded-xl p-4 border-2 cursor-pointer transition-all hover:scale-105 hover:shadow-lg ${difficultyColor}`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  <span className="font-semibold text-sm">{session.day_name}</span>
                </div>
                <span className={status.color}>{status.icon}</span>
              </div>
              <div className="text-xs text-gray-500 mb-2">
                {formatDate(session.scheduled_date)}
              </div>
              <div className="space-y-1">
                {session.exercises.slice(0, 3).map((ex, idx) => (
                  <div key={idx} className="text-xs truncate flex items-center gap-1">
                    <Dumbbell className="w-3 h-3 flex-shrink-0" />
                    <span>{ex.name}</span>
                    <span className="text-gray-400 ml-auto">
                      {ex.target_weight}kg × {ex.reps}
                    </span>
                  </div>
                ))}
                {session.exercises.length > 3 && (
                  <div className="text-xs text-gray-400">
                    +{session.exercises.length - 3} ejercicios más
                  </div>
                )}
              </div>
              <div className="mt-3 pt-2 border-t border-white/20">
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-medium">{session.exercises.length} ejercicios</span>
                  <span className="text-gray-300">•</span>
                  <span className="text-gray-300">~{session.exercises.length * 45} min</span>
                </div>
              </div>

            </div>
          );
        })}
      </div>

      {selectedDay && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-2xl font-bold text-gray-900">{selectedDay.day_name}</h3>
                  <p className="text-gray-500">{formatDate(selectedDay.scheduled_date)}</p>
                </div>
                <button onClick={() => setSelectedDay(null)} className="text-gray-400 hover:text-gray-600">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="p-6">
              <div className="grid gap-4">
                {selectedDay.exercises.map((ex, idx) => (
                  <div key={idx} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <div className="bg-indigo-100 p-2 rounded-lg">
                          <Dumbbell className="w-5 h-5 text-indigo-600" />
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-900">{ex.name}</h4>
                          {ex.progression_note && <p className="text-xs text-indigo-600 mt-1">{ex.progression_note}</p>}
                        </div>
                      </div>
                      {ex.intensity_percentage && (
                        <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded">{ex.intensity_percentage}% 1RM</span>
                      )}
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div className="bg-gray-50 rounded-lg p-2 text-center">
                        <div className="font-semibold text-gray-900">{ex.sets}</div>
                        <div className="text-gray-500">Series</div>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-2 text-center">
                        <div className="font-semibold text-gray-900">{ex.target_weight}kg</div>
                        <div className="text-gray-500">Peso</div>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-2 text-center">
                        <div className="font-semibold text-gray-900">{ex.target_reps}</div>
                        <div className="text-gray-500">Reps</div>
                      </div>
                    </div>
                    <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
                      {ex.rpe_target && <span>RPE objetivo: {ex.rpe_target}</span>}
                      {ex.rest && <span>Descanso: {ex.rest}</span>}
                      {ex.tempo && <span>Tempo: {ex.tempo}</span>}
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-6 flex gap-3">
                {!selectedDay.completed && !selectedDay.skipped && (
                  <button onClick={() => handleStartWorkout(selectedDay)} className="flex-1 bg-indigo-600 text-white py-3 rounded-lg font-medium hover:bg-indigo-700 transition-colors">
                    Empezar Entrenamiento
                  </button>
                )}
                {!selectedDay.completed && !selectedDay.skipped && (
                  <button onClick={() => handleSkipSession('Baja disponibilidad / fatiga')} className="flex-1 bg-gray-200 text-gray-700 py-3 rounded-lg font-medium hover:bg-gray-300 transition-colors">
                    Omitir Sesión
                  </button>
                )}
                {selectedDay.completed && <div className="flex-1 bg-green-100 text-green-700 py-3 rounded-lg font-medium text-center">✓ Sesión Completada</div>}
                {selectedDay.skipped && <div className="flex-1 bg-gray-100 text-gray-500 py-3 rounded-lg font-medium text-center">⏭ Sesión Omitida</div>}
                <button onClick={() => setSelectedDay(null)} className="bg-gray-200 text-gray-700 px-6 py-3 rounded-lg font-medium hover:bg-gray-300 transition-colors">Cerrar</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showWorkoutLogger && currentSession && (
        <WorkoutLogger session={currentSession} onClose={() => { setShowWorkoutLogger(false); setCurrentSession(null); }} onComplete={handleCompleteSession} />
      )}
    </div>
  );
};

const WorkoutLogger: React.FC<{ session: TrainingSession; onClose: () => void; onComplete: (actualData: any) => void }> = ({ session, onClose, onComplete }) => {
  const [exercises, setExercises] = useState(
    session.exercises.map((ex) => ({
      ...ex,
      sets: Array(ex.sets).fill(null).map((_, i) => ({
        setNumber: i + 1,
        weight: ex.target_weight,
        reps: typeof ex.target_reps === 'number' ? ex.target_reps : 8,
        rpe: ex.rpe_target || 8,
        completed: false,
      })),
    }))
  );

  const updateSet = (exIdx: number, setIdx: number, field: string, value: any) => {
    setExercises((prev) =>
      prev.map((ex, eIdx) => {
        if (eIdx !== exIdx) return ex;
        const newSets = [...ex.sets];
        newSets[setIdx] = { ...newSets[setIdx], [field]: value };
        return { ...ex, sets: newSets };
      })
    );
  };

  const handleComplete = () => {
    const actualData = {
      exercises: exercises.map((ex) => ({
        name: ex.name,
        sets: ex.sets.map((s) => ({ setNumber: s.setNumber, weight: s.weight, reps: s.reps, rpe: s.rpe, completed: s.completed })),
        totalSets: ex.sets.length,
        avgWeight: ex.sets.reduce((sum, s) => sum + s.weight, 0) / ex.sets.length,
        totalReps: ex.sets.reduce((sum, s) => sum + s.reps, 0),
      })),
      completedAt: new Date().toISOString(),
    };
    onComplete(actualData);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-gray-900">{session.day_name}</h3>
            <p className="text-gray-500">Registra tu entrenamiento</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="p-6 space-y-6">
          {exercises.map((ex, exIdx) => (
            <div key={exIdx} className="border rounded-lg p-4">
              <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <span className="bg-indigo-100 text-indigo-700 px-2 py-1 rounded text-sm">{ex.target_weight}kg × {ex.target_reps}</span>
                {ex.name}
              </h4>
              <div className="space-y-3">
                {ex.sets.map((set, setIdx) => (
                  <div key={setIdx} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <span className="w-8 text-sm font-medium text-gray-500">Set {set.setNumber}</span>
                    <input type="number" value={set.weight} onChange={(e) => updateSet(exIdx, setIdx, 'weight', parseFloat(e.target.value) || 0)} className="w-16 px-2 py-1 border rounded-lg text-sm" placeholder="kg" />
                    <span className="text-gray-400">×</span>
                    <input type="number" value={set.reps} onChange={(e) => updateSet(exIdx, setIdx, 'reps', parseInt(e.target.value) || 0)} className="w-16 px-2 py-1 border rounded-lg text-sm" placeholder="reps" />
                    <span className="text-sm text-gray-500">RPE</span>
                    <input type="number" value={set.rpe} onChange={(e) => updateSet(exIdx, setIdx, 'rpe', parseInt(e.target.value) || 0)} className="w-12 px-2 py-1 border rounded-lg text-sm" min="1" max="10" />
                    <label className="flex items-center gap-2 ml-auto">
                      <input type="checkbox" checked={set.completed} onChange={(e) => updateSet(exIdx, setIdx, 'completed', e.target.checked)} className="w-4 h-4 rounded text-indigo-600" />
                      <span className="text-sm text-gray-500">Hecho</span>
                    </label>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="p-6 border-t flex gap-3">
          <button onClick={handleComplete} className="flex-1 bg-indigo-600 text-white py-3 rounded-lg font-medium hover:bg-indigo-700 transition-colors">Guardar Entrenamiento</button>
          <button onClick={onClose} className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition-colors">Cancelar</button>
        </div>
      </div>
    </div>
  );
};

export default WeeklyPlanView;
