import api from "./api";

export interface NutritionSettings {
  goal_type: string;
  weight_kg: number | null;
  height_cm: number | null;
  age: number | null;
  gender: string;
  activity_multiplier: number;
  protein_per_kg: number;
  fat_per_kg: number;
  calorie_adjustment: number;
}

export interface MealTiming {
  name: string;
  time: string;
  type: string;
  calories: number;
  macros: { carbs_pct: number; protein_pct: number; fat_pct: number };
  description: string;
  examples: string;
}

export interface NutritionTarget {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface ConsumedNutrition {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  meals_logged: number;
  meal_details: MealDetail[];
}

export interface MealDetail {
  id: number;
  name: string;
  type: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface NutritionToday {
  date: string;
  goal_type: string;
  target: NutritionTarget;
  consumed: ConsumedNutrition;
  remaining: NutritionTarget;
  bmr: number;
  tdee: number;
  neat_calories: number;
  eat_calories: number;
  steps: number;
  steps_source: string;
  workout_calories: number;
  hydration_target_ml: number;
  meals: MealTiming[];
}

export interface NutritionDaily {
  target_calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  hydration_ml: number;
  bmr: number;
  neat_calories: number;
  eat_calories: number;
  tdee: number;
  steps_source: string;
  steps: number;
  workout_calories: number;
  goal_type: string;
  meals: MealTiming[];
}

export interface NutritionHistoryEntry {
  date: string;
  target_calories: number;
  consumed_calories: number;
  target_protein_g: number;
  consumed_protein_g: number;
  target_carbs_g: number;
  consumed_carbs_g: number;
  target_fat_g: number;
  consumed_fat_g: number;
  steps: number;
  steps_source: string;
  workout_calories: number;
  hydration_ml: number;
  water_glasses: number;
}

export interface HydrationStatus {
  water_glasses: number;
  hydration_ml: number;
  target_ml: number;
  progress_pct: number;
  glasses_remaining: number;
}

export const nutritionService = {
  getDailyNeeds: (targetDate?: string) =>
    api.get<{ status: string; data: NutritionDaily }>("/nutrition/daily", { params: targetDate ? { target_date: targetDate } : undefined }),

  getToday: () =>
    api.get<{ status: string; data: NutritionToday }>("/nutrition/today"),

  getMealPlan: (targetDate?: string) =>
    api.get<{ status: string; data: { date: string; goal_type: string; target_calories: number; meals: MealTiming[] } }>("/nutrition/meal-plan", { params: targetDate ? { target_date: targetDate } : undefined }),

  logMeal: (meal: {
    meal_type: string;
    name: string;
    calories?: number;
    protein_g?: number;
    carbs_g?: number;
    fat_g?: number;
    description?: string;
  }, targetDate?: string) =>
    api.post<{ status: string; data: any }>("/nutrition/log", { ...meal, ...(targetDate ? { target_date: targetDate } : {}) }),

  deleteMeal: (mealId: number) =>
    api.delete<{ status: string }>(`/nutrition/log/${mealId}`),

  getHistory: (days = 7) =>
    api.get<{ status: string; data: { history: NutritionHistoryEntry[]; days_requested: number; days_returned: number } }>("/nutrition/history", { params: { days } }),

  getSettings: () =>
    api.get<{ status: string; data: NutritionSettings }>("/nutrition/settings"),

  updateSettings: (settings: Partial<NutritionSettings>) =>
    api.put<{ status: string; data: NutritionSettings }>("/nutrition/settings", settings),

  logWater: (glasses = 1) =>
    api.post<{ status: string; data: { glasses_logged: number; hydration_ml: number; hydration_target_ml: number; progress_pct: number } }>("/nutrition/water", { glasses }),

  getHydrationStatus: () =>
    api.get<{ status: string; data: HydrationStatus }>("/nutrition/hydration-status"),
};