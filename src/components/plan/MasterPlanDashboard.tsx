import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type {
  MasterPlan,
  MasterPlanProgress,
  MasterPlanPhaseTimeline,
  AdaptiveWeeklyPlan,
  AdaptivePlanSession,
} from '../../types';
import WeeklyCalendar from '../training/WeeklyCalendar';
import SessionDetailPanel from '../training/SessionDetailPanel';
import SessionEditModal from '../training/SessionEditModal';

interface MasterPlanDashboardProps {
  masterPlan: MasterPlan;
  progress: MasterPlanProgress | undefined;
  currentWeekPlan: AdaptiveWeeklyPlan | null;
  onProposeNextWeek: (masterPlanId: number) => Promise<AdaptiveWeeklyPlan>;
  onConfirmWeek: (weeklyPlanId: number) => Promise<void>;
  onCancelMasterPlan: (masterPlanId: number) => Promise<void>;
  proposingWeek: boolean;
  confirmingWeek: boolean;
  onSelectSession: (session: AdaptivePlanSession) => void;
  selectedSession: AdaptivePlanSession | null;
  onCloseSession: () => void;
  onCompleteSession: (sessionId: number, completed: boolean) => void;
  onAdaptSession: (sessionId: number, title: string) => void;
  editModalOpen: boolean;
  editSessionId: number;
  editSessionTitle: string;
  onAdaptSubmit: (sessionId: number, request: string) => Promise<void>;
  onEditModalClose: () => void;
  adaptingSession: boolean;
  progressions: any[];
  progressionsLoading: boolean;
  readinessScore: number | null;
  onDetectCompleted: () => void;
  detecting: boolean;
  onRefetch: () => void;
}

const PHASE_STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  completed: { bg: 'rgba(34,197,94,0.1)', text: '#22C55E', border: 'rgba(34,197,94,0.3)' },
  current: { bg: 'rgba(232,255,71,0.1)', text: '#E8FF47', border: 'rgba(232,255,71,0.3)' },
  pending: { bg: 'rgba(107,107,138,0.1)', text: '#6B6B8A', border: 'rgba(107,107,138,0.2)' },
};

const INTENSITY_BADGE: Record<string, { bg: string; text: string }> = {
  low: { bg: 'rgba(34,197,94,0.15)', text: '#22C55E' },
  medium: { bg: 'rgba(251,191,36,0.15)', text: '#FBBF24' },
  high: { bg: 'rgba(239,68,68,0.15)', text: '#EF4444' },
};

