import React from 'react';

interface ZoneProps {
  zones: { z1: number; z2: number; z3: number; z4: number; z5: number };
}

export const HeartRateZoneChart: React.FC<ZoneProps> = ({ zones }) => {
  const total = zones.z1 + zones.z2 + zones.z3 + zones.z4 + zones.z5;
  if (total === 0) return null;

  const zoneData = [
    { label: 'Z1', value: zones.z1, color: 'bg-green-500' },
    { label: 'Z2', value: zones.z2, color: 'bg-blue-500' },
    { label: 'Z3', value: zones.z3, color: 'bg-yellow-500' },
    { label: 'Z4', value: zones.z4, color: 'bg-orange-500' },
    { label: 'Z5', value: zones.z5, color: 'bg-red-500' },
  ];

  return (
    <div className="space-y-2 mt-4 bg-surface-container-low/30 p-3 rounded-xl border border-outline-variant/10">
      <h4 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Distribución de Zonas (FC)</h4>
      <div className="flex items-end gap-1 h-12">
        {zoneData.map((z) => (
          <div key={z.label} className="flex-1 flex flex-col items-center gap-1 group">
            <div 
              className={`w-full rounded-t-sm ${z.color} transition-all duration-500`}
              style={{ height: `${(z.value / total) * 100}%` }}
            />
            <span className="text-[8px] font-bold opacity-60">{z.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
