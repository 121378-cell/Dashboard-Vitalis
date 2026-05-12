import React from 'react';
import { motion } from 'framer-motion';
import type { AdaptiveWeeklyPlan, AdaptivePlanSession } from '../../types';

interface WeeklyCalendarProps {
  plan: AdaptiveWeeklyPlan;
  onSelectSession: (session: AdaptivePlanSession) => void;
  onCompleteSession: (sessionId: number, completed: boolean) => void;
  onDetectCompleted: () => void;
  detecting: boolean;
}

const SESSION_ICONS: Record<AdaptivePlanSession['session_type'], string> = {
  strength: '💪',
  running: '🏃',
  trail_running: '🏔️',
  mobility: '🧘',
  hiit: '⚡',
  rest: '😴',
  active_recovery: '🔄',
};

const INTENSITY_COLORS: Record<string, string> = {
  low: 'bg-emerald-500/20 text-emerald-400',
  medium: 'bg-amber-500/20 text-amber-400',
  high: 'bg-red-500/20 text-red-400',
};

const DAY_NAMES_SHORT = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];

function isToday(dateStr: string): boolean {
  return dateStr === new Date().toISOString().split('T')[0];
}

function formatDayDate(dateStr: string): { dayName: string; dateStr: string } {
  const d = new Date(dateStr + 'T12:00:00');
  const dayName = DAY_NAMES_SHORT[d.getDay()];
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  return { dayName, dateStr: `${day}/${month}` };
}

function formatWeekRange(weekStart: string, weekEnd: string): string {
  const s = new Date(weekStart + 'T12:00:00');
  const e = new Date(weekEnd + 'T12:00:00');
  const months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  return `${s.getDate()} ${months[s.getMonth()]} - ${e.getDate()} ${months[e.getMonth()]}`;
}

function getDaysOfWeek(weekStart: string): string[] {
  const days: string[] = [];
  const start = new Date(weekStart + 'T12:00:00');
  for (let i = 0; i < 7; i++) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    days.push(d.toISOString().split('T')[0]);
  }
  return days;
}

