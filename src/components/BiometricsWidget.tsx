import React from 'react';
import { Heart, Activity, Zap, Wind, Footprints, Moon, Flame, AlertCircle, ArrowUp, ArrowDown, Clock, Dumbbell } from 'lucide-react';
import { Biometrics } from '../types';

// Helper function to safely display values
function displayValue(value: any, decimals: number = 0, fallback: string = "N/D"): string {
  if (value === null || value === undefined || value === 0 || isNaN(Number(value))) {
    return fallback;
  }
  return decimals > 0 ? Number(value).toFixed(decimals) : String(Math.round(Number(value)));
}

interface Props {
  data: Biometrics | null;
  userId?: string;
}

export const BiometricsWidget: React.FC<Props> = ({ data, userId = 'default_user' }) => {
  if (!data) return <div className="p-4 text-center text-on-surface-variant">No data available</div>;

  const getMetricColor = (value: number, type: string) => {
    switch (type) {
      case 'heartRate':
        return value < 100 ? 'text-green-400' : (value < 165 ? 'text-orange-400' : 'text-red-400');
      case 'hrv':
        return value >= 55 ? 'text-green-400' : (value >= 30 ? 'text-orange-400' : 'text-red-400');
      case 'spo2':
        return value >= 95 ? 'text-green-400' : 'text-red-400';
      case 'stress':
        return value < 45 ? 'text-green-400' : (value < 70 ? 'text-orange-400' : 'text-red-400');
      case 'sleep':
        return value >= 7 ? 'text-green-400' : (value >= 6 ? 'text-orange-400' : 'text-red-400');
      default:
        return 'text-on-surface';
    }
  };

  const renderTrend = (current: number, baseline: number | undefined, lowIsBetter: boolean = false) => {
    if (!baseline || baseline === 0) return null;
    const diff = current - baseline;
    const isGood = lowIsBetter ? diff < 0 : diff > 0;
    const Icon = diff > 0 ? ArrowUp : ArrowDown;
    
    if (Math.abs(diff) < 1) return null;

    return (
      <span className={`flex items-center text-[8px] font-bold ml-1 ${isGood ? 'text-green-400' : 'text-red-400'}`}>
        <Icon size={8} />
        {Math.abs(Math.round(diff))}
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {/* REQ-F14: Data source indicator */}
      <div className="flex items-center justify-between text-[10px] uppercase tracking-widest font-bold">
        <span className="text-on-surface-variant">Vitalis Coach Core</span>
        <span className={
          data.source === 'garmin_api' ? 'text-green-400' : 
          data.source === 'garmin' ? 'text-green-400' : 
          data.source === 'cache' ? 'text-blue-400' : 
          data.source === 'none' ? 'text-gray-500' : 
          'text-orange-400'
        }>
          {data.source === 'garmin_api' ? '🟢 REAL' : 
           data.source === 'garmin' ? '🟢 REAL' : 
           data.source === 'cache' ? '📦 CACHÉ' : 
           data.source === 'none' ? '⭕ SIN DATOS' : 
           '⚙️ DEMO'}
        </span>
      </div>

      {/* Advanced Status Badges */}
      <div className="flex flex-wrap gap-2">
        {data.training_status && (
          <div className="bg-primary/10 border border-primary/20 px-2 py-1 rounded-md flex items-center gap-1.5">
            <Dumbbell size={10} className="text-primary" />
            <span className="text-[9px] font-bold uppercase text-primary">{data.training_status}</span>
          </div>
        )}
        {data.recovery_time !== undefined && data.recovery_time > 0 && (
          <div className="bg-orange-500/10 border border-orange-500/20 px-2 py-1 rounded-md flex items-center gap-1.5">
            <Clock size={10} className="text-orange-400" />
            <span className="text-[9px] font-bold uppercase text-orange-400">Recuperación: {data.recovery_time}h</span>
          </div>
        )}
      </div>

      {/* REQ-F12: Readiness Score with Trend Insight */}
      <div className="space-y-1.5 bg-surface-container-high/40 p-3 rounded-xl border border-outline-variant/10">
        <div className="flex justify-between items-center mb-1">
          <div className="flex flex-col">
            <span className="text-[10px] font-bold uppercase text-on-surface-variant tracking-tighter">Readiness Score</span>
            <span className={`text-xs font-black uppercase ${
              data.readiness >= 75 ? 'text-green-400' : (data.readiness >= 50 ? 'text-orange-400' : 'text-red-400')
            }`}>
              {data.status || 'Good'}
            </span>
          </div>
          <span className="text-2xl font-black">{data.readiness}</span>
        </div>
        <div className="h-1.5 w-full bg-surface-variant/30 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-700 ease-out ${
              data.readiness >= 75 ? 'bg-green-400' : (data.readiness >= 50 ? 'bg-orange-400' : 'bg-red-400')
            }`}
            style={{ width: `${data.readiness}%` }}
          />
        </div>
      </div>

      {/* REQ-F13: Overtraining Alert */}
      {data.overtraining && (
        <div className="bg-red-500/10 border border-red-500/20 p-2 rounded-lg flex items-center gap-2 text-red-400 animate-pulse">
          <AlertCircle size={16} />
          <span className="text-[10px] font-bold uppercase tracking-tighter">Aviso: Posible Fatiga Acumulada</span>
        </div>
      )}

      {/* 8 Key Metrics Grid with Trends */}
      <div className="grid grid-cols-2 gap-2">
        <MetricCard icon={Heart} label="FC Reposo" value={displayValue(data.heartRate, 0, "--")} unit="bpm" color={getMetricColor(Number(data.heartRate) || 0, 'heartRate')}>
          {renderTrend(Number(data.heartRate) || 0, data.rhr_baseline, true)}
        </MetricCard>
        
        <MetricCard icon={Activity} label="HRV" value={displayValue(data.hrv, 0, "N/D")} unit="ms" color={getMetricColor(Number(data.hrv) || 0, 'hrv')}>
          {renderTrend(Number(data.hrv) || 0, data.hrv_baseline)}
        </MetricCard>

        <MetricCard icon={Moon} label="Sueño" value={displayValue(data.sleep, 1, "N/D")} unit="h" color={getMetricColor(Number(data.sleep) || 0, 'sleep')} />
        <MetricCard icon={AlertCircle} label="Estrés" value={displayValue(data.stress, 0, "N/D")} unit="" color={getMetricColor(Number(data.stress) || 0, 'stress')} />
        
        <MetricCard icon={Zap} label="SpO2" value={displayValue(data.spo2, 0, "N/D")} unit="%" color={getMetricColor(Number(data.spo2) || 0, 'spo2')} />
        <MetricCard icon={Footprints} label="Pasos" value={displayValue(data.steps, 0, "N/D")} unit="" color="text-on-surface" />
        
        <MetricCard icon={Flame} label="Calorías" value={displayValue(data.calories, 0, "N/D")} unit="kcal" color="text-on-surface" />
        <MetricCard icon={Wind} label="Respiración" value={displayValue(data.respiration, 0, "N/D")} unit="rpm" color="text-on-surface" />
      </div>
    </div>
  );
};

const MetricCard: React.FC<{ 
  icon: any, 
  label: string, 
  value: string | number, 
  unit: string, 
  color: string,
  children?: React.ReactNode 
}> = ({ icon: Icon, label, value, unit, color, children }) => (
  <div className="bg-surface-container-low/50 p-2.5 rounded-xl border border-outline-variant/5 hover:border-outline-variant/20 transition-colors">
    <div className="flex items-center gap-1.5 mb-1 opacity-70">
      <Icon size={11} className="text-on-surface-variant" />
      <span className="text-[9px] uppercase font-black text-on-surface-variant tracking-tight">{label}</span>
    </div>
    <div className="flex items-baseline gap-0.5">
      <span className={`text-sm font-black ${color}`}>{value}</span>
      <span className="text-[8px] font-bold text-on-surface-variant ml-0.5">{unit}</span>
      {children}
    </div>
  </div>
);
