import React from 'react';
import Skeleton from 'react-loading-skeleton';
import 'react-loading-skeleton/dist/skeleton.css';

interface ChartSkeletonProps {
  height?: number;
  count?: number;
}

export const ChartSkeleton = ({ height = 300, count = 1 }: ChartSkeletonProps) => {
  return (
    <div className="w-full space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-4">
          <Skeleton
            height={height}
            baseColor="var(--color-surface)"
            highlightColor="var(--color-surface-high)"
            borderRadius={8}
            enableAnimation
          />
        </div>
      ))}
    </div>
  );
};
