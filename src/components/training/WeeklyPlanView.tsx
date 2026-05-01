import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Calendar,
  Dumbbell,
  CheckCircle,
  PlayCircle,
  AlertCircle,
  Target,
  TrendingUp,
  RefreshCw,
  ChevronRight,
  Clock,
  Zap,
} from "lucide-react";
import { plannerService } from "../../services/plannerService";
import type { WeeklyPlan, TrainingSession, PlanExercise } from "../../types";

interface WeeklyPlanViewProps {
  userId?: string;
  autoRefresh?: boolean;
}

const WEEKDAYS = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"];

const WeeklyPlanView: React.FC<WeeklyPlanViewProps> = ({
  userId = "default_user",
  autoRefresh = true,
}) => {
  const queryClient = useQueryClient();
  const [selectedDay, setSelectedDay] = useState<TrainingSession | null>(null);
  const [showWorkoutLogger, setShowWorkoutLogger] = useState(false);
  const [currentSession, setCurrentSession] = useState<TrainingSession | null>(null);
  const [showRescheduleModal, setShowRescheduleModal] = useState(false);

  const { data: planData, isLoading, error, refetch } = useQuery({
    queryKey: ["weekly-plan", userId],
    queryFn: async () => {
      const { data } = await plannerService.getCurrentWeek();
      return data;
    },
    enabled: !!userId,
    staleTime: 5 * 60 * 1000,
  });

  const generateMutation = useMutation({
    mutationFn: () => plannerService.generateWeek().then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["weekly-plan", userId] });
    },
  });

  const completeSessionMutation = useMutation({
    mutationFn: (payload: { session_id: number; actual_data: any }) =>
      plannerService.completeSession(payload).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["weekly-plan", userId] });
      setShowWorkoutLogger(false);
      setCurrentSession(null);
    },
  });

  const skipSessionMutation = useMutation({
    mutationFn: (payload: { session_id: number; reason?: string }) =>
      plannerService.skipSession(payload).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["weekly-plan", userId] });
      setSelectedDay(null);
      setCurrentSession(null);
    },
  });

  const rescheduleMutation = useMutation({
    mutationFn: (payload: { session_id: number; new_date: string }) =>
      plannerService.rescheduleSession(payload).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["weekly-plan", userId] });
      setShowRescheduleModal(false);
    },
  });

  const regeneratePlan = () => generateMutation.mutate();

  const handleSessionClick = (session: TrainingSession) => {
    setSelectedDay(session);
  };

  const handleStartWorkout = (session: TrainingSession) => {
    setCurrentSession(session);
    setShowWorkoutLogger(true);
  };

  const handleCompleteSession = (actualData: any) => {
    if (currentSession) {
      completeSessionMutation.mutate({
        session_id: currentSession.id,
        actual_data: actualData,
      });
    }
  };

  const handleSkipSession = (reason?: string) => {
    if (selectedDay) {
      skipSessionMutation.mutate({
        session_id: selectedDay.id,
        reason,
      });
      setSelectedDay(null);
    }
  };

  const handleReschedule = (newDate: string) => {
    if (selectedDay) {
      rescheduleMutation.mutate({
        session_id: selectedDay.id,
        new_date: newDate,
      });
    }
  };

  const getReadinessColor = (score?: number | null) => {
    if (score === null || score === undefined) return "bg-gray-100";
    if (score >= 75) return "bg-green-50";
    if (score >= 50) return "bg-yellow-50";
    return "bg-red-50";
  };

  const getReadinessBadge = (score?: number | null) => {
    if (score === null || score === undefined) return null;
    if (score >= 75)
      return { bg: "bg-green-500", text: "text-green-700", label: "Optimo" };
    if (score >= 50)
      return { bg: "bg-yellow-500", text: "text-yellow-700", label: "Moderado" };
    return { bg: "bg-red-500", text: "text-red-700", label: "Bajo" };
  };

  const getDifficultyColor = (session: TrainingSession) => {
    if (session.completed) return "bg-green-100 text-green-800 border-green-200";
    if (session.skipped) return "bg-gray-100 text-gray-500 border-gray-200";
    const compoundCount = session.exercises.filter((ex) =>
      ["Squat", "Deadlift", "Bench Press", "Overhead Press", "Barbell Row", "Pull-Up"].includes(ex.name)
    ).length;
    if (compoundCount >= 3) return "bg-red-50 text-red-700 border-red-200";
    if (compoundCount >= 2) return "bg-orange-50 text-orange-700 border-orange-200";
    return "bg-blue-50 text-blue-700 border-blue-200";
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("es-ES", { weekday: "short", day: "numeric", month: "short" });
  };

  const getDayStatus = (session: TrainingSession) => {
    if (session.completed)
      return { icon: <CheckCircle className="w-4 h-4" />, label: "Completado", color: "text-green-600" };
    if (session.skipped)
      return { icon: <AlertCircle className="w-4 h-4" />, label: "Omitido", color: "text-gray-400" };
    return { icon: <PlayCircle className="w-4 h-4" />, label: "Pendiente", color: "text-blue-500" };
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="text-center text-red-500">
          <AlertCircle className="w-12 h-12 mx-auto mb-4" />
          <p>
            Error al cargar el plan.{" "}
            <button onClick={() => refetch()} className="text-indigo-600 underline">
              Reintentar
            </button>
          </p>
        </div>
      </div>
    );
  }

  if (!planData?.data) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="text-center">
          <Calendar className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-xl font-semibold text-gray-700 mb-2">
            No hay plan de entrenamiento
          </h3>
          <p className="text-gray-500 mb-6">
            Genera tu primer plan semanal para empezar a entrenar
          </p>
          <button
            onClick={regeneratePlan}
            disabled={generateMutation.isPending}
            className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
          >
            {generateMutation.isPending ? "Generando..." : "Generar Plan Semanal"}
          </button>
        </div>
      </div>
    );
  }

  const plan: WeeklyPlan = planData.data;
  const weekStart = new Date(plan.week_start);
  const weekEnd = new Date(plan.week_end);
  const completedCount = plan.sessions.filter((s) => s.completed).length;
  const totalCount = plan.sessions.length;
  const completionRate = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const sessionsByDay: Record<string, TrainingSession> = {};
  for (const s of plan.sessions) {
    const d = new Date(s.scheduled_date).toISOString().split("T")[0];
    sessionsByDay[d] = s;
  }

  return (
    <div className="space-y-4">
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl shadow-lg p-5 text-white">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-xl font-bold">PLAN SEMANA</h2>
            <p className="text-indigo-100 text-sm">
              {weekStart.toLocaleDateString("es-ES", { day: "2-digit", month: "short" })} —{" "}
              {weekEnd.toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })}
            </p>
          </div>
          <div className="text-right">
            <div className="flex items-center justify-end gap-2">
              <Target className="w-4 h-4" />
              <span className="font-medium text-sm">{plan.objective}</span>
            </div>
            {plan.structure_name && (
              <div className="flex items-center justify-end gap-2 mt-1">
                <TrendingUp className="w-3 h-3" />
                <span className="text-xs text-indigo-200">{plan.structure_name}</span>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 mt-4">
          <div className="bg-white/10 rounded-lg p-2 text-center">
            <div className="text-xl font-bold">{completedCount}</div>
            <div className="text-xs text-indigo-200">Completadas</div>
          </div>
          <div className="bg-white/10 rounded-lg p-2 text-center">
            <div className="text-xl font-bold">{completionRate}%</div>
            <div className="text-xs text-indigo-200">Progreso</div>
          </div>
          <div className="bg-white/10 rounded-lg p-2 text-center">
            <div className="text-xl font-bold">{totalCount - completedCount}</div>
            <div className="text-xs text-indigo-200">Pendientes</div>
          </div>
        </div>

        <div className="flex gap-2 mt-3">
          <button
            onClick={regeneratePlan}
            disabled={generateMutation.isPending}
            className="flex-1 flex items-center justify-center gap-1 bg-white/15 hover:bg-white/25 text-white px-3 py-2 rounded-lg font-medium text-sm transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${generateMutation.isPending ? "animate-spin" : ""}`} />
            Regenerar
          </button>
          <button
            onClick={() => setSelectedDay(null)}
            className="flex-1 flex items-center justify-center gap-1 bg-white/10 hover:bg-white/20 text-white px-3 py-2 rounded-lg font-medium text-sm transition-colors"
          >
            <ChevronRight className="w-3 h-3" />
            Ver Detalles
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 md:grid-cols-7 gap-2">
        {WEEKDAYS.map((dayName, dayIdx) => {
          const today = new Date();
          const targetDate = new Date(weekStart);
          targetDate.setDate(targetDate.getDate() + dayIdx);
          const dateKey = targetDate.toISOString().split("T")[0];
          const session = sessionsByDay[dateKey];

          if (!session) {
            return (
              <div
                key={dayName}
                className="rounded-xl p-3 border-2 border-dashed border-gray-200 bg-gray-50 text-center"
              >
                <div className="text-xs font-semibold text-gray-400 mb-1">{dayName}</div>
                <div className="text-xs text-gray-300">Descanso</div>
              </div>
            );
          }

          const status = getDayStatus(session);
          const readinessBadge = getReadinessBadge(session.readiness_score);
          const difficultyColor = getDifficultyColor(session);

          return (
            <div
              key={dayName}
              onClick={() => handleSessionClick(session)}
              className={`rounded-xl p-3 border-2 cursor-pointer transition-all hover:scale-102 hover:shadow-md ${difficultyColor}`}
            >
              <div className="text-xs font-semibold mb-1">{dayName}</div>
              <div className="text-xs font-bold mb-1">{session.day_name}</div>

              {readinessBadge && (
                <div
                  className={`inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full ${readinessBadge.bg} ${readinessBadge.text} mb-1`}
                >
                  <Zap className="w-2.5 h-2.5" />
                  {session.readiness_score}
                </div>
              )}

              <div className="flex items-center gap-1 mt-1">
                <span className={status.color}>{status.icon}</span>
                <span className="text-xs">{session.exercises.length} ej.</span>
              </div>

              <div className="mt-2 pt-2 border-t border-black/10">
                <div className="flex items-center gap-1 text-xs text-gray-500">
                  <Clock className="w-2.5 h-2.5" />
                  ~{session.exercises.length * 45} min
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {plan.sessions.filter((s) => !s.completed && !s.skipped).length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <div className="flex items-center gap-2 text-amber-800">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm font-medium">
              {plan.sessions.filter((s) => !s.completed && !s.skipped).length} sesiones pendientes esta semana
            </span>
          </div>
        </div>
      )}

      {selectedDay && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-5 border-b flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-bold text-gray-900">{selectedDay.day_name}</h3>
                  {selectedDay.readiness_score && (
                    <span
                      className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
                        selectedDay.readiness_score >= 75
                          ? "bg-green-100 text-green-700"
                          : selectedDay.readiness_score >= 50
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      <Zap className="w-3 h-3" />
                      Readiness: {selectedDay.readiness_score}
                    </span>
                  )}
                </div>
                <p className="text-gray-500 text-sm">{formatDate(selectedDay.scheduled_date)}</p>
              </div>
              <button
                onClick={() => setSelectedDay(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {selectedDay.mcgill_warmup && (
              <div className="p-4 bg-amber-50 border-b border-amber-200">
                <div className="flex items-center gap-2 text-amber-800 mb-2">
                  <AlertCircle className="w-4 h-4" />
                  <span className="font-semibold text-sm">{selectedDay.mcgill_warmup.name}</span>
                </div>
                <p className="text-xs text-amber-700">{selectedDay.mcgill_warmup.notes}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {selectedDay.mcgill_warmup.exercises.map((ex: any, idx: number) => (
                    <span key={idx} className="text-xs bg-amber-100 text-amber-800 px-2 py-1 rounded">
                      {ex.name} {ex.reps}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="p-4 space-y-3">
              {selectedDay.exercises.map((ex, idx) => (
                <div
                  key={idx}
                  className="border rounded-lg p-3 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="bg-indigo-100 p-1.5 rounded-lg">
                        <Dumbbell className="w-4 h-4 text-indigo-600" />
                      </div>
                      <div>
                        <h4 className="font-semibold text-gray-900 text-sm">{ex.name}</h4>
                        {ex.progression_note && (
                          <p className="text-xs text-indigo-600 mt-0.5">{ex.progression_note}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {ex.intensity_percentage && (
                        <span className="text-xs bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded">
                          {ex.intensity_percentage}% 1RM
                        </span>
                      )}
                      {ex.superset_with && (
                        <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">
                          SS: {ex.superset_with}
                        </span>
                      )}
                      {ex.drop_set && (
                        <span className="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">
                          Drop Set
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div className="bg-gray-50 rounded-lg p-2 text-center">
                      <div className="font-semibold text-gray-900">{ex.sets}</div>
                      <div className="text-gray-500 text-xs">Series</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-2 text-center">
                      <div className="font-semibold text-gray-900">{ex.target_weight}kg</div>
                      <div className="text-gray-500 text-xs">Peso</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-2 text-center">
                      <div className="font-semibold text-gray-900">{ex.target_reps}</div>
                      <div className="text-gray-500 text-xs">Reps</div>
                    </div>
                  </div>

                  <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
                    {ex.rpe_target && <span>RPE: {ex.rpe_target}</span>}
                    {ex.rest && <span>Descanso: {ex.rest}</span>}
                    {ex.tempo && <span>Tempo: {ex.tempo}</span>}
                  </div>
                </div>
              ))}
            </div>

            <div className="p-4 border-t flex gap-2 flex-wrap">
              {!selectedDay.completed && !selectedDay.skipped && (
                <>
                  <button
                    onClick={() => handleStartWorkout(selectedDay)}
                    className="flex-1 bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 transition-colors text-sm"
                  >
                    Empezar Sesion
                  </button>
                  <button
                    onClick={() => setShowRescheduleModal(true)}
                    className="bg-amber-100 text-amber-700 px-4 py-2.5 rounded-lg font-medium hover:bg-amber-200 transition-colors text-sm"
                  >
                    Reprogramar
                  </button>
                  <button
                    onClick={() => handleSkipSession("Baja disponibilidad / fatiga")}
                    className="bg-gray-200 text-gray-700 px-4 py-2.5 rounded-lg font-medium hover:bg-gray-300 transition-colors text-sm"
                  >
                    Omitir
                  </button>
                </>
              )}
              {selectedDay.completed && (
                <div className="flex-1 bg-green-100 text-green-700 py-2.5 rounded-lg font-medium text-center text-sm">
                  Sesion Completada
                </div>
              )}
              {selectedDay.skipped && (
                <div className="flex-1 bg-gray-100 text-gray-500 py-2.5 rounded-lg font-medium text-center text-sm">
                  Sesion Omitida
                </div>
              )}
              <button
                onClick={() => setSelectedDay(null)}
                className="bg-gray-200 text-gray-700 px-4 py-2.5 rounded-lg font-medium hover:bg-gray-300 transition-colors text-sm"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {showRescheduleModal && selectedDay && (
        <RescheduleModal
          session={selectedDay}
          weekStart={plan.week_start}
          weekEnd={plan.week_end}
          onReschedule={handleReschedule}
          onClose={() => setShowRescheduleModal(false)}
          isLoading={rescheduleMutation.isPending}
        />
      )}

      {showWorkoutLogger && currentSession && (
        <WorkoutLogger
          session={currentSession}
          onClose={() => {
            setShowWorkoutLogger(false);
            setCurrentSession(null);
          }}
          onComplete={handleCompleteSession}
        />
      )}
    </div>
  );
};

const RescheduleModal: React.FC<{
  session: TrainingSession;
  weekStart: string;
  weekEnd: string;
  onReschedule: (newDate: string) => void;
  onClose: () => void;
  isLoading: boolean;
}> = ({ session, weekStart, weekEnd, onReschedule, onClose, isLoading }) => {
  const [selectedDate, setSelectedDate] = useState("");

  const availableDates: string[] = [];
  const start = new Date(weekStart);
  for (let i = 0; i < 7; i++) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    availableDates.push(d.toISOString().split("T")[0]);
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-sm w-full p-5">
        <h3 className="text-lg font-bold text-gray-900 mb-1">Reprogramar Sesion</h3>
        <p className="text-sm text-gray-500 mb-4">
          {session.day_name} — {formatDate(session.scheduled_date)}
        </p>

        <div className="space-y-2 mb-4">
          {availableDates.map((d) => (
            <button
              key={d}
              onClick={() => setSelectedDate(d)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                selectedDate === d
                  ? "bg-indigo-100 text-indigo-700 border-2 border-indigo-400"
                  : "bg-gray-50 hover:bg-gray-100 border-2 border-transparent"
              }`}
            >
              {new Date(d).toLocaleDateString("es-ES", {
                weekday: "long",
                day: "numeric",
                month: "long",
              })}
            </button>
          ))}
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => selectedDate && onReschedule(selectedDate)}
            disabled={!selectedDate || isLoading}
            className="flex-1 bg-indigo-600 text-white py-2 rounded-lg font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 text-sm"
          >
            {isLoading ? "Reprogramando..." : "Confirmar"}
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition-colors text-sm"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
};

const WorkoutLogger: React.FC<{
  session: TrainingSession;
  onClose: () => void;
  onComplete: (actualData: any) => void;
}> = ({ session, onClose, onComplete }) => {
  interface LoggedExercise {
    name: string;
    target_weight: number;
    target_reps: number;
    rpe_target?: number;
    progression_note?: string;
    sets: Array<{ setNumber: number; weight: number; reps: number; rpe: number; completed: boolean }>;
  }
  const [exercises, setExercises] = useState<LoggedExercise[]>(
    session.exercises.map((ex) => ({
      name: ex.name,
      target_weight: ex.target_weight,
      target_reps: ex.target_reps,
      rpe_target: ex.rpe_target,
      progression_note: ex.progression_note,
      sets: Array(ex.sets)
        .fill(null)
        .map((_, i) => ({
          setNumber: i + 1,
          weight: ex.target_weight,
          reps: typeof ex.target_reps === "number" ? ex.target_reps : 8,
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
        sets: ex.sets.map((s) => ({
          setNumber: s.setNumber,
          weight: s.weight,
          reps: s.reps,
          rpe: s.rpe,
          completed: s.completed,
        })),
        totalSets: ex.sets.length,
        avgWeight:
          ex.sets.reduce((sum, s) => sum + s.weight, 0) / ex.sets.length,
        totalReps: ex.sets.reduce((sum, s) => sum + s.reps, 0),
      })),
      completedAt: new Date().toISOString(),
    };
    onComplete(actualData);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-5 border-b flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-gray-900">{session.day_name}</h3>
            <p className="text-gray-500 text-sm">Registra tu entrenamiento</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-4 space-y-4">
          {exercises.map((ex, exIdx) => (
            <div key={exIdx} className="border rounded-lg p-3">
              <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <span className="bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded text-xs">
                  {ex.target_weight}kg x {ex.target_reps}
                </span>
                {ex.name}
              </h4>
              <div className="space-y-2">
                {ex.sets.map((set, setIdx) => (
                  <div
                    key={setIdx}
                    className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg text-sm"
                  >
                    <span className="w-8 text-xs font-medium text-gray-500">Set {set.setNumber}</span>
                    <input
                      type="number"
                      value={set.weight}
                      onChange={(e) => updateSet(exIdx, setIdx, "weight", parseFloat(e.target.value) || 0)}
                      className="w-16 px-2 py-1 border rounded text-sm"
                      placeholder="kg"
                    />
                    <span className="text-gray-400">x</span>
                    <input
                      type="number"
                      value={set.reps}
                      onChange={(e) => updateSet(exIdx, setIdx, "reps", parseInt(e.target.value) || 0)}
                      className="w-14 px-2 py-1 border rounded text-sm"
                      placeholder="reps"
                    />
                    <span className="text-xs text-gray-500 ml-1">RPE</span>
                    <input
                      type="number"
                      value={set.rpe}
                      onChange={(e) => updateSet(exIdx, setIdx, "rpe", parseInt(e.target.value) || 0)}
                      className="w-12 px-2 py-1 border rounded text-sm"
                      min="1"
                      max="10"
                    />
                    <label className="flex items-center gap-1 ml-auto">
                      <input
                        type="checkbox"
                        checked={set.completed}
                        onChange={(e) => updateSet(exIdx, setIdx, "completed", e.target.checked)}
                        className="w-4 h-4 rounded text-indigo-600"
                      />
                      <span className="text-xs text-gray-500">Hecho</span>
                    </label>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="p-4 border-t flex gap-2">
          <button
            onClick={handleComplete}
            className="flex-1 bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 transition-colors text-sm"
          >
            Guardar Entrenamiento
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2.5 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition-colors text-sm"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
};

const formatDate = (dateStr: string) =>
  new Date(dateStr).toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" });

export default WeeklyPlanView;