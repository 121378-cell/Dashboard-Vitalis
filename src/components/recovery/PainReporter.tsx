import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { recoveryService } from '../../services/recoveryService';

interface PainReporterProps {
  onReported?: () => void;
}

type PainType = 'agudo' | 'sordo' | 'ardor' | 'fatiga';

const PAIN_TYPE_LABELS: Record<PainType, { label: string; emoji: string; desc: string }> = {
  agudo: { label: 'Agudo', emoji: '⚡', desc: 'Punzante, punzada' },
  sordo: { label: 'Sordo', emoji: '🪨', desc: 'Continuo, molesto' },
  ardor: { label: 'Ardor', emoji: '🔥', desc: 'Quemazón, inflamación' },
  fatiga: { label: 'Fatiga', emoji: '😩', desc: 'Cansancio muscular' },
};

interface BodyZone {
  id: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

const BODY_ZONES_FRONT: BodyZone[] = [
  { id: 'head', label: 'Cabeza', x: 88, y: 2, width: 24, height: 24 },
  { id: 'neck', label: 'Cuello', x: 90, y: 28, width: 20, height: 14 },
  { id: 'shoulder_left', label: 'Hombro Izq.', x: 62, y: 42, width: 22, height: 16 },
  { id: 'shoulder_right', label: 'Hombro Der.', x: 116, y: 42, width: 22, height: 16 },
  { id: 'chest', label: 'Pecho', x: 86, y: 52, width: 28, height: 24 },
  { id: 'upper_back', label: 'Espalda Alta', x: 86, y: 48, width: 28, height: 12 },
  { id: 'elbow_left', label: 'Codo Izq.', x: 52, y: 76, width: 16, height: 16 },
  { id: 'elbow_right', label: 'Codo Der.', x: 132, y: 76, width: 16, height: 16 },
  { id: 'core', label: 'Core', x: 86, y: 78, width: 28, height: 20 },
  { id: 'wrist_left', label: 'Muñeca Izq.', x: 46, y: 106, width: 14, height: 14 },
  { id: 'wrist_right', label: 'Muñeca Der.', x: 140, y: 106, width: 14, height: 14 },
  { id: 'hip_left', label: 'Cadera Izq.', x: 72, y: 100, width: 18, height: 18 },
  { id: 'hip_right', label: 'Cadera Der.', x: 110, y: 100, width: 18, height: 18 },
  { id: 'lower_back', label: 'Lumbar', x: 86, y: 96, width: 28, height: 14 },
  { id: 'knee_left', label: 'Rodilla Izq.', x: 76, y: 138, width: 16, height: 18 },
  { id: 'knee_right', label: 'Rodilla Der.', x: 108, y: 138, width: 16, height: 18 },
  { id: 'ankle_left', label: 'Tobillo Izq.', x: 78, y: 174, width: 12, height: 14 },
  { id: 'ankle_right', label: 'Tobillo Der.', x: 110, y: 174, width: 12, height: 14 },
  { id: 'hand_left', label: 'Mano Izq.', x: 42, y: 120, width: 14, height: 14 },
  { id: 'hand_right', label: 'Mano Der.', x: 144, y: 120, width: 14, height: 14 },
];

export const PainReporter = ({ onReported }: PainReporterProps) => {
  const [selectedZone, setSelectedZone] = useState<string | null>(null);
  const [painLevel, setPainLevel] = useState(5);
  const [painType, setPainType] = useState<PainType>('sordo');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ message: string; zones_to_avoid: string[] } | null>(null);

