import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { GeneratePlanRequest } from '../../types';

interface PlanWizardProps {
  onGenerate: (request: GeneratePlanRequest) => Promise<void>;
  generating: boolean;
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

const GOAL_CHIPS = [
  'Ganar fuerza',
  'Mejorar resistencia',
  'Recuperación activa',
  'Mantener nivel',
  'Preparar competición',
];

const SESSION_TYPE_OPTIONS = [
  { value: 'strength', label: 'Fuerza' },
  { value: 'running', label: 'Running' },
  { value: 'trail_running', label: 'Trail' },
  { value: 'mobility', label: 'Movilidad' },
  { value: 'hiit', label: 'HIIT' },
  { value: 'active_recovery', label: 'Rec. Activa' },
] as const;

const INTENSITY_OPTIONS = [
  { value: 'low', label: 'Suave', emoji: '🟢' },
  { value: 'medium', label: 'Moderada', emoji: '🟡' },
  { value: 'high', label: 'Intensa', emoji: '🔴' },
] as const;

const STEPS = ['Objetivo', 'Disponibilidad', 'Preferencias'];

const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 300 : -300,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction: number) => ({
    x: direction < 0 ? 300 : -300,
    opacity: 0,
  }),
};

const slideTransition = {
  type: 'spring' as const,
  stiffness: 300,
  damping: 30,
};

