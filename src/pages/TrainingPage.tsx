import React, { useRef, useMemo } from 'react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import { Activity, Dumbbell, TrendingUp, Target } from 'lucide-react';
import { CustomTooltip } from '../components/charts/CustomTooltip';
import { ChartSkeleton } from '../components/charts/ChartSkeleton';
import { ExportButton } from '../components/common/ExportButton';
import { ChartExportButton } from '../components/common/ChartExportButton';
import { useWorkouts, useAnalytics } from '../hooks/useDashboardData';

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

const MUSCLE_COLORS = {
  'Chest': COLORS.chest,
  'Back': COLORS.back,
  'Legs': COLORS.legs,
  'Shoulders': COLORS.shoulders,
  'Arms': COLORS.arms,
  'Core': COLORS.core,
  'Full Body': COLORS.primary,
  'Cardio': COLORS.muted,
};

const generateMockTrainingData = () => {
  const weeks = Array.from({ length: 12 }, (_, i) => {
    const weekNum = i + 1;
    return {
      week: `W${weekNum}`,
      Chest: Math.floor(80 + Math.random() * 120),
      Back: Math.floor(90 + Math.random() * 110),
      Legs: Math.floor(120 + Math.random() * 180),
      Shoulders: Math.floor(60 + Math.random() * 90),
      Arms: Math.floor(40 + Math.random() * 80),
      Core: Math.floor(30 + Math.random() * 70),
    };
  });

  const progression = Array.from({ length: 16 }, (_, i) => ({
    week: i + 1,
    bench: Math.floor(40 + i * 0.8 + Math.random() * 5),
    squat: Math.floor(60 + i * 1.2 + Math.random() * 8),
    deadlift: Math.floor(80 + i * 1.5 + Math.random() * 10),
  }));

  const prs = [
    { date: '2024-10-15', exercise: 'Bench Press', pr: 52, unit: 'kg', muscle: 'Chest' },
    { date: '2024-09-28', exercise: 'Squat', pr: 85, unit: 'kg', muscle: 'Legs' },
    { date: '2024-09-10', exercise: 'Deadlift', pr: 110, unit: 'kg', muscle: 'Back' },
    { date: '2024-08-22', exercise: 'Overhead Press', pr: 42, unit: 'kg', muscle: 'Shoulders' },
    { date: '2024-08-05', exercise: 'Barbell Row', pr: 70, unit: 'kg', muscle: 'Back' },
    { date: '2024-07-18', exercise: 'Bicep Curl', pr: 25, unit: 'kg', muscle: 'Arms' },
  ].map(p => ({ ...p, dateObj: new Date(p.date) }))
    .sort((a, b) => b.dateObj.getTime() - a.dateObj.getTime())
    .map(({ dateObj, ...rest }) => rest);

  const intensityData = Array.from({ length: 8 }, (_, i) => ({
    zone: `Week ${i + 1}`,
    'Zone 1': Math.floor(20 + Math.random() * 30),
    'Zone 2': Math.floor(40 + Math.random() * 40),
    'Zone 3': Math.floor(30 + Math.random() * 30),
    'Zone 4': Math.floor(10 + Math.random() * 20),
    'Zone 5': Math.floor(5 + Math.random() * 10),
  }));

  return { weekly: weeks, progression, prs, intensity: intensityData };
};

