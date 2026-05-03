import React, { useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { Calendar, Activity, TrendingUp, Zap, Dumbbell, Heart } from 'lucide-react';
import { CustomTooltip } from '../components/charts/CustomTooltip';
import { ChartSkeleton } from '../components/charts/ChartSkeleton';
import { ExportButton } from '../components/common/ExportButton';
import { ChartExportButton } from '../components/common/ChartExportButton';
import { useBiometrics, useWorkouts } from '../hooks/useDashboardData';
import { useAnalytics } from '../hooks/useAnalytics';
import { ForecastWidget } from '../components/analytics/ForecastWidget';
import { InsightCard } from '../components/analytics/InsightCard';
import { PlateauAlert } from '../components/analytics/PlateauAlert';


const COLORS = {
  primary: '#E8FF47',
  success: '#4ADE80',
  warning: '#FB923C',
  danger: '#F87171',
  info: '#60A5FA',
  muted: '#6B6B8A',
};

const PAGE_COLORS = ['#E8FF47', '#4ADE80', '#FB923C', '#60A5FA', '#F472B6'];

export const OverviewPage = () => {
  const navigate = useNavigate();
  const heatmapRef = useRef<HTMLDivElement>(null);
  const readinessRef = useRef<HTMLDivElement>(null);
  const pieRef = useRef<HTMLDivElement>(null);

  const { data: biometrics, isLoading: isLoadingBiometrics } = useBiometrics();
  const { data: workouts, isLoading: isLoadingWorkouts } = useWorkouts(50);
  const { insights, forecast, correlations, isLoading: isLoadingAnalytics, refresh: refreshAnalytics } = useAnalytics();

  // Mock data for charts when no API data available
  const generateMockData = () => {
    const days = Array.from({ length: 30 }, (_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - 29 + i);
      return d.toISOString().split('T')[0];
    });

    const readiness = days.map((d, i) => ({
      date: d,
      score: Math.floor(50 + Math.random() * 40 + Math.sin(i / 5) * 15),
      status: i % 7 === 0 ? 'rest' : 'good',
    }));

    const weekly = Array.from({ length: 52 }, (_, i) => ({
      week: `S${i + 1}`,
      value: Math.floor(100 + Math.random() * 400),
    }));

    const sessions = [
      { type: 'Strength', value: 35, color: COLORS.primary },
      { type: 'Cardio', value: 25, color: COLORS.info },
      { type: 'HIIT', value: 20, color: COLORS.warning },
      { type: 'Mobility', value: 15, color: COLORS.success },
      { type: 'Recovery', value: 5, color: COLORS.muted },
    ];

    const lineData = Array.from({ length: 90 }, (_, i) => ({
      day: i + 1,
      readiness: Math.floor(50 + Math.random() * 40 + Math.sin(i / 10) * 20),
      volume: Math.floor(20 + Math.random() * 80),
      avgHr: Math.floor(60 + Math.random() * 30),
    }));

    return { readiness, weekly, sessions, lineData, days };
  };

  const mockData = useMemo(() => generateMockData(), []);

  const kpiData = {
    totalWorkouts: workouts?.length || 127,
    totalVolume: 4250,
    avgReadiness: biometrics?.readiness || 78,
    hrvTrend: 45,
  };

  if (isLoadingBiometrics || isLoadingWorkouts) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-display font-bold text-[var(--color-text)]">
          Dashboard Overview
        </h1>
        <ChartSkeleton count={4} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-[var(--color-text)]">
            Dashboard Overview
          </h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Analytics and insights for your fitness journey
          </p>
        </div>
        <div className="flex gap-2">
          <ExportButton data={mockData.readiness} filename="overview-readiness" format="csv" />
          <ChartExportButton chartRef={heatmapRef} filename="heatmap-52week" />
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-[var(--color-primary)]/10">
              <Dumbbell className="w-5 h-5 text-[var(--color-primary)]" />
            </div>
            <span className="text-sm text-[var(--color-text-muted)]">Workouts This Month</span>
          </div>
          <p className="text-3xl font-display font-bold text-[var(--color-text)]">
            {kpiData.totalWorkouts}
          </p>
          <p className="text-xs text-[var(--color-success)] mt-1">+12% vs last month</p>
        </div>

        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-[var(--color-info)]/10">
              <Zap className="w-5 h-5 text-[var(--color-info)]" />
            </div>
            <span className="text-sm text-[var(--color-text-muted)]">Total Volume (min)</span>
          </div>
          <p className="text-3xl font-display font-bold text-[var(--color-text)]">
            {kpiData.totalVolume.toLocaleString()}
          </p>
          <p className="text-xs text-[var(--color-success)] mt-1">On track</p>
        </div>

        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-[var(--color-success)]/10">
              <Heart className="w-5 h-5 text-[var(--color-success)]" />
            </div>
            <span className="text-sm text-[var(--color-text-muted)]">Avg Readiness</span>
          </div>
          <p className="text-3xl font-display font-bold text-[var(--color-text)]">
            {kpiData.avgReadiness}%
          </p>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">
            {kpiData.avgReadiness >= 80 ? 'Excellent' : kpiData.avgReadiness >= 70 ? 'Good' : 'Moderate'}
          </p>
        </div>

        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-[var(--color-warning)]/10">
              <Activity className="w-5 h-5 text-[var(--color-warning)]" />
            </div>
            <span className="text-sm text-[var(--color-text-muted)]">HRV Trend</span>
          </div>
          <p className="text-3xl font-display font-bold text-[var(--color-text)]">
            {kpiData.hrvTrend}ms
          </p>
          <p className="text-xs text-[var(--color-success)] mt-1">Stable baseline</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 52-Week Activity Heatmap */}
        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
              52-Week Activity Heatmap
            </h3>
          </div>
          <div ref={heatmapRef} className="w-full overflow-x-auto">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={mockData.weekly} layout="vertical" barSize={12}>
                <CartesianGrid stroke="var(--color-outline-variant)" strokeDasharray="3 3" />
                <XAxis 
                  type="number" 
                  tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                  stroke="var(--color-outline-variant)"
                />
                <YAxis 
                  dataKey="week" 
                  type="category" 
                  tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                  stroke="var(--color-outline-variant)"
                  width={40}
                />
                <Tooltip 
                  content={<CustomTooltip color={COLORS.primary} />}
                  cursor={{ fill: 'rgba(232, 255, 71, 0.1)' }}
                />
                <Bar dataKey="value" fill={COLORS.primary} radius={2} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-2 mt-3">
            <span className="text-xs text-[var(--color-text-muted)]">Less</span>
            {[25, 50, 75, 100].map(p => (
              <div key={p} className="w-3 h-3 rounded-sm" style={{ backgroundColor: COLORS.primary, opacity: p / 100 }} />
            ))}
            <span className="text-xs text-[var(--color-text-muted)]">More</span>
          </div>
        </div>

        {/* Training Type Pie Chart */}
        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
              Training Type Distribution
            </h3>
          </div>
          <div ref={pieRef} className="w-full">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={mockData.sessions}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="var(--color-surface-container)"
                  strokeWidth={2}
                >
                  {mockData.sessions.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend 
                  verticalAlign="bottom" 
                  height={36}
                  wrapperStyle={{
                    fontSize: '11px',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 90-Day Readiness Line Chart */}
      <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
            90-Day Readiness Trend
          </h3>
          <ChartExportButton chartRef={readinessRef} filename="readiness-90day" />
        </div>
        <div ref={readinessRef}>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={mockData.lineData} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
              <defs>
                <linearGradient id="colorReadiness" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#E8FF47" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#E8FF47" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#60A5FA" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#60A5FA" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--color-outline-variant)" strokeDasharray="3 3" vertical={false} />
              <XAxis 
                dataKey="day" 
                tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                stroke="var(--color-outline-variant)"
                label={{ value: 'Days Ago', position: 'bottom', offset: -5, style: { fill: 'var(--color-text-muted)', fontSize: 11 } }}
              />
              <YAxis 
                yAxisId="left"
                tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                stroke="var(--color-outline-variant)"
                domain={[0, 100]}
                label={{ value: 'Readiness', angle: -90, position: 'insideLeft', style: { fill: 'var(--color-text-muted)', fontSize: 11 } }}
              />
              <YAxis 
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                stroke="var(--color-outline-variant)"
                domain={[0, 100]}
                label={{ value: 'Volume', angle: 90, position: 'insideRight', style: { fill: 'var(--color-text-muted)', fontSize: 11 } }}
              />
              <Tooltip 
                content={<CustomTooltip />}
                cursor={{ stroke: 'var(--color-primary)', strokeWidth: 1 }}
              />
              <Legend 
                verticalAlign="top" 
                height={36}
                wrapperStyle={{ fontSize: '11px' }}
                iconType="line"
              />
              <Line 
                yAxisId="left"
                type="monotone" 
                dataKey="readiness" 
                stroke="#E8FF47" 
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 6, fill: '#E8FF47' }}
                name="Readiness Score"
              />
              <Line 
                yAxisId="right"
                type="monotone" 
                dataKey="volume" 
                stroke="#60A5FA" 
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 6, fill: '#60A5FA' }}
                name="Training Volume"
              />
              <Line 
                yAxisId="left"
                type="monotone" 
                dataKey="avgHr" 
                stroke="#FB923C" 
                strokeWidth={2}
                dot={false}
                name="Avg Heart Rate"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* AI Analytics Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-display font-bold text-[var(--color-text)]">
              Insights & Predicciones
            </h2>
          </div>
          <button
            onClick={refreshAnalytics}
            disabled={isLoadingAnalytics}
            className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-primary)] disabled:opacity-50"
          >
            {isLoadingAnalytics ? 'Actualizando...' : 'Actualizar'}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <ForecastWidget
              forecasts={forecast?.forecasts ?? []}
              isLoading={isLoadingAnalytics}
            />
            <PlateauAlert
              plateaus={insights?.plateaus ?? []}
              isLoading={isLoadingAnalytics}
            />
          </div>

          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-[var(--color-text-muted)]">
              Descubrimientos del mes
            </h3>
            {insights?.insights?.length ? (
              insights.insights.map((insight) => (
                <InsightCard key={insight.id} insight={insight} />
              ))
            ) : (
              <div className="rounded-xl bg-white/5 border border-white/10 p-4 text-center">
                <p className="text-sm text-[var(--color-text-muted)]">
                  {isLoadingAnalytics ? 'Cargando insights...' : 'Acumulando datos para generar insights...'}
                </p>
              </div>
            )}
            {insights?.optimal_volume?.status === 'ok' && insights.optimal_volume.optimal_volume_min != null && (
              <div className="rounded-xl bg-emerald-500/5 border border-emerald-500/20 backdrop-blur-sm p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm">🎯</span>
                  <span className="text-sm font-semibold text-emerald-400">Volumen Óptimo</span>
                </div>
                <p className="text-xs text-[var(--color-text)]">
                  {insights.optimal_volume.optimal_volume_min}-{insights.optimal_volume.optimal_volume_min + 30} min/semana
                  ({insights.optimal_volume.optimal_sessions_per_week} sesiones)
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
