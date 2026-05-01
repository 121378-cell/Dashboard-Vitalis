import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { nutritionService } from "../../services/nutritionService";
import { Droplets, Plus, AlertTriangle, Check } from "lucide-react";

interface HydrationTrackerProps {
  className?: string;
  compact?: boolean;
}

const HydrationTracker: React.FC<HydrationTrackerProps> = ({ className = "", compact = false }) => {
  const queryClient = useQueryClient();
  const [bedtimeWarningDismissed, setBedtimeWarningDismissed] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["hydration-status"],
    queryFn: async () => {
      const { data: response } = await nutritionService.getHydrationStatus();
      return response.data;
    },
    refetchInterval: 120000,
  });

  const logWaterMutation = useMutation({
    mutationFn: (glasses: number) => nutritionService.logWater(glasses),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["hydration-status"] });
      queryClient.invalidateQueries({ queryKey: ["nutrition-today"] });
    },
  });

  const handleTapGlass = () => {
    logWaterMutation.mutate(1);
  };

  const getBedtimeWarning = (): string | null => {
    if (bedtimeWarningDismissed) return null;

    const now = new Date();
    const bedtime = new Date(now);
    bedtime.setHours(22, 0, 0, 0);

    if (now >= bedtime) return null;

    const hoursUntilBedtime = (bedtime.getTime() - now.getTime()) / (1000 * 60 * 60);

    if (hoursUntilBedtime <= 2 && data && data.progress_pct < 80) {
      return `Quedan ${Math.round(hoursUntilBedtime * 60)} min para dormir. Hidratación al ${data.progress_pct}% — aún te faltan ${data.glasses_remaining} vasos.`;
    }
    return null;
  };

  const bedtimeWarning = getBedtimeWarning();

  if (isLoading || !data) {
    return (
      <div className={`bg-white rounded-xl shadow-md p-4 ${className}`}>
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-gray-200 rounded w-1/2" />
          <div className="h-12 bg-gray-200 rounded" />
        </div>
      </div>
    );
  }

  const { water_glasses, hydration_ml, target_ml, progress_pct, glasses_remaining } = data;

  if (compact) {
    return (
      <div className={`bg-white rounded-xl shadow-md p-3 ${className}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Droplets className="w-5 h-5 text-blue-400" />
            <span className="text-sm font-medium text-gray-700">
              {water_glasses} / {Math.round(target_ml / 250)} vasos
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={handleTapGlass}
              disabled={logWaterMutation.isPending}
              className="p-1.5 bg-blue-100 hover:bg-blue-200 rounded-lg transition-colors disabled:opacity-50"
            >
              <Plus className="w-3 h-3 text-blue-600" />
            </button>
          </div>
        </div>
        <div className="mt-2 w-full bg-gray-100 rounded-full h-1.5">
          <div
            className="bg-blue-400 h-1.5 rounded-full transition-all"
            style={{ width: `${Math.min(100, progress_pct)}%` }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-xl shadow-md p-5 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Droplets className="w-5 h-5 text-blue-400" />
          <h3 className="text-base font-bold text-gray-800">Hidratación</h3>
        </div>
        <span className="text-sm font-medium text-blue-600">
          {Math.round(progress_pct)}%
        </span>
      </div>

      <div className="flex items-center justify-center gap-2 mb-3">
        {Array.from({ length: Math.min(10, Math.ceil(target_ml / 250)) }).map((_, i) => (
          <button
            key={i}
            onClick={handleTapGlass}
            disabled={logWaterMutation.isPending || i >= water_glasses}
            className={`w-10 h-10 rounded-full border-2 flex items-center justify-center transition-all ${
              i < water_glasses
                ? "bg-blue-400 border-blue-400 text-white"
                : i === water_glasses
                ? "border-blue-300 bg-blue-50 hover:bg-blue-100 hover:border-blue-400 cursor-pointer"
                : "border-gray-200 bg-gray-50 cursor-default"
            }`}
          >
            {i < water_glasses ? (
              <Check className="w-4 h-4" />
            ) : (
              <Droplets className="w-3 h-3 text-gray-300" />
            )}
          </button>
        ))}
      </div>

      <div className="text-center mb-3">
        <span className="text-2xl font-bold text-gray-800">{hydration_ml}ml</span>
        <span className="text-sm text-gray-400"> / {target_ml}ml</span>
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleTapGlass}
          disabled={logWaterMutation.isPending}
          className="flex-1 flex items-center justify-center gap-1.5 bg-blue-500 hover:bg-blue-600 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          <Plus className="w-4 h-4" />
          {logWaterMutation.isPending ? "Añadiendo..." : "Añadir vaso"}
        </button>
        {water_glasses > 0 && (
          <button
            onClick={() => logWaterMutation.mutate(-water_glasses)}
            className="bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-2 rounded-lg text-sm transition-colors"
          >
            Reset
          </button>
        )}
      </div>

      {glasses_remaining > 0 && (
        <div className="mt-3 text-xs text-gray-400 text-center">
          {glasses_remaining} vasos remaining to reach goal
        </div>
      )}

      {bedtimeWarning && (
        <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-800">{bedtimeWarning}</p>
            <button
              onClick={() => setBedtimeWarningDismissed(true)}
              className="text-amber-600 hover:text-amber-800 ml-auto"
            >
              <span className="text-xs underline">Dismiss</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default HydrationTracker;