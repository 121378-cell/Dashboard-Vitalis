import React from 'react';

export interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: any;
  labelFormatter?: (value: any) => string;
  color?: string;
}

export const CustomTooltip = ({
  active,
  payload,
  label,
  labelFormatter,
  color = '#E8FF47',
}: CustomTooltipProps) => {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-lg border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)]/95 backdrop-blur-md shadow-xl p-3 min-w-[160px]">
      <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--color-on-surface-variant)] mb-2">
        {labelFormatter ? labelFormatter(label) : label}
      </p>
      <div className="space-y-1.5">
        {(payload || []).map((entry: any, index: number) => {
          const entryColor = (entry.color as string) || color;
          return (
            <div key={index} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: entryColor }}
                />
                <span className="text-sm font-medium text-[var(--color-text)]">
                  {entry.name}
                </span>
              </div>
              <span
                className="font-mono text-sm font-bold"
                style={{ color: entryColor }}
              >
                {typeof entry.value === 'number'
                  ? entry.value.toLocaleString(undefined, {
                      minimumFractionDigits: 1,
                      maximumFractionDigits: 1,
                    })
                  : entry.value}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
