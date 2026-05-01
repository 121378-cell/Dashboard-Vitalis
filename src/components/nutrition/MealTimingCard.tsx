import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { nutritionService } from "../../services/nutritionService";
import type { MealTiming } from "../../services/nutritionService";
import { Clock, ChevronRight, Utensils, Zap, Moon, Coffee, Apple } from "lucide-react";

const MEAL_ICONS: Record<string, React.ReactNode> = {
  breakfast: <Coffee className="w-4 h-4" />,
  lunch: <Utensils className="w-4 h-4" />,
  dinner: <Moon className="w-4 h-4" />,
  snack: <Apple className="w-4 h-4" />,
  pre_workout: <Zap className="w-4 h-4" />,
  post_workout: <Zap className="w-4 h-4" />,
};

const MEAL_COLORS: Record<string, string> = {
  breakfast: "bg-amber-100 text-amber-700 border-amber-200",
  lunch: "bg-green-100 text-green-700 border-green-200",
  dinner: "bg-indigo-100 text-indigo-700 border-indigo-200",
  snack: "bg-orange-100 text-orange-700 border-orange-200",
  pre_workout: "bg-red-100 text-red-700 border-red-200",
  post_workout: "bg-blue-100 text-blue-700 border-blue-200",
};

interface MealTimingCardProps {
  className?: string;
}

const MealTimingCard: React.FC<MealTimingCardProps> = ({ className = "" }) => {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  const { data, isLoading } = useQuery({
    queryKey: ["meal-plan"],
    queryFn: async () => {
      const { data: response } = await nutritionService.getMealPlan();
      return response.data as { date: string; goal_type: string; target_calories: number; meals: MealTiming[] };
    },
    refetchInterval: 300000,
  });

  const getNextMeal = (meals: MealTiming[]): { current: MealTiming | null; next: MealTiming | null; passed: MealTiming[] } => {
    if (!meals || meals.length === 0) return { current: null, next: null, passed: [] };

    const now = currentTime.getHours() * 60 + currentTime.getMinutes();

    const sorted = [...meals].sort((a, b) => {
      const ta = parseInt(a.time.split(":")[0]) * 60 + parseInt(a.time.split(":")[1]);
      const tb = parseInt(b.time.split(":")[0]) * 60 + parseInt(b.time.split(":")[1]);
      return ta - tb;
    });

    const passed: MealTiming[] = [];
    let current: MealTiming | null = null;
    let next: MealTiming | null = null;

    for (let i = 0; i < sorted.length; i++) {
      const mealTime = parseInt(sorted[i].time.split(":")[0]) * 60 + parseInt(sorted[i].time.split(":")[1]);
      if (mealTime <= now + 30) {
        passed.push(sorted[i]);
        if (!current && mealTime <= now + 30 && mealTime >= now - 60) {
          current = sorted[i];
        }
      } else if (!next) {
        next = sorted[i];
      }
    }

    return { current, next, passed };
  };

  const getCountdown = (nextMeal: MealTiming): string => {
    const now = currentTime;
    const [hours, minutes] = nextMeal.time.split(":").map(Number);
    const mealTime = new Date(now);
    mealTime.setHours(hours, minutes, 0, 0);

    if (mealTime <= now) {
      mealTime.setDate(mealTime.getDate() + 1);
    }

    const diffMs = mealTime.getTime() - now.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const hoursLeft = Math.floor(diffMins / 60);
    const minsLeft = diffMins % 60;

    if (hoursLeft > 0) return `${hoursLeft}h ${minsLeft}m`;
    return `${minsLeft}m`;
  };

  if (isLoading || !data) {
    return (
      <div className={`bg-white rounded-xl shadow-md p-5 ${className}`}>
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-gray-200 rounded w-1/2" />
          <div className="h-20 bg-gray-200 rounded" />
          <div className="h-20 bg-gray-200 rounded" />
        </div>
      </div>
    );
  }

  const { meals, target_calories } = data;
  const { current, next, passed } = getNextMeal(meals);

  return (
    <div className={`bg-white rounded-xl shadow-md p-5 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-800">Plan de Comidas</h3>
        <span className="text-xs text-gray-400">{target_calories} kcal/día</span>
      </div>

      {next && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3 mb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`p-1.5 rounded-lg ${MEAL_COLORS[next.type] || "bg-gray-100 text-gray-700"}`}>
                {MEAL_ICONS[next.type] || <Utensils className="w-4 h-4" />}
              </div>
              <div>
                <div className="font-semibold text-sm text-gray-800">Siguiente: {next.name}</div>
                <div className="text-xs text-gray-500">{next.calories} kcal · {next.macros.carbs_pct}C / {next.macros.protein_pct}P / {next.macros.fat_pct}G</div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-lg font-bold text-indigo-600">{getCountdown(next)}</div>
              <div className="text-xs text-gray-400">a las {next.time}</div>
            </div>
          </div>
          <p className="text-xs text-gray-600 mt-2">{next.description}</p>
          <div className="text-xs text-gray-400 mt-1 italic">Ej: {next.examples}</div>
        </div>
      )}

      <div className="relative">
        <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-200" />

        {meals.map((meal, idx) => {
          const mealTime = parseInt(meal.time.split(":")[0]) * 60 + parseInt(meal.time.split(":")[1]);
          const now = currentTime.getHours() * 60 + currentTime.getMinutes();
          const isPassed = mealTime < now;
          const isCurrent = current?.name === meal.name;

          return (
            <div key={meal.name} className="relative pl-10 pb-4">
              <div
                className={`absolute left-2 w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                  isPassed ? "bg-green-400 border-green-400" :
                  isCurrent ? "bg-indigo-400 border-indigo-400" :
                  "bg-white border-gray-300"
                }`}
              >
                {(isPassed || isCurrent) && <div className="w-2 h-2 rounded-full bg-white" />}
              </div>

              <div className={`rounded-lg border p-3 ${
                isPassed ? "bg-gray-50 border-gray-200 opacity-75" :
                isCurrent ? "bg-indigo-50 border-indigo-200" :
                "bg-white border-gray-200"
              }`}>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`p-1.5 rounded-lg ${MEAL_COLORS[meal.type] || "bg-gray-100 text-gray-700"}`}>
                      {MEAL_ICONS[meal.type] || <Utensils className="w-3 h-3" />}
                    </div>
                    <div>
                      <div className={`font-semibold text-sm ${isPassed ? "text-gray-500 line-through" : "text-gray-800"}`}>
                        {meal.name}
                      </div>
                      <div className="text-xs text-gray-400">{meal.time}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-sm font-bold ${isPassed ? "text-gray-400" : "text-gray-800"}`}>
                      {meal.calories} kcal
                    </div>
                    <div className="text-xs text-gray-400">
                      {meal.macros.protein_pct}P / {meal.macros.carbs_pct}C / {meal.macros.fat_pct}G
                    </div>
                  </div>
                </div>
                {isCurrent && !isPassed && (
                  <div className="mt-2 pt-2 border-t border-indigo-200">
                    <p className="text-xs text-indigo-700">{meal.description}</p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MealTimingCard;