  const handleSubmit = async () => {
    if (!selectedZone) return;
    setSubmitting(true);
    try {
      const res = await recoveryService.reportPain({
        zone: selectedZone,
        pain_level: painLevel,
        pain_type: painType,
        notes: notes || undefined,
      });
      setResult({
        message: res.data.message,
        zones_to_avoid: res.data.zones_to_avoid,
      });
      onReported?.();
    } catch {
      setResult({ message: 'Error al reportar. Inténtalo de nuevo.', zones_to_avoid: [] });
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setSelectedZone(null);
    setPainLevel(5);
    setPainType('sordo');
    setNotes('');
    setResult(null);
  };

  const getPainColor = (level: number) => {
    if (level <= 3) return '#4ADE80';
    if (level <= 5) return '#FBBF24';
    if (level <= 7) return '#FB923C';
    return '#EF4444';
  };

  const selectedZoneData = BODY_ZONES_FRONT.find(z => z.id === selectedZone);

  return (
    <div className="glass-high rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-[var(--color-outline)] flex items-center gap-2">
        <span className="text-xl">🩺</span>
        <h3 className="font-display font-semibold text-[var(--color-text)]">
          Reportar Dolor
        </h3>
      </div>

      <div className="p-4">
        {/* Result message */}
        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className={`p-3 rounded-xl mb-4 ${painLevel >= 8 ? 'bg-red-500/10 border border-red-500/30' : 'bg-emerald-500/10 border border-emerald-500/30'}`}
            >
              <p className={`text-sm ${painLevel >= 8 ? 'text-red-400' : 'text-emerald-400'}`}>
                {result.message}
              </p>
              {painLevel >= 8 && (
                <p className="text-xs text-red-300 mt-1 font-semibold">
                  ⚠️ Consulta a un profesional médico antes de continuar entrenando.
                </p>
              )}
              {result.zones_to_avoid.length > 0 && (
                <p className="text-xs text-[var(--color-text-muted)] mt-1">
                  Zonas a evitar: {result.zones_to_avoid.map(z => z.replace(/_/g, ' ')).join(', ')}
                </p>
              )}
              <button
                onClick={handleReset}
                className="mt-2 text-xs text-[var(--color-primary)] hover:underline"
              >
                Reportar otra molestia
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {!result && (
          <>
            {/* Body Map SVG */}
            <div className="flex justify-center mb-4">
              <svg
                viewBox="0 0 200 200"
                className="w-full max-w-[280px]"
                style={{ filter: 'drop-shadow(0 0 20px rgba(99, 102, 241, 0.15))' }}
              >
                {/* Body outline */}
                <ellipse cx="100" cy="14" rx="12" ry="12" fill="var(--color-surface-high)" stroke="var(--color-outline)" strokeWidth="1" />
                <rect x="90" y="28" width="20" height="14" rx="4" fill="var(--color-surface-high)" stroke="var(--color-outline)" strokeWidth="1" />
                <path
                  d="M 76 44 L 62 42 L 52 76 L 46 106 L 42 120 L 50 134 L 56 134 L 58 120 L 62 106 L 68 90 L 72 100 L 76 138 L 78 174 L 82 188 L 92 188 L 92 174 L 90 138 L 86 100 L 100 100 L 114 100 L 110 138 L 108 174 L 108 188 L 118 188 L 122 174 L 124 138 L 128 100 L 132 90 L 138 106 L 142 120 L 144 134 L 150 134 L 158 120 L 154 106 L 148 76 L 138 42 L 124 44 L 114 48 L 100 52 L 86 48 L 76 44 Z"
                  fill="var(--color-surface-high)"
                  stroke="var(--color-outline)"
                  strokeWidth="1"
                />

                {/* Clickable zone overlays */}
                {BODY_ZONES_FRONT.map(zone => (
                  <g key={zone.id}>
                    <rect
                      x={zone.x}
                      y={zone.y}
                      width={zone.width}
                      height={zone.height}
                      rx="4"
                      fill={
                        selectedZone === zone.id
                          ? `${getPainColor(painLevel)}40`
                          : 'transparent'
                      }
                      stroke={
                        selectedZone === zone.id
                          ? getPainColor(painLevel)
                          : 'transparent'
                      }
                      strokeWidth={selectedZone === zone.id ? 2 : 0}
                      className="cursor-pointer"
                      onClick={() => setSelectedZone(zone.id)}
                    />
                    {/* Hover area (larger, transparent) */}
                    <rect
                      x={zone.x - 2}
                      y={zone.y - 2}
                      width={zone.width + 4}
                      height={zone.height + 4}
                      rx="6"
                      fill="transparent"
                      className="cursor-pointer hover:fill-white/5 transition-colors"
                      onClick={() => setSelectedZone(zone.id)}
                    />
                  </g>
                ))}

                {/* Selected zone indicator */}
                {selectedZone && selectedZoneData && (
                  <motion.circle
                    cx={selectedZoneData.x + selectedZoneData.width / 2}
                    cy={selectedZoneData.y + selectedZoneData.height / 2}
                    r="4"
                    fill={getPainColor(painLevel)}
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="animate-ping"
                  />
                )}
              </svg>
            </div>

            {/* Zone label */}
            <AnimatePresence>
              {selectedZone && (
                <motion.div
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-center mb-4"
                >
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--color-primary)]/10 text-[var(--color-primary)] text-sm font-medium">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: getPainColor(painLevel) }} />
                    {selectedZoneData?.label || selectedZone.replace(/_/g, ' ')}
                  </span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Pain level slider */}
            {selectedZone && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-4"
              >
                <div>
                  <label className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider block mb-2">
                    Intensidad: <span style={{ color: getPainColor(painLevel) }} className="font-bold">{painLevel}/10</span>
                  </label>
                  <input
                    type="range"
                    min={1}
                    max={10}
                    value={painLevel}
                    onChange={(e) => setPainLevel(Number(e.target.value))}
                    className="w-full h-2 rounded-full appearance-none cursor-pointer"
                    style={{
                      background: `linear-gradient(to right, #4ADE80, #FBBF24, #FB923C, #EF4444)`,
                    }}
                  />
                  <div className="flex justify-between text-xs text-[var(--color-text-subtle)] mt-1">
                    <span>Leve</span>
                    <span>Moderado</span>
                    <span>Severo</span>
                  </div>
                </div>

                {/* Pain type selection */}
                <div>
                  <label className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider block mb-2">
                    Tipo de dolor
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {(Object.entries(PAIN_TYPE_LABELS) as [PainType, typeof PAIN_TYPE_LABELS[PainType]][]).map(([type, info]) => (
                      <button
                        key={type}
                        onClick={() => setPainType(type)}
                        className={`p-2.5 rounded-xl border transition-all text-left ${
                          painType === type
                            ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10'
                            : 'border-white/10 bg-white/5 hover:bg-white/10'
                        }`}
                      >
                        <span className="text-lg">{info.emoji}</span>
                        <p className={`text-sm font-medium ${painType === type ? 'text-[var(--color-primary)]' : 'text-[var(--color-text)]'}`}>
                          {info.label}
                        </p>
                        <p className="text-xs text-[var(--color-text-muted)]">{info.desc}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Notes */}
                <div>
                  <label className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider block mb-2">
                    Notas (opcional)
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Ej: Dolor al flexionar, aparece después de sentadillas..."
                    rows={2}
                    className="w-full text-sm px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-[var(--color-text)] placeholder:text-[var(--color-text-subtle)] focus:outline-none focus:border-[var(--color-primary)] resize-none"
                  />
                </div>

                {/* Submit */}
                <button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="w-full py-3 rounded-xl bg-[var(--color-primary)] text-white font-semibold disabled:opacity-40 hover:brightness-110 transition-all flex items-center justify-center gap-2"
                >
                  {submitting ? (
                    <span className="animate-spin">⏳</span>
                  ) : (
                    <span>📍</span>
                  )}
                  {submitting ? 'Guardando...' : 'Reportar Molestia'}
                </button>

                {painLevel >= 8 && (
                  <p className="text-xs text-red-400 text-center">
                    ⚠️ Dolor agudo detectado. ATLAS recomienda consultar a un profesional médico.
                  </p>
                )}
              </motion.div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default PainReporter;