const WeeklyCalendar: React.FC<WeeklyCalendarProps> = ({
  plan,
  onSelectSession,
  onCompleteSession,
  onDetectCompleted,
  detecting,
}) => {
  const sessionsByDate = new Map<string, AdaptivePlanSession>();
  for (const session of plan.plan.sessions) {
    sessionsByDate.set(session.date, session);
  }

  const days = getDaysOfWeek(plan.week_start);
  const { completed, total, percentage } = plan.progress;

  return (
    <div className="space-y-4">
      <div
        className="rounded-2xl p-5 border"
        style={{ backgroundColor: '#13131A', borderColor: '#1C1C26' }}
      >
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4">
          <div className="flex-1 min-w-0">
            <h2
              className="text-lg font-bold truncate"
              style={{ fontFamily: "'Orbitron', sans-serif", color: '#F0F0FF' }}
            >
              {plan.plan.weekly_goal}
            </h2>
            <p
              className="text-sm mt-1 line-clamp-2"
              style={{ color: '#6B6B8A' }}
            >
              {plan.ai_reasoning}
            </p>
          </div>
          <button
            onClick={onDetectCompleted}
            disabled={detecting}
            className="flex-shrink-0 px-4 py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50"
            style={{
              backgroundColor: '#E8FF47',
              color: '#0A0A0F',
            }}
          >
            {detecting ? 'Detectando...' : 'Detectar Completadas'}
          </button>
        </div>

        <div className="mb-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium" style={{ color: '#6B6B8A' }}>
              Progreso semanal
            </span>
            <span className="text-xs font-bold" style={{ color: '#F0F0FF' }}>
              {completed}/{total} sesiones · {percentage}%
            </span>
          </div>
          <div
            className="h-2 rounded-full overflow-hidden"
            style={{ backgroundColor: '#1C1C26' }}
          >
            <motion.div
              className="h-full rounded-full"
              style={{ backgroundColor: '#4ADE80' }}
              initial={{ width: 0 }}
              animate={{ width: `${percentage}%` }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
            />
          </div>
        </div>

        {(plan.plan.nutrition_focus || plan.plan.sleep_reminder) && (
          <div className="flex flex-wrap gap-2 mt-3">
            {plan.plan.nutrition_focus && (
              <div
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs"
                style={{ backgroundColor: '#1C1C26', color: '#F0F0FF' }}
              >
                <span>🥗</span>
                <span>{plan.plan.nutrition_focus}</span>
              </div>
            )}
            {plan.plan.sleep_reminder && (
              <div
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs"
                style={{ backgroundColor: '#1C1C26', color: '#F0F0FF' }}
              >
                <span>😴</span>
                <span>{plan.plan.sleep_reminder}</span>
              </div>
            )}
          </div>
        )}

        <div className="mt-3 pt-3" style={{ borderTop: '1px solid #1C1C26' }}>
          <span className="text-xs" style={{ color: '#6B6B8A' }}>
            {formatWeekRange(plan.week_start, plan.week_end)}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-2">
        {days.map((date) => {
          const session = sessionsByDate.get(date);
          const today = isToday(date);
          const { dayName, dateStr: dayDate } = formatDayDate(date);

          if (!session) {
            return (
              <div
                key={date}
                className="rounded-xl p-3 border text-center"
                style={{
                  backgroundColor: '#0A0A0F',
                  borderColor: today ? '#E8FF47' : '#1C1C26',
                }}
              >
                <div className="flex items-center justify-center gap-1.5 mb-2">
                  <span
                    className="text-xs font-semibold"
                    style={{ color: '#6B6B8A' }}
                  >
                    {dayName} {dayDate}
                  </span>
                  {today && (
                    <span
                      className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                      style={{ backgroundColor: '#E8FF47', color: '#0A0A0F' }}
                    >
                      HOY
                    </span>
                  )}
                </div>
                <div className="py-4">
                  <span className="text-2xl">😴</span>
                  <p
                    className="text-xs mt-2 font-medium"
                    style={{ color: '#6B6B8A' }}
                  >
                    Descanso
                  </p>
                </div>
              </div>
            );
          }

          const isCompleted = session.completed;
          const isAdapted = !!session.adaptation_reason;
          const borderColor = isCompleted
            ? '#4ADE80'
            : today
            ? '#E8FF47'
            : '#1C1C26';
          const icon = SESSION_ICONS[session.session_type] || '🏋️';
          const intensityClass = session.intensity
            ? INTENSITY_COLORS[session.intensity]
            : '';

          return (
            <motion.div
              key={date}
              whileHover={{ scale: 1.02, boxShadow: '0 4px 24px rgba(0,0,0,0.4)' }}
              transition={{ type: 'tween', duration: 0.15 }}
              onClick={() => onSelectSession(session)}
              className="relative rounded-xl p-3 border cursor-pointer overflow-hidden"
              style={{
                backgroundColor: isCompleted ? '#0A0A0F' : '#13131A',
                borderColor,
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <span
                  className="text-xs font-semibold"
                  style={{ color: '#6B6B8A' }}
                >
                  {dayName} {dayDate}
                </span>
                <div className="flex items-center gap-1.5">
                  {today && (
                    <span
                      className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                      style={{ backgroundColor: '#E8FF47', color: '#0A0A0F' }}
                    >
                      HOY
                    </span>
                  )}
                  {isAdapted && (
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400">
                      Adaptado
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-start gap-2">
                <span className="text-xl leading-none mt-0.5">{icon}</span>
                <div className="flex-1 min-w-0">
                  <p
                    className="text-sm font-semibold truncate"
                    style={{ color: '#F0F0FF' }}
                  >
                    {session.title}
                  </p>
                  <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                    {session.duration_minutes != null && (
                      <span
                        className="text-[11px]"
                        style={{ color: '#6B6B8A' }}
                      >
                        {session.duration_minutes}min
                      </span>
                    )}
                    {session.intensity && (
                      <span
                        className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${intensityClass}`}
                      >
                        {session.intensity === 'low'
                          ? 'Baja'
                          : session.intensity === 'medium'
                          ? 'Media'
                          : 'Alta'}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {isCompleted && (
                <div
                  className="absolute top-2 right-2 flex items-center justify-center w-5 h-5 rounded-full"
                  style={{ backgroundColor: '#4ADE80' }}
                >
                  <svg
                    className="w-3 h-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="#0A0A0F"
                    strokeWidth={3}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </div>
              )}

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onCompleteSession(session.id, !session.completed);
                }}
                className="absolute bottom-2 right-2 w-4 h-4 rounded-sm border flex items-center justify-center transition-colors"
                style={{
                  backgroundColor: isCompleted ? '#4ADE80' : 'transparent',
                  borderColor: isCompleted ? '#4ADE80' : '#6B6B8A',
                }}
                aria-label={isCompleted ? 'Marcar como no completada' : 'Marcar como completada'}
              >
                {isCompleted && (
                  <svg
                    className="w-2.5 h-2.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="#0A0A0F"
                    strokeWidth={4}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                )}
              </button>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};

export default WeeklyCalendar;
