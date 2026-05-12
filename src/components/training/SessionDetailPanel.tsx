import React, { useState, useEffect, useRef, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  X,
  Dumbbell,
  Zap,
  Timer,
  ArrowUp,
  ArrowDown,
  Trophy,
  Play,
  Pause,
  Square,
  Send,
  ChevronRight,
  Moon,
  Droplets,
  BedDouble,
  Activity,
} from 'lucide-react';
import type {
  AdaptivePlanSession,
  ExerciseProgression,
  PlanSessionExercise,
} from '../../types';

interface SessionDetailPanelProps {
  session: AdaptivePlanSession | null;
  onClose: () => void;
  onComplete: (sessionId: number, completed: boolean) => void;
  onAdapt: (sessionId: number, request: string) => void;
  progressions: ExerciseProgression[];
  progressionsLoading: boolean;
  readiness?: number | null;
}

const BG = '#0A0A0F';
const SURFACE = '#13131A';
const SURFACE_HIGH = '#1C1C26';
const PRIMARY = '#E8FF47';
const ON_PRIMARY = '#0A0A0F';
const TEXT = '#F0F0FF';
const TEXT_MUTED = '#6B6B8A';
const SUCCESS = '#4ADE80';
const WARNING = '#FB923C';
const DANGER = '#F87171';

const HR_ZONE_COLORS: Record<string, string> = {
  Z1: '#3B82F6',
  Z2: '#22C55E',
  Z3: '#EAB308',
  Z4: '#F97316',
  Z5: '#EF4444',
};

const SESSION_TYPE_ICONS: Record<string, React.ReactNode> = {
  strength: <Dumbbell size={18} />,
  hiit: <Zap size={18} />,
  running: <Activity size={18} />,
  trail_running: <Activity size={18} />,
  mobility: <span style={{ fontSize: 16 }}>🧘</span>,
  active_recovery: <span style={{ fontSize: 16 }}>🧘</span>,
  rest: <Moon size={18} />,
};

const MOBILITY_FOCUS_ICONS: Record<string, string> = {
  lower_body: '🦵',
  upper_body: '💪',
  full_body: '🧘',
  spine: '🦴',
};

const INTENSITY_COLORS: Record<string, string> = {
  low: SUCCESS,
  medium: WARNING,
  high: DANGER,
};

const INTENSITY_LABELS: Record<string, string> = {
  low: 'Baja',
  medium: 'Media',
  high: 'Alta',
};