export const TrainingPage = () => {
  const weeklyRef = useRef<HTMLDivElement>(null);
  const progressionRef = useRef<HTMLDivElement>(null);
  const pieRef = useRef<HTMLDivElement>(null);
  const intensityRef = useRef<HTMLDivElement>(null);

  const { data: workouts, isLoading } = useWorkouts(50);

  const mockData = useMemo(() => generateMockTrainingData(), []);

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

  const totalByMuscle = Object.entries(
    mockData.weekly.slice(-4).reduce((acc, week) => {
      Object.entries(week).forEach(([muscle, value]) => {
        if (muscle !== 'week') {
          acc[muscle] = (acc[muscle] || 0) + (value as number);
        }
      });
      return acc;
    }, {} as Record<string, number>)
  ).map(([muscle, value]) => ({
    muscle,
    value,
    color: MUSCLE_COLORS[muscle as keyof typeof MUSCLE_COLORS] || COLORS.primary,
  }));

  const pieData = totalByMuscle.map(d => ({
    name: d.muscle,
    value: d.value,
    color: d.color,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-[var(--color-text)]">
            Training Analytics
          </h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Volume, progression, and intensity tracking
          </p>
        </div>
        <div className="flex gap-2">
          <ExportButton data={mockData.weekly} filename="weekly-volume" format="csv" />
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
                12-week rolling volume distribution
              </p>
            </div>
          </div>
          <ChartExportButton chartRef={weeklyRef} filename="weekly-muscle-volume" />
        </div>
        <div ref={weeklyRef}>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart
              data={mockData.weekly}
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
                label={{ value: 'Volume (kg)', angle: -90, position: 'insideLeft', style: { fill: 'var(--color-text-muted)', fontSize: 11 } }}
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
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Exercise Progression Line Chart */}
        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-[var(--color-success)]/20">
                <TrendingUp className="w-5 h-5 text-[var(--color-success)]" />
              </div>
              <div>
                <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                  Exercise Progression
                </h3>
                <p className="text-sm text-[var(--color-text-muted)]">
                  Main lifts progression over 16 weeks
                </p>
              </div>
            </div>
            <ChartExportButton chartRef={progressionRef} filename="exercise-progression" />
          </div>
          <div ref={progressionRef}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={mockData.progression} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                <defs>
                  <linearGradient id="colorBench" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#E8FF47" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#E8FF47" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorSquat" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4ADE80" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#4ADE80" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorDeadlift" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#60A5FA" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#60A5FA" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--color-outline-variant)" strokeDasharray="3 3" vertical={false} />
                <XAxis 
                  dataKey="week" 
                  tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                  stroke="var(--color-outline-variant)"
                  label={{ value: 'Week', position: 'bottom', offset: -5, style: { fill: 'var(--color-text-muted)', fontSize: 11 } }}
                />
                <YAxis 
                  tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                  stroke="var(--color-outline-variant)"
                  domain={[0, 'dataMax + 20']}
                  label={{ value: 'Weight (kg)', angle: -90, position: 'insideLeft', style: { fill: 'var(--color-text-muted)', fontSize: 11 } }}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ strokeWidth: 1 }} />
                <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '11px' }} />
                <Line 
                  type="monotone" 
                  dataKey="bench" 
                  stroke="#E8FF47" 
                  strokeWidth={2.5}
                  dot={{ fill: '#E8FF47', strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6, fill: '#E8FF47', stroke: '#0A0A0F', strokeWidth: 2 }}
                  name="Bench Press"
                />
                <Line 
                  type="monotone" 
                  dataKey="squat" 
                  stroke="#4ADE80" 
                  strokeWidth={2.5}
                  dot={{ fill: '#4ADE80', strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6, fill: '#4ADE80', stroke: '#0A0A0F', strokeWidth: 2 }}
                  name="Squat"
                />
                <Line 
                  type="monotone" 
                  dataKey="deadlift" 
                  stroke="#60A5FA" 
                  strokeWidth={2.5}
                  dot={{ fill: '#60A5FA', strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6, fill: '#60A5FA', stroke: '#0A0A0F', strokeWidth: 2 }}
                  name="Deadlift"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

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
        <div className="relative">
          {mockData.prs.map((pr, index) => (
            <div key={index} className="flex items-start gap-4 pb-6 last:pb-0">
              <div className="flex flex-col items-center">
                <div className="w-3 h-3 rounded-full bg-[var(--color-primary)] shadow-[0_0_10px_rgba(232,255,71,0.5)]" />
                {index < mockData.prs.length - 1 && (
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
                </div>
                <p className="text-xs text-[var(--color-text-muted)] mt-1">
                  {pr.date}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Intensity Zone Distribution */}
      <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[var(--color-warning)]/20">
              <Activity className="w-5 h-5 text-[var(--color-warning)]" />
            </div>
            <div>
              <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                Intensity Zone Distribution
              </h3>
              <p className="text-sm text-[var(--color-text-muted)]">
                Training time in heart rate zones
              </p>
            </div>
          </div>
          <ChartExportButton chartRef={intensityRef} filename="intensity-zones" />
        </div>
        <div ref={intensityRef}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={mockData.intensity} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
              <CartesianGrid stroke="var(--color-outline-variant)" strokeDasharray="3 3" horizontal={true} vertical={false} />
              <XAxis 
                dataKey="zone" 
                tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                stroke="var(--color-outline-variant)"
              />
              <YAxis 
                tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                stroke="var(--color-outline-variant)"
                label={{ value: 'Minutes', angle: -90, position: 'insideLeft', style: { fill: 'var(--color-text-muted)', fontSize: 11 } }}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(232, 255, 71, 0.1)' }} />
              <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '10px' }} />
              <Bar dataKey="Zone 1" stackId="a" fill="#6B6B8A" />
              <Bar dataKey="Zone 2" stackId="a" fill="#4ADE80" />
              <Bar dataKey="Zone 3" stackId="a" fill="#FB923C" />
              <Bar dataKey="Zone 4" stackId="a" fill="#F87171" />
              <Bar dataKey="Zone 5" stackId="a" fill="#E8FF47" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
