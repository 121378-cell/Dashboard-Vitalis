import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { CreateMasterPlanRequest } from '../../types';

interface MasterPlanWizardProps {
  onCreate: (request: CreateMasterPlanRequest) => Promise<void>;
  creating: boolean;
}

const DAYS = [
  { key: 'monday', label: 'Lun' },
  { key: 'tuesday', label: 'Mar' },
  { key: 'wednesday', label: 'Mié' },
  { key: 'thursday', label: 'Jue' },
  { key: 'friday', label: 'Vie' },
  { key: 'saturday', label: 'Sáb' },
  { key: 'sunday', label: 'Dom' },
] as const;

const GOAL_PRESETS = [
  'Proyecto 31/07: Bench Press 52.5kg + Leg Press 100kg',
  'Preparar competición de fuerza',
  'Volumen muscular con periodización',
  'Mejorar resistencia cardiovascular',
  'Rehabilitación y vuelta gradual',
  'Rendimiento general atlético',
];

const INTENSITY_OPTIONS = [
  { value: 'low', label: 'Suave', emoji: '🟢' },
  { value: 'medium', label: 'Moderada', emoji: '🟡' },
  { value: 'high', label: 'Intensa', emoji: '🔴' },
  { value: 'atlas_decides', label: 'ATLAS decide', emoji: '🤖' },
] as const;

const STEPS = ['Objetivo', 'Calendario', 'Configuración', 'Confirmar'];

