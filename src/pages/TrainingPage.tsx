import React, { useRef } from 'react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import { Activity, Dumbbell, TrendingUp, Target } from 'lucide-react';
import { CustomTooltip } from '../components/charts/CustomTooltip';
import { ChartSkeleton } from '../components/charts/ChartSkeleton';
import { ExportButton } from '../components/common/ExportButton';
import { ChartExportButton } from '../components/common/ChartExportButton';
import { useMuscleVolume, usePersonalRecords, useTrainingDistribution } from '../hooks/useDashboardData';
import { ExerciseSelector } from '../components/ExerciseSelector';

const COLORS = {
  primary: '#E8FF47',
  chest: '#4ADE80',
  back: '#60A5FA',
  legs: '#FB923C',
  shoulders: '#F472B6',
  arms: '#A78BFA',
  core: '#34D399',
  muted: '#6B6B8A',
};

const MUSCLE_COLORS: Record<string, string> = {
  'Chest': COLORS.chest,
  'Back': COLORS.back,
  'Legs': COLORS.legs,
  'Shoulders': COLORS.shoulders,
  'Arms': COLORS.arms,
  'Core': COLORS.core,
  'Full Body': COLORS.primary,
  'Cardio': COLORS.muted,
};

export const TrainingPage = () => {
  const weeklyRef = useRef<HTMLDivElement>(null);
  const pieRef = useRef<HTMLDivElement>(null);

  const { data: muscleVolume, isLoading: isLoadingVolume } = useMuscleVolume(12);
  const { data: personalRecords, isLoading: isLoadingPRs } = usePersonalRecords();
  const { data: distribution, isLoading: isLoadingDistribution } = useTrainingDistribution(90);

  const isLoading = isLoadingVolume || isLoadingPRs || isLoadingDistribution;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-display font-bold text-[var(--color-text)]">
          Training Analytics
        </h1>
        <ChartSkeleton count={4} />
      </div>
    );
  }

  const weeklyData = muscleVolume?.length ? muscleVolume : [];
  const prs = personalRecords?.length ? personalRecords : [];
  const sessionData = distribution?.length ? distribution : [];

  const totalByMuscle = Object.entries(
    weeklyData.slice(-4).reduce((acc: Record<string, number>, week: any) => {
      Object.entries(week).forEach(([muscle, value]) => {
        if (muscle !== 'week' && typeof value === 'number') {
          acc[muscle] = (acc[muscle] || 0) + value;
        }
      });
      return acc;
    }, {} as Record<string, number>)
  ).map(([muscle, value]) => ({
    muscle,
    value,
    color: MUSCLE_COLORS[muscle] || COLORS.primary,
  }));

  const pieData = totalByMuscle.map(d => ({
    name: d.muscle,
    value: d.value,
    color: d.color,
  }));

  return (
    <div className="space-y-6">
      <div className="mb-8">
        <ExerciseSelector />
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-[var(--color-text)]">
            Training Analytics
          </h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Volume, progression, and training distribution
          </p>
        </div>
        <div className="flex gap-2">
          <ExportButton data={weeklyData} filename="weekly-volume" format="csv" />
          <ChartExportButton chartRef={weeklyRef} filename="weekly-stacked-bar" />
        </div>
      </div>

      {/* Weekly Volume Stacked Bar */}
      <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[var(--color-primary)]/20">
              <Dumbbell className="w-5 h-5 text-[var(--color-primary)]" />
            </div>
            <div>
              <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                Weekly Volume by Muscle Group
              </h3>
              <p className="text-sm text-[var(--color-text-muted)]">
                12-week rolling volume distribution (minutes)
              </p>
            </div>
          </div>
          <ChartExportButton chartRef={weeklyRef} filename="weekly-muscle-volume" />
        </div>
        {weeklyData.length > 0 ? (
          <div ref={weeklyRef}>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart
                data={weeklyData}
                margin={{ top: 20, right: 30, left: 10, bottom: 20 }}
                barSize={25}
                barGap={0}
              >
                <CartesianGrid stroke="var(--color-outline-variant)" strokeDasharray="3 3" horizontal={true} vertical={false} />
                <XAxis
                  dataKey="week"
                  tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                  stroke="var(--color-outline-variant)"
                />
                <YAxis
                  tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                  stroke="var(--color-outline-variant)"
                  label={{ value: 'Volume (min)', angle: -90, position: 'insideLeft', style: { fill: 'var(--color-text-muted)', fontSize: 11 } }}
                />
                <Tooltip
                  content={<CustomTooltip />}
                  cursor={{ fill: 'rgba(232, 255, 71, 0.1)' }}
                />
                <Legend
                  verticalAlign="top"
                  height={44}
                  wrapperStyle={{ fontSize: '10px', paddingTop: '10px' }}
                  iconType="square"
                />
                <Bar dataKey="Chest" stackId="a" fill={COLORS.chest} />
                <Bar dataKey="Back" stackId="a" fill={COLORS.back} />
                <Bar dataKey="Legs" stackId="a" fill={COLORS.legs} />
                <Bar dataKey="Shoulders" stackId="a" fill={COLORS.shoulders} />
                <Bar dataKey="Arms" stackId="a" fill={COLORS.arms} />
                <Bar dataKey="Core" stackId="a" fill={COLORS.core} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-[350px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
            No training volume data available
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Muscle Group Distribution Pie */}
        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-[var(--color-primary)]/20">
                <Dumbbell className="w-5 h-5 text-[var(--color-primary)]" />
              </div>
              <div>
                <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                  Muscle Group Focus
                </h3>
                <p className="text-sm text-[var(--color-text-muted)]">
                  Last 4 weeks volume distribution
                </p>
              </div>
            </div>
            <ChartExportButton chartRef={pieRef} filename="muscle-distribution" />
          </div>
          {pieData.length > 0 ? (
            <div ref={pieRef}>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={70}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                    stroke="var(--color-surface-container)"
                    strokeWidth={2}
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={<CustomTooltip />}
                    cursor={{ fill: 'rgba(232, 255, 71, 0.1)' }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    height={50}
                    wrapperStyle={{ fontSize: '10px', lineHeight: '1.4' }}
                    iconType="square"
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-[280px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
              No muscle distribution data available
            </div>
          )}
        </div>

        {/* Training Type Distribution */}
        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-[var(--color-info)]/20">
                <Activity className="w-5 h-5 text-[var(--color-info)]" />
              </div>
              <div>
                <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                  Training Type Distribution
                </h3>
                <p className="text-sm text-[var(--color-text-muted)]">
                  Activity breakdown (last 90 days)
                </p>
              </div>
            </div>
          </div>
          {sessionData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={sessionData}
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="var(--color-surface-container)"
                  strokeWidth={2}
                >
                  {sessionData.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  verticalAlign="bottom"
                  height={50}
                  wrapperStyle={{ fontSize: '10px', lineHeight: '1.4' }}
                  iconType="square"
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[280px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
              No training type data available
            </div>
          )}
        </div>
      </div>

      {/* PR Timeline */}
      <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[var(--color-success)]/20">
              <Target className="w-5 h-5 text-[var(--color-success)]" />
            </div>
            <div>
              <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                Personal Best Timeline
              </h3>
              <p className="text-sm text-[var(--color-text-muted)]">
                Recent record achievements
              </p>
            </div>
          </div>
        </div>
        {prs.length > 0 ? (
          <div className="relative">
            {prs.map((pr: any, index: number) => (
              <div key={index} className="flex items-start gap-4 pb-6 last:pb-0">
                <div className="flex flex-col items-center">
                  <div className="w-3 h-3 rounded-full bg-[var(--color-primary)] shadow-[0_0_10px_rgba(232,255,71,0.5)]" />
                  {index < prs.length - 1 && (
                    <div className="w-px h-full bg-[var(--color-outline-variant)]" />
                  )}
                </div>
                <div className="flex-1 bg-[var(--color-surface)] rounded-lg p-4 border border-[var(--color-outline-variant)]/20 hover:border-[var(--color-primary)]/30 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[var(--color-text)]">
                      {pr.exercise}
                    </span>
                    <span className="text-xs px-2 py-1 rounded bg-[var(--color-primary)]/20 text-[var(--color-primary)]">
                      {pr.muscle}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-display font-bold text-[var(--color-text)]">
                      {pr.pr}
                    </span>
                    <span className="text-sm text-[var(--color-text-muted)]">
                      {pr.unit}
                    </span>
                    {pr.reps && (
                      <span className="text-xs text-[var(--color-text-muted)]">
                        x{pr.reps} reps
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1">
                    {pr.date}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="h-[200px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
            No personal records logged yet
          </div>
        )}
      </div>
    </div>
  );
};