const MasterPlanDashboard: React.FC<MasterPlanDashboardProps> = ({
  masterPlan,
  progress,
  currentWeekPlan,
  onProposeNextWeek,
  onConfirmWeek,
  onCancelMasterPlan,
  proposingWeek,
  confirmingWeek,
  onSelectSession,
  selectedSession,
  onCloseSession,
  onCompleteSession,
  onAdaptSession,
  editModalOpen,
  editSessionId,
  editSessionTitle,
  onAdaptSubmit,
  onEditModalClose,
  adaptingSession,
  progressions,
  progressionsLoading,
  readinessScore,
  onDetectCompleted,
  detecting,
  onRefetch,
}) => {
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  const handleProposeNextWeek = useCallback(async () => {
    const result = await onProposeNextWeek(masterPlan.id);
    onRefetch();
    return result;
  }, [onProposeNextWeek, masterPlan.id, onRefetch]);

  const handleConfirmWeek = useCallback(async () => {
    if (masterPlan.next_unconfirmed_week) {
      await onConfirmWeek(masterPlan.next_unconfirmed_week.id);
    }
  }, [onConfirmWeek, masterPlan.next_unconfirmed_week]);

  const completionPct = progress?.completion_pct ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: '#F0F0FF', fontFamily: "'Orbitron', sans-serif" }}>
              {masterPlan.title}
            </h1>
            <p className="text-sm mt-1" style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}>
              {masterPlan.strategy}
            </p>
          </div>
          <button
            onClick={() => setShowCancelConfirm(true)}
            className="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
            style={{ background: 'rgba(239,68,68,0.1)', color: '#EF4444', border: '1px solid rgba(239,68,68,0.2)' }}
          >
            Cancelar Plan
          </button>
        </div>

        {/* Progress bar */}
        <div className="mt-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium" style={{ color: '#F0F0FF', fontFamily: "'DM Sans', sans-serif" }}>
              Progreso general
            </span>
            <span className="text-xs font-bold" style={{ color: '#E8FF47', fontFamily: "'Orbitron', sans-serif" }}>
              {completionPct.toFixed(1)}%
            </span>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ background: '#1C1C26' }}>
            <motion.div
              className="h-full rounded-full"
              style={{ background: 'linear-gradient(90deg, #E8FF47, #B8D936)' }}
              initial={{ width: 0 }}
              animate={{ width: `${completionPct}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
          </div>
          <div className="flex items-center justify-between mt-1.5">
            <span className="text-[10px]" style={{ color: '#6B6B8A' }}>
              Semana {masterPlan.current_week} / {masterPlan.total_weeks}
            </span>
            {masterPlan.days_remaining !== null && (
              <span className="text-[10px]" style={{ color: '#6B6B8A' }}>
                {masterPlan.days_remaining} días restantes
              </span>
            )}
          </div>
        </div>
      </motion.div>

      {/* Phase Timeline */}
      {progress && progress.phase_timeline.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-2xl p-5"
          style={{ background: '#13131A' }}
        >
          <h3 className="text-sm font-bold mb-4" style={{ color: '#F0F0FF', fontFamily: "'Orbitron', sans-serif" }}>
            Fases de Periodización
          </h3>
          <div className="space-y-2">
            {progress.phase_timeline.map((phase: MasterPlanPhaseTimeline) => {
              const colors = PHASE_STATUS_COLORS[phase.status] || PHASE_STATUS_COLORS.pending;
              const intensityBadge = INTENSITY_BADGE[phase.intensity] || INTENSITY_BADGE.medium;
              return (
                <div
                  key={phase.phase_number}
                  className="flex items-start gap-3 p-3 rounded-xl transition-all"
                  style={{ background: colors.bg, border: `1px solid ${colors.border}` }}
                >
                  <div className="flex flex-col items-center mt-0.5 shrink-0">
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                      style={{ background: colors.text, color: phase.status === 'current' ? '#0A0A0F' : '#F0F0FF' }}
                    >
                      {phase.phase_number}
                    </div>
                    {phase.status !== 'pending' && (
                      <div className="w-px h-4 mt-1" style={{ background: colors.border }} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-semibold" style={{ color: colors.text, fontFamily: "'DM Sans', sans-serif" }}>
                        {phase.name}
                      </span>
                      <span
                        className="px-2 py-0.5 rounded-full text-[10px] font-medium"
                        style={{ background: intensityBadge.bg, color: intensityBadge.text }}
                      >
                        {phase.intensity}
                      </span>
                    </div>
                    <p className="text-[11px] mb-1" style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}>
                      {phase.description}
                    </p>
                    <div className="flex items-center gap-3">
                      <span className="text-[10px]" style={{ color: '#6B6B8A' }}>
                        Sem {phase.start_week}–{phase.end_week}
                      </span>
                      <span className="text-[10px]" style={{ color: '#6B6B8A' }}>
                        {phase.focus.join(' + ')}
                      </span>
                    </div>
                  </div>
                  <div className="shrink-0">
                    {phase.status === 'completed' && <span className="text-xs" style={{ color: '#22C55E' }}>&#10003;</span>}
                    {phase.status === 'current' && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold" style={{ background: '#E8FF47', color: '#0A0A0F' }}>
                        ACTIVA
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* Milestones */}
      {progress && progress.milestones.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="rounded-2xl p-5"
          style={{ background: '#13131A' }}
        >
          <h3 className="text-sm font-bold mb-3" style={{ color: '#F0F0FF', fontFamily: "'Orbitron', sans-serif" }}>
            Hitos
          </h3>
          <div className="space-y-2">
            {progress.milestones.map((m, idx) => (
              <div key={idx} className="flex items-center gap-3 p-2.5 rounded-lg" style={{ background: '#1C1C26' }}>
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center text-xs shrink-0"
                  style={{
                    background: m.achieved ? '#22C55E' : '#2A2A3A',
                    color: m.achieved ? '#0A0A0F' : '#6B6B8A',
                  }}
                >
                  {m.achieved ? '✓' : `S${m.week}`}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium" style={{ color: m.achieved ? '#22C55E' : '#F0F0FF', fontFamily: "'DM Sans', sans-serif" }}>
                    {m.description}
                  </p>
                  <p className="text-[10px]" style={{ color: '#6B6B8A' }}>{m.target}</p>
                </div>
                {m.achieved && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold" style={{ background: 'rgba(34,197,94,0.15)', color: '#22C55E' }}>
                    LOGRADO
                  </span>
                )}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Week Management */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="rounded-2xl p-5"
        style={{ background: '#13131A' }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold" style={{ color: '#F0F0FF', fontFamily: "'Orbitron', sans-serif" }}>
            Gestión de Semanas
          </h3>
          <div className="flex items-center gap-2">
            {masterPlan.current_phase && (
              <span
                className="px-2.5 py-1 rounded-full text-[10px] font-medium"
                style={{ background: 'rgba(232,255,71,0.12)', color: '#E8FF47', border: '1px solid rgba(232,255,71,0.25)' }}
              >
                {masterPlan.current_phase.name}
              </span>
            )}
          </div>
        </div>

        {/* Unconfirmed week banner */}
        {masterPlan.next_unconfirmed_week && (
          <div
            className="p-4 rounded-xl mb-4"
            style={{ background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)' }}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold" style={{ color: '#FBBF24', fontFamily: "'DM Sans', sans-serif" }}>
                  Semana {masterPlan.next_unconfirmed_week.week_number} pendiente de confirmación
                </p>
                <p className="text-xs mt-0.5" style={{ color: '#6B6B8A' }}>
                  {masterPlan.next_unconfirmed_week.goal}
                </p>
              </div>
              <button
                onClick={handleConfirmWeek}
                disabled={confirmingWeek}
                className="px-4 py-2 rounded-lg text-xs font-bold transition-all duration-200 hover:scale-105 disabled:opacity-50"
                style={{ background: '#E8FF47', color: '#0A0A0F', fontFamily: "'DM Sans', sans-serif" }}
              >
                {confirmingWeek ? 'Confirmando...' : 'Confirmar Semana'}
              </button>
            </div>
          </div>
        )}

        {/* Propose next week */}
        {!masterPlan.next_unconfirmed_week && masterPlan.current_week < masterPlan.total_weeks && (
          <div className="p-4 rounded-xl" style={{ background: '#1C1C26' }}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium" style={{ color: '#F0F0FF', fontFamily: "'DM Sans', sans-serif" }}>
                  Generar semana {masterPlan.current_week + 1}
                </p>
                <p className="text-xs mt-0.5" style={{ color: '#6B6B8A' }}>
                  ATLAS propondrá la siguiente semana adaptada a tu estado
                </p>
              </div>
              <button
                onClick={handleProposeNextWeek}
                disabled={proposingWeek}
                className="px-4 py-2 rounded-lg text-xs font-bold transition-all duration-200 hover:scale-105 disabled:opacity-50 flex items-center gap-2"
                style={{ background: '#E8FF47', color: '#0A0A0F', fontFamily: "'DM Sans', sans-serif" }}
              >
                {proposingWeek && (
                  <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" style={{ opacity: 0.3 }} />
                    <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                  </svg>
                )}
                {proposingWeek ? 'Generando...' : 'Proponer Semana'}
              </button>
            </div>
          </div>
        )}

        {/* Plan completed message */}
        {masterPlan.current_week >= masterPlan.total_weeks && (
          <div
            className="p-4 rounded-xl text-center"
            style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)' }}
          >
            <p className="text-sm font-semibold" style={{ color: '#22C55E' }}>
              Plan completado
            </p>
            <p className="text-xs mt-1" style={{ color: '#6B6B8A' }}>
              Has completado las {masterPlan.total_weeks} semanas. Considera crear un nuevo plan.
            </p>
          </div>
        )}
      </motion.div>

      {/* Current Week Calendar */}
      {currentWeekPlan && (
        <WeeklyCalendar
          plan={currentWeekPlan}
          onSelectSession={onSelectSession}
          onCompleteSession={onCompleteSession}
          onDetectCompleted={onDetectCompleted}
          detecting={detecting}
        />
      )}

      {/* Session Detail Panel */}
      <SessionDetailPanel
        session={selectedSession}
        onClose={onCloseSession}
        onComplete={onCompleteSession}
        onAdapt={onAdaptSession}
        progressions={progressions}
        progressionsLoading={progressionsLoading}
        readiness={readinessScore}
      />

      {/* Session Edit Modal */}
      <SessionEditModal
        open={editModalOpen}
        sessionTitle={editSessionTitle}
        sessionId={editSessionId}
        onSubmit={onAdaptSubmit}
        onClose={onEditModalClose}
        loading={adaptingSession}
      />

      {/* Cancel Confirmation Modal */}
      <AnimatePresence>
        {showCancelConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ background: 'rgba(0,0,0,0.6)' }}
            onClick={() => setShowCancelConfirm(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="rounded-2xl p-6 max-w-sm w-full"
              style={{ background: '#13131A', border: '1px solid rgba(239,68,68,0.2)' }}
              onClick={e => e.stopPropagation()}
            >
              <h3 className="text-lg font-bold mb-2" style={{ color: '#EF4444', fontFamily: "'Orbitron', sans-serif" }}>
                Cancelar Plan Maestro
              </h3>
              <p className="text-sm mb-4" style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}>
                Se cancelará el plan "{masterPlan.title}" y todas sus semanas pendientes. Esta acción no se puede deshacer.
              </p>
              <div className="flex items-center gap-3 justify-end">
                <button
                  onClick={() => setShowCancelConfirm(false)}
                  className="px-4 py-2 rounded-lg text-xs font-medium"
                  style={{ background: '#1C1C26', color: '#F0F0FF', border: '1px solid #2A2A3A' }}
                >
                  No, mantener
                </button>
                <button
                  onClick={async () => {
                    await onCancelMasterPlan(masterPlan.id);
                    setShowCancelConfirm(false);
                  }}
                  className="px-4 py-2 rounded-lg text-xs font-bold"
                  style={{ background: '#EF4444', color: '#FFF' }}
                >
                  Sí, cancelar
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default MasterPlanDashboard;