const slideVariants = {
  enter: (direction: number) => ({ x: direction > 0 ? 300 : -300, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (direction: number) => ({ x: direction < 0 ? 300 : -300, opacity: 0 }),
};

const slideTransition = { type: 'spring' as const, stiffness: 300, damping: 30 };

const MasterPlanWizard: React.FC<MasterPlanWizardProps> = ({ onCreate, creating }) => {
  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState(1);
  const [goal, setGoal] = useState('');
  const [targetDate, setTargetDate] = useState('');
  const [noDeadline, setNoDeadline] = useState(false);
  const [preferredDays, setPreferredDays] = useState<string[]>([]);
  const [timePerSession, setTimePerSession] = useState(60);
  const [intensity, setIntensity] = useState('atlas_decides');
  const [restrictions, setRestrictions] = useState('');
  const [validationError, setValidationError] = useState('');

  const goTo = useCallback((next: number) => {
    setDirection(next > step ? 1 : -1);
    setStep(next);
    setValidationError('');
  }, [step]);

  const validateStep = useCallback((): boolean => {
    if (step === 0 && goal.trim().length === 0) {
      setValidationError('Define tu objetivo');
      return false;
    }
    if (step === 0 && !noDeadline && !targetDate) {
      setValidationError('Indica una fecha límite o selecciona "Sin fecha límite"');
      return false;
    }
    if (step === 1 && preferredDays.length === 0) {
      setValidationError('Selecciona al menos 2 días de entrenamiento');
      return false;
    }
    return true;
  }, [step, goal, noDeadline, targetDate, preferredDays]);

  const handleNext = useCallback(() => {
    if (!validateStep()) return;
    goTo(step + 1);
  }, [validateStep, goTo, step]);

  const handleBack = useCallback(() => goTo(step - 1), [goTo, step]);

  const toggleDay = useCallback((dayKey: string) => {
    setPreferredDays(prev =>
      prev.includes(dayKey) ? prev.filter(d => d !== dayKey) : [...prev, dayKey]
    );
  }, []);

  const handleCreate = useCallback(async () => {
    await onCreate({
      goal: goal.trim(),
      target_date: noDeadline ? null : targetDate,
      preferred_days: preferredDays,
      time_per_session_minutes: timePerSession,
      intensity_preference: intensity,
      restrictions: restrictions.trim() || null,
    });
  }, [onCreate, goal, noDeadline, targetDate, preferredDays, timePerSession, intensity, restrictions]);

  const totalWeeks = (() => {
    if (noDeadline) return 8;
    if (!targetDate) return 8;
    const diff = Math.ceil(
      (new Date(targetDate).getTime() - new Date().getTime()) / (7 * 24 * 60 * 60 * 1000)
    );
    return Math.max(4, Math.min(52, diff));
  })();

  return (
    <div className="w-full max-w-lg mx-auto rounded-2xl overflow-hidden" style={{ background: '#13131A' }}>
      {/* Step Indicator */}
      <div className="px-6 pt-5 pb-3">
        <div className="flex items-center justify-between mb-2">
          {STEPS.map((label, i) => (
            <div key={label} className="flex items-center gap-1.5">
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-all duration-300"
                style={{
                  background: i <= step ? '#E8FF47' : '#1C1C26',
                  color: i <= step ? '#0A0A0F' : '#6B6B8A',
                }}
              >
                {i + 1}
              </div>
              <span
                className="text-[10px] font-medium hidden lg:inline transition-colors duration-300"
                style={{
                  color: i <= step ? '#F0F0FF' : '#6B6B8A',
                  fontFamily: "'DM Sans', sans-serif",
                }}
              >
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <div className="hidden lg:block w-4 h-px" style={{ background: i < step ? '#E8FF47' : '#1C1C26' }} />
              )}
            </div>
          ))}
        </div>
        <p className="text-xs text-right" style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}>
          Paso {step + 1}/{STEPS.length}
        </p>
      </div>

      {/* Step Content */}
      <div className="relative px-6 min-h-[340px]">
        <AnimatePresence initial={false} custom={direction} mode="wait">
          {step === 0 && (
            <motion.div key="step-0" custom={direction} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={slideTransition}>
              <h3 className="text-lg font-bold mb-4" style={{ color: '#F0F0FF', fontFamily: "'Orbitron', sans-serif" }}>
                Objetivo del Plan Maestro
              </h3>
              <textarea
                value={goal}
                onChange={e => { setGoal(e.target.value); if (validationError) setValidationError(''); }}
                placeholder="Describe tu objetivo a largo plazo..."
                rows={3}
                className="w-full rounded-xl px-4 py-3 text-sm outline-none resize-none transition-all duration-200 focus:ring-2"
                style={{
                  background: '#1C1C26',
                  color: '#F0F0FF',
                  border: validationError && step === 0 && !goal.trim() ? '1px solid #EF4444' : '1px solid transparent',
                  fontFamily: "'DM Sans', sans-serif",
                }}
                onFocus={e => (e.target.style.boxShadow = '0 0 0 2px rgba(232,255,71,0.3)')}
                onBlur={e => (e.target.style.boxShadow = 'none')}
              />
              <p className="mt-2 mb-2 text-xs" style={{ color: '#6B6B8A' }}>O elige un preset:</p>
              <div className="flex flex-wrap gap-2">
                {GOAL_PRESETS.map(preset => (
                  <button
                    key={preset}
                    onClick={() => { setGoal(preset); if (validationError) setValidationError(''); }}
                    className="px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 hover:scale-105"
                    style={{
                      background: goal === preset ? '#E8FF47' : '#1C1C26',
                      color: goal === preset ? '#0A0A0F' : '#F0F0FF',
                      border: `1px solid ${goal === preset ? '#E8FF47' : '#2A2A3A'}`,
                      fontFamily: "'DM Sans', sans-serif",
                    }}
                  >
                    {preset.length > 35 ? preset.slice(0, 35) + '...' : preset}
                  </button>
                ))}
              </div>

              {/* Target date */}
              <div className="mt-5">
                <p className="text-xs mb-2" style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}>Fecha límite</p>
                <div className="flex items-center gap-3 mb-2">
                  <input
                    type="date"
                    value={targetDate}
                    onChange={e => { setTargetDate(e.target.value); setNoDeadline(false); }}
                    disabled={noDeadline}
                    className="rounded-lg px-3 py-2 text-sm outline-none"
                    style={{
                      background: noDeadline ? '#0D0D14' : '#1C1C26',
                      color: noDeadline ? '#6B6B8A' : '#F0F0FF',
                      border: validationError && !noDeadline && !targetDate ? '1px solid #EF4444' : '1px solid #2A2A3A',
                      fontFamily: "'DM Sans', sans-serif",
                    }}
                  />
                </div>
                <button
                  onClick={() => { setNoDeadline(prev => !prev); if (validationError) setValidationError(''); }}
                  className="flex items-center gap-2 text-xs transition-colors"
                  style={{ color: noDeadline ? '#E8FF47' : '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}
                >
                  <div
                    className="w-4 h-4 rounded border flex items-center justify-center"
                    style={{ background: noDeadline ? '#E8FF47' : 'transparent', borderColor: noDeadline ? '#E8FF47' : '#6B6B8A' }}
                  >
                    {noDeadline && <span style={{ color: '#0A0A0F', fontSize: '10px', fontWeight: 700 }}>&#10003;</span>}
                  </div>
                  Sin fecha límite (8 semanas renovables)
                </button>
              </div>
            </motion.div>
          )}

          {step === 1 && (
            <motion.div key="step-1" custom={direction} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={slideTransition}>
              <h3 className="text-lg font-bold mb-4" style={{ color: '#F0F0FF', fontFamily: "'Orbitron', sans-serif" }}>
                Días y Horario
              </h3>
              <p className="text-xs mb-2" style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}>
                Días de entrenamiento
              </p>
              <div className="flex flex-wrap gap-2 mb-5">
                {DAYS.map(day => {
                  const active = preferredDays.includes(day.key);
                  return (
                    <button
                      key={day.key}
                      onClick={() => toggleDay(day.key)}
                      className="px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200"
                      style={{
                        background: active ? '#E8FF47' : '#1C1C26',
                        color: active ? '#0A0A0F' : '#F0F0FF',
                        border: `1px solid ${active ? '#E8FF47' : validationError && preferredDays.length === 0 ? '#EF4444' : '#2A2A3A'}`,
                        fontFamily: "'DM Sans', sans-serif",
                      }}
                    >
                      {day.label}
                    </button>
                  );
                })}
              </div>

              <p className="text-xs mb-2" style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}>
                Minutos por sesión
              </p>
              <div className="flex items-center gap-3 mb-1">
                <input
                  type="range"
                  min={30}
                  max={120}
                  step={15}
                  value={timePerSession}
                  onChange={e => setTimePerSession(Number(e.target.value))}
                  className="flex-1 h-1.5 rounded-full appearance-none cursor-pointer"
                  style={{
                    background: `linear-gradient(to right, #E8FF47 ${((timePerSession - 30) / 90) * 100}%, #1C1C26 ${((timePerSession - 30) / 90) * 100}%)`,
                  }}
                />
                <span className="text-xs font-bold w-10 text-right" style={{ color: '#E8FF47', fontFamily: "'Orbitron', sans-serif" }}>
                  {timePerSession}m
                </span>
              </div>
              <p className="text-[10px] mt-1" style={{ color: '#6B6B8A' }}>
                {preferredDays.length > 0
                  ? `${preferredDays.length} días × ${timePerSession}min = ${preferredDays.length * timePerSession}min/semana`
                  : 'Selecciona días para ver volumen semanal'}
              </p>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div key="step-2" custom={direction} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={slideTransition}>
              <h3 className="text-lg font-bold mb-4" style={{ color: '#F0F0FF', fontFamily: "'Orbitron', sans-serif" }}>
                Configuración
              </h3>
              <p className="text-xs mb-2" style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}>
                Intensidad preferida
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-5">
                {INTENSITY_OPTIONS.map(opt => {
                  const active = intensity === opt.value;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => setIntensity(opt.value)}
                      className="flex flex-col items-center gap-1 py-3 rounded-xl transition-all duration-200 hover:scale-105"
                      style={{
                        background: active ? 'rgba(232,255,71,0.12)' : '#1C1C26',
                        border: `2px solid ${active ? '#E8FF47' : '#2A2A3A'}`,
                      }}
                    >
                      <span className="text-lg">{opt.emoji}</span>
                      <span className="text-[10px] font-semibold" style={{ color: active ? '#E8FF47' : '#F0F0FF', fontFamily: "'DM Sans', sans-serif" }}>
                        {opt.label}
                      </span>
                    </button>
                  );
                })}
              </div>

              <p className="text-xs mb-2" style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}>
                Restricciones (opcional)
              </p>
              <textarea
                value={restrictions}
                onChange={e => setRestrictions(e.target.value)}
                placeholder="Lesiones, zonas a evitar, consideraciones médicas..."
                rows={3}
                className="w-full rounded-xl px-4 py-3 text-sm outline-none resize-none transition-all duration-200 focus:ring-2"
                style={{
                  background: '#1C1C26',
                  color: '#F0F0FF',
                  border: '1px solid transparent',
                  fontFamily: "'DM Sans', sans-serif",
                }}
                onFocus={e => (e.target.style.boxShadow = '0 0 0 2px rgba(232,255,71,0.3)')}
                onBlur={e => (e.target.style.boxShadow = 'none')}
              />
            </motion.div>
          )}

          {step === 3 && (
            <motion.div key="step-3" custom={direction} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={slideTransition}>
              <h3 className="text-lg font-bold mb-4" style={{ color: '#F0F0FF', fontFamily: "'Orbitron', sans-serif" }}>
                Confirmar Plan Maestro
              </h3>
              <div className="space-y-3">
                <div className="p-3 rounded-xl" style={{ background: '#1C1C26' }}>
                  <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: '#6B6B8A' }}>Objetivo</p>
                  <p className="text-sm font-medium" style={{ color: '#F0F0FF', fontFamily: "'DM Sans', sans-serif" }}>{goal}</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl" style={{ background: '#1C1C26' }}>
                    <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: '#6B6B8A' }}>Fecha límite</p>
                    <p className="text-sm font-bold" style={{ color: '#E8FF47', fontFamily: "'Orbitron', sans-serif" }}>
                      {noDeadline ? '8 sem renovables' : targetDate}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl" style={{ background: '#1C1C26' }}>
                    <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: '#6B6B8A' }}>Duración</p>
                    <p className="text-sm font-bold" style={{ color: '#E8FF47', fontFamily: "'Orbitron', sans-serif" }}>
                      {totalWeeks} semanas
                    </p>
                  </div>
                  <div className="p-3 rounded-xl" style={{ background: '#1C1C26' }}>
                    <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: '#6B6B8A' }}>Días</p>
                    <p className="text-sm font-medium" style={{ color: '#F0F0FF', fontFamily: "'DM Sans', sans-serif" }}>
                      {preferredDays.map(d => DAYS.find(dd => dd.key === d)?.label).join(', ')}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl" style={{ background: '#1C1C26' }}>
                    <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: '#6B6B8A' }}>Intensidad</p>
                    <p className="text-sm font-medium" style={{ color: '#F0F0FF', fontFamily: "'DM Sans', sans-serif" }}>
                      {INTENSITY_OPTIONS.find(o => o.value === intensity)?.label ?? intensity}
                    </p>
                  </div>
                </div>
                {restrictions && (
                  <div className="p-3 rounded-xl" style={{ background: '#1C1C26' }}>
                    <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: '#6B6B8A' }}>Restricciones</p>
                    <p className="text-sm" style={{ color: '#F0F0FF', fontFamily: "'DM Sans', sans-serif" }}>{restrictions}</p>
                  </div>
                )}
                <div className="p-3 rounded-xl" style={{ background: 'rgba(232,255,71,0.06)', border: '1px solid rgba(232,255,71,0.15)' }}>
                  <p className="text-xs" style={{ color: '#E8FF47', fontFamily: "'DM Sans', sans-serif" }}>
                    ATLAS generará un plan periodizado con fases (Base → Desarrollo → Peak → Taper).
                    Deberás confirmar cada semana antes de que se active.
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Validation error */}
      <AnimatePresence>
        {validationError && (
          <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="px-6">
            <p className="text-xs font-medium py-2" style={{ color: '#EF4444', fontFamily: "'DM Sans', sans-serif" }}>
              {validationError}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Actions */}
      <div className="flex items-center justify-between px-6 py-4 mt-2 gap-3">
        {step > 0 ? (
          <button
            onClick={handleBack}
            className="px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 hover:opacity-80"
            style={{ background: '#1C1C26', color: '#F0F0FF', border: '1px solid #2A2A3A', fontFamily: "'DM Sans', sans-serif" }}
          >
            Atrás
          </button>
        ) : (
          <div />
        )}

        {step < 3 ? (
          <button
            onClick={handleNext}
            className="px-6 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 hover:scale-105"
            style={{ background: '#E8FF47', color: '#0A0A0F', fontFamily: "'DM Sans', sans-serif" }}
          >
            Siguiente
          </button>
        ) : (
          <button
            onClick={handleCreate}
            disabled={creating}
            className="px-6 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:hover:scale-100 flex items-center gap-2"
            style={{ background: '#E8FF47', color: '#0A0A0F', fontFamily: "'DM Sans', sans-serif" }}
          >
            {creating && (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" style={{ opacity: 0.3 }} />
                <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
              </svg>
            )}
            {creating ? 'Creando Plan Maestro...' : 'Crear Plan Maestro'}
          </button>
        )}
      </div>
    </div>
  );
};

export default MasterPlanWizard;