function formatMMSS(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function parseHRZone(zone: string): { label: string; color: string }[] {
  const zones: { label: string; color: string }[] = [];
  const normalized = zone.toUpperCase().replace(/\s/g, '');
  const matches = normalized.match(/Z[1-5]/g);
  if (matches) {
    const seen = new Set<string>();
    for (const z of matches) {
      if (!seen.has(z)) {
        seen.add(z);
        zones.push({ label: z, color: HR_ZONE_COLORS[z] || '#6B6B8A' });
      }
    }
  }
  if (zones.length === 0) {
    zones.push({ label: 'Z2', color: HR_ZONE_COLORS.Z2 });
  }
  return zones;
}

function parseStructure(structure: string): string[] {
  return structure
    .split(/\+|→/)
    .map((s) => s.trim())
    .filter(Boolean);
}

const RestTimer: React.FC<{ restSeconds: number }> = ({ restSeconds }) => {
  const [running, setRunning] = useState(false);
  const [remaining, setRemaining] = useState(restSeconds);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = useCallback(() => {
    setRunning(false);
    setRemaining(restSeconds);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, [restSeconds]);

  useEffect(() => {
    if (running && remaining > 0) {
      intervalRef.current = setInterval(() => {
        setRemaining((prev) => {
          if (prev <= 1) {
            setRunning(false);
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [running, remaining]);

  if (remaining === 0 && !running) {
    return (
      <button
        onClick={() => {
          setRemaining(restSeconds);
          setRunning(true);
        }}
        className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-colors"
        style={{ background: SURFACE_HIGH, color: TEXT_MUTED, border: `1px solid ${PRIMARY}22` }}
      >
        <Timer size={10} />
        Iniciar descanso
      </button>
    );
  }

  return (
    <div className="flex items-center gap-1.5">
      <span
        className="font-mono text-xs font-bold"
        style={{ color: remaining <= 10 ? DANGER : PRIMARY }}
      >
        {formatMMSS(remaining)}
      </span>
      {running ? (
        <>
          <button
            onClick={() => {
              if (intervalRef.current) clearInterval(intervalRef.current);
              intervalRef.current = null;
              setRunning(false);
            }}
            className="p-0.5 rounded transition-colors"
            style={{ color: WARNING }}
          >
            <Pause size={11} />
          </button>
          <button onClick={stop} className="p-0.5 rounded transition-colors" style={{ color: DANGER }}>
            <Square size={9} />
          </button>
        </>
      ) : (
        <button
          onClick={() => setRunning(true)}
          className="p-0.5 rounded transition-colors"
          style={{ color: SUCCESS }}
        >
          <Play size={11} />
        </button>
      )}
    </div>
  );
};

const InlineWeightEdit: React.FC<{
  value: number;
  progression?: ExerciseProgression;
  onSave: (val: number) => void;
}> = ({ value, progression, onSave }) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value));
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing && inputRef.current) inputRef.current.focus();
  }, [editing]);

  const confirm = () => {
    const num = parseFloat(draft);
    if (!isNaN(num) && num > 0) onSave(num);
    setEditing(false);
  };

  const suggested = progression?.suggested_weight ?? null;
  const diff = suggested !== null ? suggested - value : 0;
  const showArrow = diff !== 0;

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="number"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={confirm}
        onKeyDown={(e) => {
          if (e.key === 'Enter') confirm();
          if (e.key === 'Escape') setEditing(false);
        }}
        className="w-14 px-1 py-0.5 rounded text-xs font-mono text-right outline-none"
        style={{ background: SURFACE, color: TEXT, border: `1px solid ${PRIMARY}` }}
      />
    );
  }

  return (
    <div
      className="relative flex items-center gap-1 cursor-pointer group"
      onClick={() => {
        setDraft(String(value));
        setEditing(true);
      }}
      title={progression?.progression_note || undefined}
    >
      <span className="text-xs font-mono" style={{ color: TEXT }}>
        {value}
      </span>
      {showArrow && (
        <span style={{ color: diff > 0 ? SUCCESS : DANGER }}>
          {diff > 0 ? <ArrowUp size={10} /> : <ArrowDown size={10} />}
        </span>
      )}
      {progression?.pr_potential && (
        <span
          className="px-1 py-0 rounded text-[8px] font-black tracking-wider"
          style={{ background: PRIMARY, color: ON_PRIMARY }}
        >
          PR
        </span>
      )}
      <span
        className="opacity-0 group-hover:opacity-100 transition-opacity text-[9px] ml-0.5"
        style={{ color: TEXT_MUTED }}
      >
        ✏️
      </span>
    </div>
  );
};

const StrengthContent: React.FC<{
  exercises: PlanSessionExercise[];
  progressions: ExerciseProgression[];
  progressionsLoading: boolean;
  onWeightChange: (idx: number, newWeight: number) => void;
}> = ({ exercises, progressions, progressionsLoading, onWeightChange }) => {
  const getProgression = (name: string): ExerciseProgression | undefined =>
    progressions.find((p) => p.exercise_name === name);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs" style={{ borderCollapse: 'separate', borderSpacing: 0 }}>
        <thead>
          <tr style={{ color: TEXT_MUTED }}>
            <th className="pb-2 pr-2 font-medium">Ejercicio</th>
            <th className="pb-2 pr-2 font-medium text-center">Series</th>
            <th className="pb-2 pr-2 font-medium text-center">Reps</th>
            <th className="pb-2 pr-2 font-medium text-center">Peso (kg)</th>
            <th className="pb-2 pr-2 font-medium text-center">Descanso</th>
            <th className="pb-2 font-medium text-center">Grupo</th>
          </tr>
        </thead>
        <tbody>
          {exercises.map((ex, i) => {
            const prog = getProgression(ex.name);
            return (
              <tr
                key={i}
                className="border-t"
                style={{ borderColor: `${TEXT_MUTED}15` }}
              >
                <td className="py-2.5 pr-2">
                  <span style={{ color: TEXT }} className="font-medium">
                    {ex.name}
                  </span>
                  {prog?.pr_potential && (
                    <span
                      className="ml-1.5 inline-flex items-center gap-0.5 px-1 py-0 rounded text-[8px] font-black tracking-wider"
                      style={{ background: PRIMARY, color: ON_PRIMARY }}
                    >
                      <Trophy size={8} /> PR
                    </span>
                  )}
                </td>
                <td className="py-2.5 pr-2 text-center font-mono" style={{ color: TEXT }}>
                  {ex.sets}
                </td>
                <td className="py-2.5 pr-2 text-center font-mono" style={{ color: TEXT }}>
                  {ex.reps}
                </td>
                <td className="py-2.5 pr-2 text-center">
                  {progressionsLoading ? (
                    <span className="text-[10px]" style={{ color: TEXT_MUTED }}>...</span>
                  ) : (
                    <InlineWeightEdit
                      value={ex.weight_kg}
                      progression={prog}
                      onSave={(val) => onWeightChange(i, val)}
                    />
                  )}
                </td>
                <td className="py-2.5 pr-2">
                  <div className="flex flex-col items-center gap-1">
                    <span className="text-[10px] font-mono" style={{ color: TEXT_MUTED }}>
                      {ex.rest_seconds}s
                    </span>
                    <RestTimer restSeconds={ex.rest_seconds} />
                  </div>
                </td>
                <td className="py-2.5 text-center">
                  <span
                    className="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium"
                    style={{ background: `${PRIMARY}15`, color: PRIMARY }}
                  >
                    {ex.muscle_group}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

const RunningContent: React.FC<{
  session: AdaptivePlanSession;
}> = ({ session }) => {
  const rd = session.running_details;
  if (!rd) return null;

  const zones = parseHRZone(rd.heart_rate_zone);
  const segments = parseStructure(rd.structure);

  return (
    <div className="space-y-5">
      <div
        className="rounded-xl p-4 space-y-3"
        style={{ background: SURFACE, border: `1px solid ${TEXT_MUTED}15` }}
      >
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-wider font-medium" style={{ color: TEXT_MUTED }}>
              Tipo
            </div>
            <div className="text-sm font-semibold mt-0.5" style={{ color: TEXT }}>
              {rd.type}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider font-medium" style={{ color: TEXT_MUTED }}>
              Distancia
            </div>
            <div className="text-sm font-semibold mt-0.5" style={{ color: TEXT }}>
              {rd.distance_km} km
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider font-medium" style={{ color: TEXT_MUTED }}>
              Ritmo objetivo
            </div>
            <div className="text-sm font-semibold mt-0.5" style={{ color: TEXT }}>
              {rd.target_pace_min_km} min/km
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider font-medium" style={{ color: TEXT_MUTED }}>
              Zona FC
            </div>
            <div className="text-lg font-bold mt-0.5" style={{ color: zones[0]?.color || PRIMARY }}>
              {rd.heart_rate_zone}
            </div>
          </div>
        </div>
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-wider font-medium mb-2" style={{ color: TEXT_MUTED }}>
          Zonas de FC
        </div>
        <div className="flex gap-1.5">
          {zones.map((z) => (
            <div
              key={z.label}
              className="flex-1 rounded-lg py-2 text-center font-bold text-sm"
              style={{ background: `${z.color}20`, color: z.color, border: `1px solid ${z.color}40` }}
            >
              {z.label}
            </div>
          ))}
        </div>
      </div>

      {segments.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider font-medium mb-2" style={{ color: TEXT_MUTED }}>
            Estructura
          </div>
          <div className="flex items-center gap-1 flex-wrap">
            {segments.map((seg, i) => (
              <React.Fragment key={i}>
                <span
                  className="px-3 py-1.5 rounded-lg text-xs font-medium"
                  style={{ background: SURFACE_HIGH, color: TEXT, border: `1px solid ${TEXT_MUTED}20` }}
                >
                  {seg}
                </span>
                {i < segments.length - 1 && (
                  <ChevronRight size={12} style={{ color: TEXT_MUTED }} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const MobilityContent: React.FC<{
  session: AdaptivePlanSession;
}> = ({ session }) => {
  const md = session.mobility_details;
  if (!md) return null;

  const focusIcon = MOBILITY_FOCUS_ICONS[md.focus] || '🧘';

  return (
    <div className="space-y-5">
      <div
        className="flex items-center gap-3 rounded-xl p-4"
        style={{ background: SURFACE, border: `1px solid ${TEXT_MUTED}15` }}
      >
        <span className="text-3xl">{focusIcon}</span>
        <div>
          <div className="text-[10px] uppercase tracking-wider font-medium" style={{ color: TEXT_MUTED }}>
            Zona de enfoque
          </div>
          <div className="text-sm font-semibold mt-0.5" style={{ color: TEXT }}>
            {md.focus.replace('_', ' ')}
          </div>
        </div>
      </div>

      {md.techniques.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider font-medium mb-2" style={{ color: TEXT_MUTED }}>
            Técnicas
          </div>
          <div className="flex flex-wrap gap-2">
            {md.techniques.map((t, i) => (
              <span
                key={i}
                className="px-3 py-1.5 rounded-full text-xs font-medium"
                style={{ background: `${PRIMARY}15`, color: PRIMARY, border: `1px solid ${PRIMARY}30` }}
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {md.key_exercises.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider font-medium mb-2" style={{ color: TEXT_MUTED }}>
            Ejercicios clave
          </div>
          <ol className="space-y-1.5">
            {md.key_exercises.map((ex, i) => (
              <li key={i} className="flex items-start gap-2">
                <span
                  className="flex-shrink-0 w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold"
                  style={{ background: PRIMARY, color: ON_PRIMARY }}
                >
                  {i + 1}
                </span>
                <span className="text-sm" style={{ color: TEXT }}>
                  {ex}
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
};

const RestContent: React.FC<{ readiness?: number | null }> = ({ readiness }) => {
  const tips = [
    { icon: <Droplets size={14} />, text: 'Mantén hidratación' },
    { icon: <BedDouble size={14} />, text: 'Sueño de 7+ horas' },
    { icon: <span className="text-sm">🧘</span>, text: 'Movilidad suave opcional' },
  ];

  const hasMetrics = readiness !== null && readiness !== undefined;

  return (
    <div className="space-y-5">
      <div
        className="rounded-xl p-5 text-center"
        style={{ background: SURFACE, border: `1px solid ${TEXT_MUTED}15` }}
      >
        <span className="text-4xl block mb-3">😴</span>
        <p className="text-sm font-medium" style={{ color: TEXT }}>
          Día de descanso — tu cuerpo se recupera
        </p>
      </div>

      {hasMetrics && (
        <div
          className="rounded-xl p-3 flex items-center justify-between"
          style={{ background: SURFACE, border: `1px solid ${TEXT_MUTED}15` }}
        >
          <span className="text-xs font-medium" style={{ color: TEXT_MUTED }}>
            Readiness hoy
          </span>
          <span
            className="text-lg font-black font-mono"
            style={{ color: readiness >= 65 ? SUCCESS : readiness >= 50 ? WARNING : DANGER }}
          >
            {readiness}
          </span>
        </div>
      )}

      <div className="space-y-2">
        <div className="text-[10px] uppercase tracking-wider font-medium" style={{ color: TEXT_MUTED }}>
          Consejos de descanso
        </div>
        {tips.map((tip, i) => (
          <div
            key={i}
            className="flex items-center gap-2.5 px-3 py-2 rounded-lg"
            style={{ background: SURFACE, border: `1px solid ${TEXT_MUTED}10` }}
          >
            <span style={{ color: PRIMARY }}>{tip.icon}</span>
            <span className="text-xs" style={{ color: TEXT }}>
              {tip.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

const SessionDetailPanel: React.FC<SessionDetailPanelProps> = ({
  session,
  onClose,
  onComplete,
  onAdapt,
  progressions,
  progressionsLoading,
  readiness,
}) => {
  const [showAdaptInput, setShowAdaptInput] = useState(false);
  const [adaptText, setAdaptText] = useState('');
  const [localWeights, setLocalWeights] = useState<Record<number, number>>({});

  useEffect(() => {
    setLocalWeights({});
    setShowAdaptInput(false);
    setAdaptText('');
  }, [session?.id]);

  const handleWeightChange = (idx: number, newWeight: number) => {
    setLocalWeights((prev) => ({ ...prev, [idx]: newWeight }));
  };

  const getExerciseWeight = (ex: PlanSessionExercise, idx: number): number => {
    return localWeights[idx] ?? ex.weight_kg;
  };

  const handleAdapt = () => {
    if (!session || !adaptText.trim()) return;
    onAdapt(session.id, adaptText.trim());
    setAdaptText('');
    setShowAdaptInput(false);
  };

  const isHighIntensity =
    session?.session_type === 'strength' ||
    session?.session_type === 'hiit' ||
    session?.session_type === 'running' ||
    session?.session_type === 'trail_running';

  const showReadinessWarning =
    isHighIntensity && readiness !== null && readiness !== undefined && readiness < 55;

  if (!session) return null;

  const exercises = session.exercises ?? [];
  const exercisesWithLocalWeights = exercises.map((ex, i) => ({
    ...ex,
    weight_kg: getExerciseWeight(ex, i),
  }));

  const sessionType = session.session_type;

  const renderContent = () => {
    if (sessionType === 'strength' || sessionType === 'hiit') {
      return (
        <StrengthContent
          exercises={exercisesWithLocalWeights}
          progressions={progressions}
          progressionsLoading={progressionsLoading}
          onWeightChange={handleWeightChange}
        />
      );
    }
    if (sessionType === 'running' || sessionType === 'trail_running') {
      return <RunningContent session={session} />;
    }
    if (sessionType === 'mobility' || sessionType === 'active_recovery') {
      return <MobilityContent session={session} />;
    }
    if (sessionType === 'rest') {
      return <RestContent readiness={readiness} />;
    }
    return null;
  };

  const formattedDate = new Date(session.date + 'T00:00:00').toLocaleDateString('es-ES', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  });

  return (
    <AnimatePresence>
      {session && (
        <>
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
            onClick={onClose}
          />

          <motion.div
            key="panel"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed top-0 right-0 z-50 h-full flex flex-col
              w-full max-w-[400px]
              max-md:top-auto max-md:bottom-0 max-md:left-0 max-md:right-0 max-md:max-w-full
              max-md:h-[92vh] max-md:rounded-t-2xl max-md:rounded-b-none
              rounded-l-2xl overflow-hidden"
            style={{ background: BG }}
          >
            {/* Header */}
            <div
              className="flex-shrink-0 px-4 pt-4 pb-3 border-b"
              style={{ borderColor: `${TEXT_MUTED}20` }}
            >
              <div className="flex items-start justify-between mb-3">
                <button
                  onClick={onClose}
                  className="p-1 rounded-lg transition-colors hover:opacity-80"
                  style={{ background: SURFACE_HIGH, color: TEXT_MUTED }}
                >
                  <X size={16} />
                </button>
                <div className="flex items-center gap-2 flex-wrap justify-end">
                  {session.adaptation_reason && (
                    <div className="group relative">
                      <span
                        className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide"
                        style={{ background: `${WARNING}20`, color: WARNING }}
                      >
                        Adaptado
                      </span>
                      <div
                        className="absolute right-0 top-full mt-1 w-56 px-3 py-2 rounded-lg text-[10px] z-50 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
                        style={{ background: SURFACE_HIGH, color: TEXT, border: `1px solid ${WARNING}40` }}
                      >
                        {session.adaptation_reason}
                      </div>
                    </div>
                  )}
                  <button
                    onClick={() => onComplete(session.id, !session.completed)}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold tracking-wide transition-colors"
                    style={{
                      background: session.completed ? `${SUCCESS}20` : SURFACE_HIGH,
                      color: session.completed ? SUCCESS : TEXT_MUTED,
                      border: `1px solid ${session.completed ? `${SUCCESS}40` : `${TEXT_MUTED}20`}`,
                    }}
                  >
                    {session.completed ? (
                      <>
                        <span className="w-2 h-2 rounded-full" style={{ background: SUCCESS }} />
                        Completada
                      </>
                    ) : (
                      <>
                        <span
                          className="w-2 h-2 rounded-full border"
                          style={{ borderColor: TEXT_MUTED }}
                        />
                        Pendiente
                      </>
                    )}
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-2.5 mb-1">
                <span style={{ color: PRIMARY }}>
                  {SESSION_TYPE_ICONS[session.session_type] ?? <Dumbbell size={18} />}
                </span>
                <h2
                  className="text-base font-bold leading-tight"
                  style={{ color: TEXT, fontFamily: "'Orbitron', sans-serif" }}
                >
                  {session.title}
                </h2>
              </div>

              <div className="flex items-center gap-3 text-[11px]" style={{ color: TEXT_MUTED }}>
                <span>
                  {session.day_of_week} · {formattedDate}
                </span>
                {session.duration_minutes && (
                  <span className="flex items-center gap-1">
                    <Timer size={10} />
                    {session.duration_minutes} min
                  </span>
                )}
                {session.intensity && (
                  <span
                    className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider"
                    style={{
                      background: `${INTENSITY_COLORS[session.intensity]}20`,
                      color: INTENSITY_COLORS[session.intensity],
                    }}
                  >
                    {INTENSITY_LABELS[session.intensity]}
                  </span>
                )}
              </div>
            </div>

            {/* Readiness warning */}
            {showReadinessWarning && (
              <div
                className="flex-shrink-0 mx-4 mt-3 px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-2"
                style={{
                  background: `${DANGER}12`,
                  color: DANGER,
                  border: `1px solid ${DANGER}30`,
                }}
              >
                ⚠️ Readiness bajo ({readiness}/100). Considera reducir la intensidad o cambiar a
                recuperación activa.
              </div>
            )}

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-4 py-4" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              {session.description && (
                <p className="text-xs mb-4 leading-relaxed" style={{ color: TEXT_MUTED }}>
                  {session.description}
                </p>
              )}
              {renderContent()}
            </div>

            {/* Footer */}
            <div
              className="flex-shrink-0 px-4 py-3 border-t space-y-2"
              style={{ borderColor: `${TEXT_MUTED}20`, background: SURFACE }}
            >
              {showAdaptInput ? (
                <div className="space-y-2">
                  <textarea
                    value={adaptText}
                    onChange={(e) => setAdaptText(e.target.value)}
                    placeholder="Describe qué quieres adaptar..."
                    rows={2}
                    className="w-full px-3 py-2 rounded-lg text-xs resize-none outline-none"
                    style={{
                      background: SURFACE_HIGH,
                      color: TEXT,
                      border: `1px solid ${PRIMARY}40`,
                      fontFamily: "'DM Sans', sans-serif",
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleAdapt();
                      }
                    }}
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={handleAdapt}
                      disabled={!adaptText.trim()}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-bold transition-colors disabled:opacity-40"
                      style={{ background: PRIMARY, color: ON_PRIMARY }}
                    >
                      <Send size={12} />
                      Enviar
                    </button>
                    <button
                      onClick={() => {
                        setShowAdaptInput(false);
                        setAdaptText('');
                      }}
                      className="px-3 py-2 rounded-lg text-xs font-medium transition-colors"
                      style={{ background: SURFACE_HIGH, color: TEXT_MUTED }}
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowAdaptInput(true)}
                    className="flex-1 py-2 rounded-lg text-xs font-bold transition-colors"
                    style={{ background: SURFACE_HIGH, color: TEXT, border: `1px solid ${TEXT_MUTED}20` }}
                  >
                    Adaptar Sesión
                  </button>
                  <button
                    onClick={() => onComplete(session.id, !session.completed)}
                    className="flex-1 py-2 rounded-lg text-xs font-bold transition-colors"
                    style={{
                      background: session.completed ? `${DANGER}20` : `${SUCCESS}20`,
                      color: session.completed ? DANGER : SUCCESS,
                      border: `1px solid ${session.completed ? `${DANGER}30` : `${SUCCESS}30`}`,
                    }}
                  >
                    {session.completed ? 'Desmarcar' : 'Marcar Completada'}
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default SessionDetailPanel;
