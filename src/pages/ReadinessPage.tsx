import React, { useRef, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, BarChart, Bar, Cell
} from 'recharts';
import { Activity, Heart, TrendingUp, AlertCircle } from 'lucide-react';
import { CustomTooltip } from '../components/charts/CustomTooltip';
import { ChartSkeleton } from '../components/charts/ChartSkeleton';
import { ExportButton } from '../components/common/ExportButton';
import { ChartExportButton } from '../components/common/ChartExportButton';
import {
  useReadinessTrend, useReadinessForecast, useBiometrics,
  useDailyReadinessHistory, useDailyReadiness
} from '../hooks/useDashboardData';
import { useAnalytics } from '../hooks/useAnalytics';

const COLORS = {
  primary: '#E8FF47',
  success: '#4ADE80',
  warning: '#FB923C',
  danger: '#F87171',
  info: '#60A5FA',
  muted: '#6B6B8A',
};

const RANGE_OPTIONS = [
  { value: 7, label: '7d' },
  { value: 30, label: '30d' },
  { value: 90, label: '90d' },
];

export const ReadinessPage = () => {
  const [selectedRange, setSelectedRange] = useState(30);
  const trendRef = useRef<HTMLDivElement>(null);
  const forecastRef = useRef<HTMLDivElement>(null);

  const { data: trendData, isLoading: isLoadingTrend } = useReadinessTrend(selectedRange);
  const { data: forecastData, isLoading: isLoadingForecast } = useReadinessForecast(3);
  const { data: biometrics } = useBiometrics();
  const { data: dailyStatus } = useDailyReadiness();
  const { data: dailyHistory } = useDailyReadinessHistory(selectedRange);
  const { correlations } = useAnalytics();

  const isLoading = isLoadingTrend || isLoadingForecast;

  const displayTrend = trendData?.length ? trendData :
    dailyHistory?.length ? dailyHistory.map((d: any) => ({
      date: d.date,
      score: d.readiness_score,
      status: d.readiness_category?.toLowerCase() || 'moderate',
      overtraining_risk: d.readiness_score < 40,
    })) : [];

  const displayForecast = forecastData?.length ? forecastData : [];

  const currentReadiness = biometrics?.readiness || dailyStatus?.readiness_score || null;
  const currentStatus = biometrics?.status || (dailyStatus?.readiness_category?.toLowerCase()) || null;

  const overtrainingRisk = trendData?.some((d: any) => d.overtraining_risk) ||
    dailyHistory?.some((d: any) => d.readiness_score < 40) || false;

  const sevenDayAvg = displayTrend.length >= 7
    ? Math.round(displayTrend.slice(-7).reduce((sum: number, d: any) => sum + (d.score || 0), 0) / 7)
    : currentReadiness;

  const readinessFactors = dailyStatus?.components
    ? [
        { factor: 'Body Battery', impact: (dailyStatus.components.body_battery?.score ?? 50) - 50, value: dailyStatus.components.body_battery?.score ?? 0 },
        { factor: 'Sleep', impact: (dailyStatus.components.sleep?.score ?? 50) - 50, value: dailyStatus.components.sleep?.score ?? 0 },
        { factor: 'Stress', impact: -((dailyStatus.components.stress?.score ?? 50) - 50), value: dailyStatus.components.stress?.score ?? 0 },
        { factor: 'RHR', impact: (dailyStatus.components.resting_hr?.score ?? 50) - 50, value: dailyStatus.components.resting_hr?.score ?? 0 },
      ]
    : [];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-display font-bold text-[var(--color-text)]">
          Readiness Dashboard
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
            Readiness Dashboard
          </h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Recovery insights and performance readiness tracking
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-1">
            {RANGE_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => setSelectedRange(option.value)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  selectedRange === option.value
                    ? 'bg-[var(--color-primary)]/20 text-[var(--color-primary)]'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
          <ExportButton data={displayTrend} filename="readiness-trend" format="csv" />
        </div>
      </div>

      {/* Current Readiness Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="w-16 h-16 rounded-full border-4 flex items-center justify-center"
                style={{
                  borderColor: currentStatus === 'excellent' || currentStatus === 'optimo' ? COLORS.success :
                    currentStatus === 'good' || currentStatus === 'bueno' ? COLORS.primary :
                    currentStatus === 'moderate' || currentStatus === 'moderado' ? COLORS.warning : COLORS.danger,
                  backgroundColor: 'var(--color-surface-container)',
                }}>
                <span className="text-2xl font-display font-bold"
                  style={{ color: currentStatus === 'excellent' || currentStatus === 'optimo' ? COLORS.success :
                    currentStatus === 'good' || currentStatus === 'bueno' ? COLORS.primary :
                    currentStatus === 'moderate' || currentStatus === 'moderado' ? COLORS.warning : COLORS.danger }}>
                  {currentReadiness ?? '—'}%
                </span>
              </div>
            </div>
            <div>
              <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                Current Readiness
              </h3>
              <p className="text-sm text-[var(--color-text-muted)]">
                {currentReadiness == null ? 'No data available' :
                  currentStatus === 'excellent' || currentStatus === 'optimo' ? 'Peak performance ready' :
                  currentStatus === 'good' || currentStatus === 'bueno' ? 'Good to train' :
                  currentStatus === 'moderate' || currentStatus === 'moderado' ? 'Moderate training' : 'Rest recommended'}
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-lg bg-[var(--color-warning)]/20">
              <AlertCircle className="w-6 h-6 text-[var(--color-warning)]" />
            </div>
            <div>
              <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                Overtraining Risk
              </h3>
              <p className={`text-sm ${overtrainingRisk ? 'text-[var(--color-danger)]' : 'text-[var(--color-success)]'}`}>
                {overtrainingRisk ? 'Elevated - Monitor closely' : 'Low - Normal levels'}
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-lg bg-[var(--color-primary)]/20">
              <TrendingUp className="w-6 h-6 text-[var(--color-primary)]" />
            </div>
            <div>
              <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                7-Day Average
              </h3>
              <p className="text-2xl font-display font-bold text-[var(--color-primary)]">
                {sevenDayAvg ?? '—'}%
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Readiness Trend */}
      <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[var(--color-primary)]/20">
              <Activity className="w-5 h-5 text-[var(--color-primary)]" />
            </div>
            <div>
              <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                Readiness Trend
              </h3>
              <p className="text-sm text-[var(--color-text-muted)]">
                {selectedRange}-day history
              </p>
            </div>
          </div>
          <ChartExportButton chartRef={trendRef} filename="readiness-trend" />
        </div>
        {displayTrend.length > 0 ? (
          <div ref={trendRef}>
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={displayTrend} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                <defs>
                  <linearGradient id="colorReadinessTrend" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#E8FF47" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#E8FF47" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--color-outline-variant)" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                  stroke="var(--color-text-muted)"
                  tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                  stroke="var(--color-outline-variant)"
                  domain={[0, 100]}
                />
                <Tooltip content={<CustomTooltip color="#E8FF47" />} />
                <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '11px' }} />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#E8FF47"
                  strokeWidth={2.5}
                  fill="url(#colorReadinessTrend)"
                  dot={{ fill: '#E8FF47', strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6, fill: '#E8FF47', stroke: '#0A0A0F', strokeWidth: 2 }}
                  name="Readiness Score"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-[350px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
            No readiness trend data available yet. Run the daily loop to generate scores.
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Readiness Forecast */}
        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-[var(--color-success)]/20">
                <TrendingUp className="w-5 h-5 text-[var(--color-success)]" />
              </div>
              <div>
                <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                  Readiness Forecast
                </h3>
                <p className="text-sm text-[var(--color-text-muted)]">
                  Next 3 days prediction
                </p>
              </div>
            </div>
            <ChartExportButton chartRef={forecastRef} filename="readiness-forecast" />
          </div>
          {displayForecast.length > 0 ? (
            <>
              <div ref={forecastRef}>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={displayForecast} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                    <CartesianGrid stroke="var(--color-outline-variant)" strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                      stroke="var(--color-outline-variant)"
                      tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                      stroke="var(--color-outline-variant)"
                      domain={[0, 100]}
                    />
                    <Tooltip content={<CustomTooltip color="#4ADE80" />} />
                    <Bar
                      dataKey="score"
                      radius={[4, 4, 0, 0]}
                    >
                      {displayForecast.map((entry: any, index: number) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.score >= 70 ? '#4ADE80' : entry.score >= 50 ? '#FB923C' : '#F87171'}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 space-y-2">
                {displayForecast.map((day: any, i: number) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-[var(--color-text-muted)]">
                      {new Date(day.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                    </span>
                    <span className="font-medium" style={{ color: day.score >= 70 ? COLORS.success : day.score >= 50 ? COLORS.warning : COLORS.danger }}>
                      {day.score}%{day.confidence ? ` (${Math.round(day.confidence * 100)}%)` : ''}
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
              No forecast data available yet
            </div>
          )}
        </div>

        {/* Factors Affecting Readiness */}
        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-[var(--color-warning)]/20">
                <Heart className="w-5 h-5 text-[var(--color-warning)]" />
              </div>
              <div>
                <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                  Factors Affecting Readiness
                </h3>
                <p className="text-sm text-[var(--color-text-muted)]">
                  Impact analysis of readiness components
                </p>
              </div>
            </div>
          </div>
          {readinessFactors.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={readinessFactors} layout="vertical" margin={{ top: 20, right: 30, left: 120, bottom: 20 }}>
                <CartesianGrid stroke="var(--color-outline-variant)" strokeDasharray="3 3" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                  stroke="var(--color-outline-variant)"
                  domain={[-30, 30]}
                />
                <YAxis
                  dataKey="factor"
                  type="category"
                  tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                  stroke="var(--color-outline-variant)"
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="impact" fill="#E8FF47" radius={[0, 4, 4, 0]}>
                  {readinessFactors.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.impact > 0 ? '#4ADE80' : entry.impact < 0 ? '#F87171' : '#6B6B8A'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
              Run the daily loop to see readiness factor analysis
            </div>
          )}
        </div>
      </div>

      {/* Overtraining Alerts */}
      <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[var(--color-danger)]/20">
              <AlertCircle className="w-5 h-5 text-[var(--color-danger)]" />
            </div>
            <div>
              <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                Overtraining Alerts
              </h3>
              <p className="text-sm text-[var(--color-text-muted)]">
                Monitoring for overtraining signs
              </p>
            </div>
          </div>
        </div>
        <div className="space-y-3">
          {displayTrend.slice(-7).filter((d: any) => d.overtraining_risk || d.score < 40).map((day: any, i: number) => (
            <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-[var(--color-danger)]/10 border border-[var(--color-danger)]/20">
              <AlertCircle className="w-5 h-5 text-[var(--color-danger)] flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-[var(--color-text)]">
                  Potential overtraining risk on {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </p>
                <p className="text-xs text-[var(--color-text-muted)]">
                  Readiness score: {day.score}% - Consider rest or active recovery
                </p>
              </div>
            </div>
          ))}
          {displayTrend.slice(-7).filter((d: any) => d.overtraining_risk || d.score < 40).length === 0 && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-[var(--color-success)]/10 border border-[var(--color-success)]/20">
              <Activity className="w-5 h-5 text-[var(--color-success)] flex-shrink-0" />
              <p className="text-sm text-[var(--color-success)]">
                No overtraining alerts detected. Training load appears well-managed.
              </p>
            </div>
          )}
          {displayTrend.length === 0 && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/10">
              <p className="text-sm text-[var(--color-text-muted)]">
                No data available for overtraining analysis
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
