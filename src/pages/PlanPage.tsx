import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  useCurrentPlan,
  useGeneratePlan,
  useAdaptSession,
  useCompleteSession,
  useSessionProgression,
  useReadiness,
  useActiveMasterPlan,
  useMasterPlanProgress,
  useCreateMasterPlan,
  useProposeNextWeek,
  useConfirmWeek,
  useCancelMasterPlan,
} from '../hooks/useDashboardData';
import { planApi } from '../services/planService';
import type {
  AdaptivePlanSession,
  AdaptiveWeeklyPlan,
  GeneratePlanRequest,
  CreateMasterPlanRequest,
} from '../types';
import PlanWizard from '../components/training/PlanWizard';
import WeeklyCalendar from '../components/training/WeeklyCalendar';
import SessionDetailPanel from '../components/training/SessionDetailPanel';
import SessionEditModal from '../components/training/SessionEditModal';
import MasterPlanWizard from '../components/plan/MasterPlanWizard';
import MasterPlanDashboard from '../components/plan/MasterPlanDashboard';

export const PlanPage: React.FC = () => {
  const [selectedSession, setSelectedSession] = useState<AdaptivePlanSession | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editSessionId, setEditSessionId] = useState<number>(0);
  const [editSessionTitle, setEditSessionTitle] = useState('');
  const [detecting, setDetecting] = useState(false);

  const { data: planResponse, isLoading, refetch } = useCurrentPlan();
  const generatePlan = useGeneratePlan();
  const adaptSession = useAdaptSession();
  const completeSession = useCompleteSession();
  const { data: readinessData } = useReadiness();

  const { data: progressions, isLoading: progressionsLoading } = useSessionProgression(
    selectedSession?.id ?? null
  );

  const plan: AdaptiveWeeklyPlan | null = planResponse?.has_plan ? planResponse.data : null;

  const { data: masterPlanResponse, isLoading: masterPlanLoading, refetch: refetchMasterPlan } = useActiveMasterPlan();
  const masterPlan = masterPlanResponse?.has_plan ? masterPlanResponse.data : null;

  const { data: masterPlanProgress } = useMasterPlanProgress(masterPlan?.id ?? null);

  const createMasterPlan = useCreateMasterPlan();
  const proposeNextWeek = useProposeNextWeek();
  const confirmWeek = useConfirmWeek();
  const cancelMasterPlan = useCancelMasterPlan();

  const readinessScore = readinessData?.readiness_score ?? null;

  const handleGenerate = useCallback(
    async (request: GeneratePlanRequest) => {
      await generatePlan.mutateAsync(request as unknown as Record<string, unknown>);
    },
    [generatePlan]
  );

  const handleCreateMasterPlan = useCallback(
    async (request: CreateMasterPlanRequest) => {
      await createMasterPlan.mutateAsync(request);
      refetchMasterPlan();
    },
    [createMasterPlan, refetchMasterPlan]
  );

  const handleSelectSession = useCallback((session: AdaptivePlanSession) => {
    setSelectedSession(session);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedSession(null);
  }, []);

  const handleCompleteSession = useCallback(
    async (sessionId: number, completed: boolean) => {
      await completeSession.mutateAsync({
        sessionId,
        request: { completed, garmin_activity_id: undefined },
      });
    },
    [completeSession]
  );

  const handleAdaptSession = useCallback(
    (sessionId: number, title: string) => {
      setEditSessionId(sessionId);
      setEditSessionTitle(title);
      setEditModalOpen(true);
    },
    []
  );

  const handleAdaptSubmit = useCallback(
    async (sessionId: number, request: string) => {
      await adaptSession.mutateAsync({ sessionId, request: { user_request: request } });
      setEditModalOpen(false);
      setSelectedSession(null);
    },
    [adaptSession]
  );

  const handleDetectCompleted = useCallback(async () => {
    setDetecting(true);
    try {
      await planApi.detectCompleted();
      await refetch();
    } finally {
      setDetecting(false);
    }
  }, [refetch]);

  const handleProposeNextWeek = useCallback(
    async (masterPlanId: number): Promise<AdaptiveWeeklyPlan> => {
      return await proposeNextWeek.mutateAsync(masterPlanId);
    },
    [proposeNextWeek]
  );

  const handleConfirmWeek = useCallback(
    async (weeklyPlanId: number) => {
      await confirmWeek.mutateAsync(weeklyPlanId);
      refetchMasterPlan();
    },
    [confirmWeek, refetchMasterPlan]
  );

  const handleCancelMasterPlan = useCallback(
    async (masterPlanId: number) => {
      await cancelMasterPlan.mutateAsync(masterPlanId);
      refetchMasterPlan();
    },
    [cancelMasterPlan, refetchMasterPlan]
  );

  if (isLoading || masterPlanLoading) {
    return (
      <div className="flex items-center justify-center h-[70vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#E8FF47]" />
      </div>
    );
  }

  // Master plan view
  if (masterPlan) {
    const currentWeekPlan = masterPlan.current_weekly_plan
      ? plan
      : null;

    return (
      <div className="p-6">
        <MasterPlanDashboard
          masterPlan={masterPlan}
          progress={masterPlanProgress}
          currentWeekPlan={currentWeekPlan}
          onProposeNextWeek={handleProposeNextWeek}
          onConfirmWeek={handleConfirmWeek}
          onCancelMasterPlan={handleCancelMasterPlan}
          proposingWeek={proposeNextWeek.isPending}
          confirmingWeek={confirmWeek.isPending}
          onSelectSession={handleSelectSession}
          selectedSession={selectedSession}
          onCloseSession={handleCloseDetail}
          onCompleteSession={handleCompleteSession}
          onAdaptSession={(sessionId, title) => handleAdaptSession(sessionId, title)}
          editModalOpen={editModalOpen}
          editSessionId={editSessionId}
          editSessionTitle={editSessionTitle}
          onAdaptSubmit={handleAdaptSubmit}
          onEditModalClose={() => setEditModalOpen(false)}
          adaptingSession={adaptSession.isPending}
          progressions={progressions ?? []}
          progressionsLoading={progressionsLoading}
          readinessScore={readinessScore}
          onDetectCompleted={handleDetectCompleted}
          detecting={detecting}
          onRefetch={refetchMasterPlan}
        />
      </div>
    );
  }

  // No master plan — show wizard or legacy weekly plan
  if (!plan) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1
            className="text-3xl font-bold mb-2"
            style={{ fontFamily: "'Orbitron', sans-serif", color: '#F0F0FF' }}
          >
            Plan Maestro
          </h1>
          <p className="text-[#6B6B8A]">
            ATLAS diseñará un plan periodizado a largo plazo con fases de entrenamiento,
            hitos intermedios y semanas adaptativas que confirmarás una a una.
          </p>
        </motion.div>

        <MasterPlanWizard onCreate={handleCreateMasterPlan} creating={createMasterPlan.isPending} />

        {createMasterPlan.isError && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm"
          >
            Error creando el plan maestro. Inténtalo de nuevo.
          </motion.div>
        )}

        {/* Legacy option */}
        <div className="mt-6 text-center">
          <button
            onClick={async () => {
              await handleGenerate({
                goal: 'Plan semanal rápido',
                consider_readiness: true,
              });
            }}
            disabled={generatePlan.isPending}
            className="text-xs underline transition-colors disabled:opacity-50"
            style={{ color: '#6B6B8A' }}
          >
            O crear un plan semanal sin Plan Maestro
          </button>
        </div>
      </div>
    );
  }

  // Legacy weekly plan view (no master plan)
  return (
    <div className="p-6 space-y-6">
      <WeeklyCalendar
        plan={plan}
        onSelectSession={handleSelectSession}
        onCompleteSession={handleCompleteSession}
        onDetectCompleted={handleDetectCompleted}
        detecting={detecting}
      />

      <SessionDetailPanel
        session={selectedSession}
        onClose={handleCloseDetail}
        onComplete={handleCompleteSession}
        onAdapt={handleAdaptSession}
        progressions={progressions ?? []}
        progressionsLoading={progressionsLoading}
        readiness={readinessScore}
      />

      <SessionEditModal
        open={editModalOpen}
        sessionTitle={editSessionTitle}
        sessionId={editSessionId}
        onSubmit={handleAdaptSubmit}
        onClose={() => setEditModalOpen(false)}
        loading={adaptSession.isPending}
      />
    </div>
  );
};

export default PlanPage;
