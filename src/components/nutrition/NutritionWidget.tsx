import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { nutritionService } from "../../services/nutritionService";
import type { NutritionToday } from "../../services/nutritionService";
import { Flame, Drumstick, Wheat, Droplets, Zap, Footprints } from "lucide-react";

interface NutritionWidgetProps {
  compact?: boolean;
  className?: string;
}

const CircularProgress: React.FC<{
  value: number;
  max: number;
  color: string;
  bgColor: string;
  size?: number;
  strokeWidth?: number;
  label?: string;
  unit?: string;
}> = ({ value, max, color, bgColor, size = 48, strokeWidth = 4, label, unit }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(100, (value / max) * 100);
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={bgColor} strokeWidth={strokeWidth} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.5s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-bold text-gray-700">{Math.round(pct)}%</span>
        </div>
      </div>
      {label && <span className="text-xs text-gray-500 mt-1">{label}</span>}
    </div>
  );
};

const NutritionWidget: React.FC<NutritionWidgetProps> = ({ compact = false, className = "" }) => {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["nutrition-today"],
    queryFn: async () => {
      const { data: response } = await nutritionService.getToday();
      return response.data as NutritionToday;
    },
    refetchInterval: 60000 * 5,
    staleTime: 60000,
  });

  if (isLoading) {
    return (
      <div className={`bg-white rounded-xl shadow-md p-4 ${className}`}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-200 rounded w-2/3" />
          <div className="h-4 bg-gray-200 rounded w-1/2" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={`bg-white rounded-xl shadow-md p-4 ${className}`}>
        <p className="text-sm text-red-500">Error cargando nutrición</p>
        <button onClick={() => refetch()} className="text-xs text-indigo-600 underline mt-1">Reintentar</button>
      </div>
    );
  }

  const { target, consumed, remaining, steps, steps_source, workout_calories, neat_calories, eat_calories } = data;

  if (compact) {
    return (
      <div className={`bg-white rounded-xl shadow-md p-3 ${className}`}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-gray-500">NUTRICIÓN</span>
          <span className={`text-xs px-1.5 py-0.5 rounded ${
            data.goal_type === "cut" ? "bg-red-100 text-red-700" :
            data.goal_type === "bulk" ? "bg-green-100 text-green-700" :
            "bg-blue-100 text-blue-700"
          }`}>
            {data.goal_type === "cut" ? "Corte" : data.goal_type === "bulk" ? "Volumen" : "Recomp"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <CircularProgress value={consumed.calories} max={target.calories} color="#ef4444" bgColor="#fee2e2" size={36} strokeWidth={3} />
          <div className="flex-1">
            <div className="text-xs font-medium text-gray-800">{consumed.calories} / {target.calories} kcal</div>
            <div className="text-xs text-gray-400">
              {consumed.protein_g.toFixed(0)}g proteína
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-xl shadow-md p-5 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-800">Nutrición</h3>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-1 rounded font-medium ${
            data.goal_type === "cut" ? "bg-red-100 text-red-700" :
            data.goal_type === "bulk" ? "bg-green-100 text-green-700" :
            "bg-blue-100 text-blue-700"
          }`}>
            {data.goal_type === "cut" ? "Corte" : data.goal_type === "bulk" ? "Volumen" : "Recomp"}
          </span>
          {steps_source === "estimated" && (
            <span className="text-xs text-gray-400" title="Pasos estimados">~{steps.toLocaleString()}</span>
          )}
        </div>
      </div>

      <div className="flex justify-around mb-4">
        <CircularProgress value={consumed.calories} max={target.calories} color="#ef4444" bgColor="#fee2e2" size={64} strokeWidth={5} label="Calorías" unit="kcal" />
        <CircularProgress value={consumed.protein_g} max={target.protein_g} color="#8b5cf6" bgColor="#ede9fe" size={64} strokeWidth={5} label="Proteína" unit="g" />
        <CircularProgress value={consumed.carbs_g} max={target.carbs_g} color="#f59e0b" bgColor="#fef3c7" size={64} strokeWidth={5} label="Carbos" unit="g" />
        <CircularProgress value={consumed.fat_g} max={target.fat_g} color="#06b6d4" bgColor="#cffafe" size={64} strokeWidth={5} label="Grasa" unit="g" />
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-gray-50 rounded-lg p-2">
          <div className="flex items-center gap-1 text-gray-500 mb-1">
            <Flame className="w-3 h-3" /> Consumido
          </div>
          <div className="font-semibold text-gray-800">{consumed.calories} kcal</div>
          <div className="text-gray-400 text-xs">
            P {consumed.protein_g.toFixed(0)}g · C {consumed.carbs_g.toFixed(0)}g · G {consumed.fat_g.toFixed(0)}g
          </div>
        </div>
        <div className="bg-gray-50 rounded-lg p-2">
          <div className="flex items-center gap-1 text-gray-500 mb-1">
            <Zap className="w-3 h-3" /> Restante
          </div>
          <div className="font-semibold text-gray-800">{remaining.calories} kcal</div>
          <div className="text-gray-400 text-xs">
            P {remaining.protein_g.toFixed(0)}g · C {remaining.carbs_g.toFixed(0)}g · G {remaining.fat_g.toFixed(0)}g
          </div>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-gray-100 grid grid-cols-3 gap-2 text-xs text-gray-500">
        <div className="flex items-center gap-1">
          <Footprints className="w-3 h-3 text-blue-400" />
          <span>{steps.toLocaleString()} pasos</span>
        </div>
        {workout_calories > 0 && (
          <div className="flex items-center gap-1">
            <Flame className="w-3 h-3 text-orange-400" />
            <span>+{workout_calories} kcal entreno</span>
          </div>
        )}
        <div className="flex items-center gap-1">
          <Droplets className="w-3 h-3 text-cyan-400" />
          <span>{(data as any).hydration_target_ml || 0}ml</span>
        </div>
      </div>
    </div>
  );
};

export default NutritionWidget;