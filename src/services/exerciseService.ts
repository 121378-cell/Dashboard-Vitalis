import { getData, postData } from './api';

export interface Exercise {
  id: string;
  name: string;
  primary_muscle: string;
  exercise_type: string;
  recommended_rpe?: [number, number];
  difficulty?: number;
  is_custom?: boolean;
}

export interface CreateExerciseDto {
  name: string;
  primary_muscle: string;
  exercise_type: string;
  difficulty_level: number;
}

export const getExercises = (muscle_group?: string, exercise_type?: string): Promise<Exercise[]> => {
  return getData('/training/exercises', { muscle_group, exercise_type });
};

export const createCustomExercise = (exercise: CreateExerciseDto): Promise<Exercise> => {
  return postData('/training/exercises/custom', exercise);
};
