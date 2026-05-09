import React, { useRef, useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts';
import { Calendar, TrendingUp, Heart, Activity, Moon } from 'lucide-react';
import { CustomTooltip } from '../components/charts/CustomTooltip';
import { ChartSkeleton } from '../components/charts/ChartSkeleton';
import { ExportButton } from '../components/common/ExportButton';
import { ChartExportButton } from '../components/common/ChartExportButton';
import { useBiometricsHistory } from '../hooks/useDashboardData';

const COLORS = {
  primary: '#E8FF47',
  success: '#4ADE80',
  warning: '#FB923C',
  danger: '#F87171',
  info: '#60A5FA',
  muted: '#6B6B8A',
  surface: '#13131A',
};

const RANGE_OPTIONS = [
  { value: 7, label: '7d' },
  { value: 30, label: '30d' },
  { value: 90, label: '90d' },
  { value: 365, label: '1y' },
];

export const BiometricsPage = () => {
  const [selectedRange, setSelectedRange] = useState(30);
  const hrvRef = useRef<HTMLDivElement>(null);
  const hrRef = useRef<HTMLDivElement>(null);
  const sleepRef = useRef<HTMLDivElement>(null);
  const stressRef = useRef<HTMLDivElement>(null);

  const { data: historyData, isLoading } = useBiometricsHistory(selectedRange);

  const displayData = historyData?.length ? historyData : [];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-display font-bold text-[var(--color-text)]">
          Biometrics
        </h1>
        <ChartSkeleton count={4} />
      </div>
    );
  }

  const rhrBaseline = displayData.length > 0
    ? Math.round(displayData.reduce((sum: number, d: any) => sum + (d.restingHr || 0), 0) / displayData.filter((d: any) => d.restingHr).length)
    : 46;

  const sleepBaseline = displayData.length > 0
    ? (displayData.reduce((sum: number, d: any) => sum + (d.sleep || 0), 0) / displayData.filter((d: any) => d.sleep).length).toFixed(1)
    : '6.2';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-[var(--color-text)]">
            Biometrics
          </h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Resting heart rate, sleep, stress, and recovery tracking
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ExportButton data={displayData} filename="biometrics" format="csv" />
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
        </div>
      </div>

      {displayData.length === 0 ? (
        <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-12 text-center">
          <Activity className="w-12 h-12 text-[var(--color-text-muted)] mx-auto mb-4" />
          <h3 className="text-lg font-display font-bold text-[var(--color-text)] mb-2">
            No biometrics data yet
          </h3>
          <p className="text-sm text-[var(--color-text-muted)]">
            Sync your Garmin device to see biometric trends
          </p>
        </div>
      ) : (
        <>
          {/* Resting Heart Rate Chart — primary since FR245 has no HRV */}
          <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-[var(--color-danger)]/20">
                  <Heart className="w-5 h-5 text-[#F87171]" />
                </div>
                <div>
                  <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                    Resting Heart Rate Trend
                  </h3>
                  <p className="text-sm text-[var(--color-text-muted)]">
                    Lower RHR generally indicates better cardiovascular fitness
                  </p>
                </div>
              </div>
              <ChartExportButton chartRef={hrRef} filename="resting-hr-trend" />
            </div>
            <div ref={hrRef}>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={displayData} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                  <defs>
                    <linearGradient id="colorHr" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#F87171" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#F87171" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
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
                    domain={['dataMin - 5', 'dataMax + 5']}
                  />
                  <Tooltip content={<CustomTooltip color="#F87171" />} />
                  <Legend
                    verticalAlign="top"
                    height={36}
                    wrapperStyle={{ fontSize: '11px' }}
                    iconType="line"
                  />
                  <ReferenceLine
                    y={rhrBaseline}
                    stroke="#6B6B8A"
                    strokeDasharray="5 5"
                    label={{ value: 'Baseline', position: 'right', fill: 'var(--color-text-muted)', fontSize: 10 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="restingHr"
                    stroke="#F87171"
                    strokeWidth={2}
                    dot={{ fill: '#F87171', strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6, strokeWidth: 2 }}
                    name="Resting HR"
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Sleep Bar Chart */}
            <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-[var(--color-info)]/20">
                    <Moon className="w-5 h-5 text-[var(--color-info)]" />
                  </div>
                  <div>
                    <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                      Sleep Duration
                    </h3>
                    <p className="text-sm text-[var(--color-text-muted)]">
                      Hours of sleep per day
                    </p>
                  </div>
                </div>
                <ChartExportButton chartRef={sleepRef} filename="sleep-bar-chart" />
              </div>
              <div ref={sleepRef}>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={displayData} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                    <defs>
                      <linearGradient id="colorSleep" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#60A5FA" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#60A5FA" stopOpacity={0.2}/>
                      </linearGradient>
                    </defs>
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
                      domain={[0, 'dataMax + 1']}
                    />
                    <Tooltip content={<CustomTooltip color="#60A5FA" />} />
                    <ReferenceLine
                      y={7}
                      stroke="#4ADE80"
                      strokeDasharray="5 5"
                      label={{ value: '7h target', position: 'right', fill: 'var(--color-text-muted)', fontSize: 10 }}
                    />
                    <Bar
                      dataKey="sleep"
                      fill="url(#colorSleep)"
                      radius={[4, 4, 0, 0]}
                      maxBarSize={50}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Stress Area Chart */}
            <div className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-[var(--color-warning)]/20">
                    <Activity className="w-5 h-5 text-[var(--color-warning)]" />
                  </div>
                  <div>
                    <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
                      Stress Level
                    </h3>
                    <p className="text-sm text-[var(--color-text-muted)]">
                      Daily stress levels over time
                    </p>
                  </div>
                </div>
                <ChartExportButton chartRef={stressRef} filename="stress-area-chart" />
              </div>
              <div ref={stressRef}>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={displayData} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                    <defs>
                      <linearGradient id="colorStress" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#FB923C" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#FB923C" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
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
                    <Tooltip content={<CustomTooltip color="#FB923C" />} />
                    <ReferenceLine
                      y={40}
                      stroke="#6B6B8A"
                      strokeDasharray="5 5"
                      label={{ value: 'Baseline', position: 'right', fill: 'var(--color-text-muted)', fontSize: 10 }}
                    />
                    <Area
                      type="monotone"
                      dataKey="stress"
                      stroke="#FB923C"
                      fill="url(#colorStress)"
                      strokeWidth={2}
                      dot={{ fill: '#FB923C', strokeWidth: 2, r: 4 }}
                      activeDot={{ r: 6, strokeWidth: 2 }}
                      name="Stress"
                      connectNulls
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