const PlanWizard: React.FC<PlanWizardProps> = ({ onGenerate, generating }) => {
  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState(1);
  const [goal, setGoal] = useState('');
  const [trainingDays, setTrainingDays] = useState<string[]>([]);
  const [timePerDay, setTimePerDay] = useState<Record<string, number>>({});
  const [sessionTypes, setSessionTypes] = useState<string[]>([]);
  const [intensity, setIntensity] = useState('medium');
  const [considerReadiness, setConsiderReadiness] = useState(true);
  const [restrictions, setRestrictions] = useState('');
  const [validationError, setValidationError] = useState('');

  const goTo = useCallback((next: number) => {
    setDirection(next > step ? 1 : -1);
    setStep(next);
    setValidationError('');
  }, [step]);

  const validateStep = useCallback((): boolean => {
    if (step === 0 && goal.trim().length === 0) {
      setValidationError('Define tu objetivo para la semana');
      return false;
    }
    if (step === 1 && trainingDays.length === 0) {
      setValidationError('Selecciona al menos un día de entrenamiento');
      return false;
    }
    return true;
  }, [step, goal, trainingDays]);

  const handleNext = useCallback(() => {
    if (!validateStep()) return;
    goTo(step + 1);
  }, [validateStep, goTo, step]);

  const handleBack = useCallback(() => {
    goTo(step - 1);
  }, [goTo, step]);

  const toggleDay = useCallback((dayKey: string) => {
    setTrainingDays(prev => {
      const next = prev.includes(dayKey)
        ? prev.filter(d => d !== dayKey)
        : [...prev, dayKey];
      if (!next.includes(dayKey)) {
        setTimePerDay(tp => {
          const copy = { ...tp };
          delete copy[dayKey];
          return copy;
        });
      } else if (!timePerDay[dayKey]) {
        setTimePerDay(tp => ({ ...tp, [dayKey]: 60 }));
      }
      return next;
    });
  }, [timePerDay]);

  const setTime = useCallback((dayKey: string, minutes: number) => {
    setTimePerDay(prev => ({ ...prev, [dayKey]: minutes }));
  }, []);

  const toggleSessionType = useCallback((type: string) => {
    setSessionTypes(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
    );
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!validateStep()) return;

    const timeAvailable: Record<string, number> = {};
    for (const day of trainingDays) {
      if (timePerDay[day]) {
        timeAvailable[day] = timePerDay[day];
      }
    }

    await onGenerate({
      goal: goal.trim(),
      training_days: trainingDays,
      time_available: timeAvailable,
      session_types: sessionTypes.length > 0 ? sessionTypes : undefined,
      intensity_preference: intensity,
      consider_readiness: considerReadiness,
      restrictions: restrictions.trim() || undefined,
    });
  }, [validateStep, onGenerate, goal, trainingDays, timePerDay, sessionTypes, intensity, considerReadiness, restrictions]);

  return (
    <div
      className="w-full max-w-lg mx-auto rounded-2xl overflow-hidden"
      style={{ background: '#13131A' }}
    >
      {/* Step Indicator */}
      <div className="px-6 pt-5 pb-3">
        <div className="flex items-center justify-between mb-2">
          {STEPS.map((label, i) => (
            <div key={label} className="flex items-center gap-2">
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
                className="text-xs font-medium hidden sm:inline transition-colors duration-300"
                style={{
                  color: i <= step ? '#F0F0FF' : '#6B6B8A',
                  fontFamily: "'DM Sans', sans-serif",
                }}
              >
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <div
                  className="hidden sm:block w-6 h-px mx-1"
                  style={{
                    background: i < step ? '#E8FF47' : '#1C1C26',
                  }}
                />
              )}
            </div>
          ))}
        </div>
        <p
          className="text-xs text-right"
          style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}
        >
          Paso {step + 1}/3
        </p>
      </div>

      {/* Step Content */}
      <div className="relative px-6 min-h-[320px]">
        <AnimatePresence initial={false} custom={direction} mode="wait">
          {step === 0 && (
            <motion.div
              key="step-0"
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={slideTransition}
            >
              <h3
                className="text-lg font-bold mb-4"
                style={{
                  color: '#F0F0FF',
                  fontFamily: "'Orbitron', sans-serif",
                }}
              >
                Objetivo de la semana
              </h3>
              <textarea
                value={goal}
                onChange={e => {
                  setGoal(e.target.value);
                  if (validationError) setValidationError('');
                }}
                placeholder="Describe tu objetivo para esta semana..."
                rows={3}
                className="w-full rounded-xl px-4 py-3 text-sm outline-none resize-none transition-all duration-200 focus:ring-2"
                style={{
                  background: '#1C1C26',
                  color: '#F0F0FF',
                  border: validationError && step === 0 ? '1px solid #EF4444' : '1px solid transparent',
                  fontFamily: "'DM Sans', sans-serif",
                }}
                onFocus={e => (e.target.style.boxShadow = '0 0 0 2px rgba(232,255,71,0.3)')}
                onBlur={e => (e.target.style.boxShadow = 'none')}
              />
              <p className="mt-2 mb-3 text-xs" style={{ color: '#6B6B8A' }}>
                O elige un objetivo rápido:
              </p>
              <div className="flex flex-wrap gap-2">
                {GOAL_CHIPS.map(chip => (
                  <button
                    key={chip}
                    onClick={() => {
                      setGoal(chip);
                      if (validationError) setValidationError('');
                    }}
                    className="px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 hover:scale-105"
                    style={{
                      background: goal === chip ? '#E8FF47' : '#1C1C26',
                      color: goal === chip ? '#0A0A0F' : '#F0F0FF',
                      border: `1px solid ${goal === chip ? '#E8FF47' : '#2A2A3A'}`,
                      fontFamily: "'DM Sans', sans-serif",
                    }}
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {step === 1 && (
            <motion.div
              key="step-1"
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={slideTransition}
            >
              <h3
                className="text-lg font-bold mb-4"
                style={{
                  color: '#F0F0FF',
                  fontFamily: "'Orbitron', sans-serif",
                }}
              >
                Disponibilidad
              </h3>

              {/* Day toggles */}
              <p className="text-xs mb-2" style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}>
                Días de entrenamiento
              </p>
              <div className="flex flex-wrap gap-2 mb-4">
                {DAYS.map(day => {
                  const active = trainingDays.includes(day.key);
                  return (
                    <button
                      key={day.key}
                      onClick={() => toggleDay(day.key)}
                      className="px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200"
                      style={{
                        background: active ? '#E8FF47' : '#1C1C26',
                        color: active ? '#0A0A0F' : '#F0F0FF',
                        border: `1px solid ${active ? '#E8FF47' : validationError && trainingDays.length === 0 ? '#EF4444' : '#2A2A3A'}`,
                        fontFamily: "'DM Sans', sans-serif",
                      }}
                    >
                      {day.label}
                    </button>
                  );
                })}
              </div>

              {/* Time per day */}
              <AnimatePresence>
                {trainingDays.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <p className="text-xs mb-2" style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}>
                      Minutos por sesión
                    </p>
                    <div className="space-y-3 mb-4">
                      {trainingDays.sort().map(dayKey => {
                        const dayData = DAYS.find(d => d.key === dayKey);
                        const minutes = timePerDay[dayKey] ?? 60;
                        return (
                          <div key={dayKey} className="flex items-center gap-3">
                            <span
                              className="text-xs font-medium w-8 shrink-0"
                              style={{ color: '#F0F0FF', fontFamily: "'DM Sans', sans-serif" }}
                            >
                              {dayData?.label}
                            </span>
                            <input
                              type="range"
                              min={30}
                              max={120}
                              step={15}
                              value={minutes}
                              onChange={e => setTime(dayKey, Number(e.target.value))}
                              className="flex-1 h-1.5 rounded-full appearance-none cursor-pointer"
                              style={{
                                background: `linear-gradient(to right, #E8FF47 ${((minutes - 30) / 90) * 100}%, #1C1C26 ${((minutes - 30) / 90) * 100}%)`,
                              }}
                            />
                            <span
                              className="text-xs font-bold w-10 text-right shrink-0"
                              style={{ color: '#E8FF47', fontFamily: "'Orbitron', sans-serif" }}
                            >
                              {minutes}m
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Session types */}
              <p className="text-xs mb-2" style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}>
                Tipos de sesión (opcional)
              </p>
              <div className="flex flex-wrap gap-2">
                {SESSION_TYPE_OPTIONS.map(opt => {
                  const active = sessionTypes.includes(opt.value);
                  return (
                    <button
                      key={opt.value}
                      onClick={() => toggleSessionType(opt.value)}
                      className="px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 hover:scale-105"
                      style={{
                        background: active ? 'rgba(232,255,71,0.15)' : '#1C1C26',
                        color: active ? '#E8FF47' : '#F0F0FF',
                        border: `1px solid ${active ? '#E8FF47' : '#2A2A3A'}`,
                        fontFamily: "'DM Sans', sans-serif",
                      }}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div
              key="step-2"
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={slideTransition}
            >
              <h3
                className="text-lg font-bold mb-4"
                style={{
                  color: '#F0F0FF',
                  fontFamily: "'Orbitron', sans-serif",
                }}
              >
                Preferencias
              </h3>

              {/* Intensity */}
              <p className="text-xs mb-2" style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}>
                Intensidad preferida
              </p>
              <div className="grid grid-cols-3 gap-3 mb-5">
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
                        fontFamily: "'DM Sans', sans-serif",
                      }}
                    >
                      <span className="text-lg">{opt.emoji}</span>
                      <span
                        className="text-xs font-semibold"
                        style={{
                          color: active ? '#E8FF47' : '#F0F0FF',
                        }}
                      >
                        {opt.label}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* Consider readiness toggle */}
              <div className="flex items-center justify-between py-3 px-4 rounded-xl mb-5" style={{ background: '#1C1C26' }}>
                <div>
                  <p
                    className="text-sm font-medium"
                    style={{ color: '#F0F0FF', fontFamily: "'DM Sans', sans-serif" }}
                  >
                    Considerar readiness
                  </p>
                  <p
                    className="text-xs mt-0.5"
                    style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}
                  >
                    Adaptar plan según tu estado de recuperación
                  </p>
                </div>
                <button
                  onClick={() => setConsiderReadiness(prev => !prev)}
                  className="relative w-11 h-6 rounded-full transition-colors duration-300 shrink-0 ml-3"
                  style={{ background: considerReadiness ? '#E8FF47' : '#2A2A3A' }}
                  aria-label="Toggle consider readiness"
                >
                  <motion.div
                    className="absolute top-0.5 w-5 h-5 rounded-full"
                    style={{ background: considerReadiness ? '#0A0A0F' : '#6B6B8A' }}
                    animate={{ left: considerReadiness ? '22px' : '2px' }}
                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  />
                </button>
              </div>

              {/* Restrictions */}
              <p className="text-xs mb-2" style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}>
                Restricciones (opcional)
              </p>
              <textarea
                value={restrictions}
                onChange={e => setRestrictions(e.target.value)}
                placeholder="Lesiones, zonas a evitar, consideraciones..."
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
        </AnimatePresence>
      </div>

      {/* Validation error */}
      <AnimatePresence>
        {validationError && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="px-6"
          >
            <p
              className="text-xs font-medium py-2"
              style={{ color: '#EF4444', fontFamily: "'DM Sans', sans-serif" }}
            >
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
            style={{
              background: '#1C1C26',
              color: '#F0F0FF',
              border: '1px solid #2A2A3A',
              fontFamily: "'DM Sans', sans-serif",
            }}
          >
            Atrás
          </button>
        ) : (
          <div />
        )}

        {step < 2 ? (
          <button
            onClick={handleNext}
            className="px-6 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 hover:scale-105"
            style={{
              background: '#E8FF47',
              color: '#0A0A0F',
              fontFamily: "'DM Sans', sans-serif",
            }}
          >
            Siguiente
          </button>
        ) : (
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="px-6 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:hover:scale-100 flex items-center gap-2"
            style={{
              background: '#E8FF47',
              color: '#0A0A0F',
              fontFamily: "'DM Sans', sans-serif",
            }}
          >
            {generating && (
              <svg
                className="animate-spin h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                  style={{ opacity: 0.3 }}
                />
                <path
                  d="M12 2a10 10 0 0 1 10 10"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                />
              </svg>
            )}
            {generating ? 'Generando...' : 'Generar Plan'}
          </button>
        )}
      </div>
    </div>
  );
};

export default PlanWizard;
