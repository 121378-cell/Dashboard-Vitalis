import React from 'react';
import { Heart, Activity, Zap, Wind, Footprints, Moon, Flame, AlertCircle } from 'lucide-react';
import { Biometrics } from '../types';

interface Props {
  data: Biometrics | null;
}

export const BiometricsWidget: React.FC<Props> = ({ data }) => {
  if (!data) return <div className="p-4 text-center text-on-surface-variant">No data available</div>;

  const getMetricColor = (value: number, type: keyof Biometrics) => {
    // REQ-F10: Color coding by value
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

  const metrics = [
    { id: 'heartRate', label: 'FC', value: `${data.heartRate} bpm`, icon: Heart },
    { id: 'hrv', label: 'HRV', value: `${data.hrv} ms`, icon: Activity },
    { id: 'spo2', label: 'SpO2', value: `${data.spo2}%`, icon: Zap },
    { id: 'stress', label: 'Estrés', value: data.stress, icon: AlertCircle },
    { id: 'steps', label: 'Pasos', value: data.steps, icon: Footprints },
    { id: 'sleep', label: 'Sueño', value: `${data.sleep}h`, icon: Moon },
    { id: 'calories', label: 'Calorías', value: data.calories, icon: Flame },
    { id: 'respiration', label: 'Resp.', value: data.respiration, icon: Wind },
  ];

  return (
    <div className="space-y-4">
      {/* REQ-F14: Data source indicator */}
      <div className="flex items-center justify-between text-[10px] uppercase tracking-widest font-bold">
        <span className="text-on-surface-variant">Estado Garmin</span>
        <span className={data.source === 'garmin_api' ? 'text-green-400' : (data.source === 'cache' ? 'text-blue-400' : 'text-orange-400')}>
          {data.source === 'garmin_api' ? '🟢 REAL' : (data.source === 'cache' ? '📦 CACHÉ' : '⚙️ DEMO')}
        </span>
      </div>

      {/* REQ-F12: Readiness Progress Bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-[10px] font-bold uppercase">
          <span>Readiness Score</span>
          <span>{data.readiness}/100</span>
        </div>
        <div className="h-2 w-full bg-surface-variant rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-500 ${data.readiness >= 75 ? 'bg-green-400' : (data.readiness >= 50 ? 'bg-orange-400' : 'bg-red-400')}`}
            style={{ width: `${data.readiness}%` }}
          />
        </div>
      </div>

      {/* REQ-F13: Overtraining Alert */}
      {data.overtraining && (
        <div className="bg-red-500/10 border border-red-500/20 p-2 rounded-lg flex items-center gap-2 text-red-400 animate-pulse">
          <AlertCircle size={16} />
          <span className="text-[10px] font-bold uppercase tracking-tighter">Riesgo Sobreentrenamiento</span>
        </div>
      )}

      {/* REQ-F09: 8 Key Metrics */}
      <div className="grid grid-cols-2 gap-2">
        {metrics.map((m) => (
          <div key={m.id} className="bg-surface-container-low p-2 rounded-lg border border-outline-variant/10">
            <div className="flex items-center gap-2 mb-1">
              <m.icon size={12} className="text-on-surface-variant" />
              <span className="text-[8px] uppercase font-bold text-on-surface-variant">{m.label}</span>
            </div>
            <div className={`text-sm font-bold ${getMetricColor(data[m.id as keyof Biometrics] as number, m.id as keyof Biometrics)}`}>
              {m.value}
            </div>
          </div>
        ))}
      </div>

      {/* REQ-F11: Training Zone Badge */}
      <div className="flex items-center justify-between p-2 bg-surface-container-high rounded-lg">
        <span className="text-[10px] font-bold uppercase text-on-surface-variant">Zona Actual</span>
        <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${
          data.heartRate < 100 ? 'bg-green-500/20 text-green-400' :
          (data.heartRate < 140 ? 'bg-blue-500/20 text-blue-400' :
          (data.heartRate < 165 ? 'bg-orange-500/20 text-orange-400' : 'bg-red-500/20 text-red-400'))
        }`}>
          {data.heartRate < 100 ? 'Recovery' : (data.heartRate < 140 ? 'Aerobic' : (data.heartRate < 165 ? 'Threshold' : 'Max'))}
        </span>
      </div>
    </div>
  );
};
