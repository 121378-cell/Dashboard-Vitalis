import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Search, Plus, Play, Dumbbell, Flame, X } from 'lucide-react';
import { Exercise } from '../types';

interface CustomExerciseOption {
  id: string;
  name: string;
  muscle_group: string;
  type: string;
}

const PREDEFINED_EXERCISES: CustomExerciseOption[] = [
  { id: '1', name: 'Press de Banca', muscle_group: 'Pecho', type: 'Fuerza' },
  { id: '2', name: 'Sentadilla Libre', muscle_group: 'Piernas', type: 'Fuerza' },
  { id: '3', name: 'Peso Muerto', muscle_group: 'Espalda/Piernas', type: 'Fuerza' },
  { id: '4', name: 'Dominadas', muscle_group: 'Espalda', type: 'Fuerza' },
  { id: '5', name: 'Press Militar', muscle_group: 'Hombros', type: 'Fuerza' },
  { id: '6', name: 'Sprint 100m', muscle_group: 'Piernas', type: 'Cardio HIIT' },
];

export const ExerciseSelector: React.FC = () => {
  const [search, setSearch] = useState('');
  const [selectedExercises, setSelectedExercises] = useState<CustomExerciseOption[]>([]);
  const [isCreatingCustom, setIsCreatingCustom] = useState(false);
  const [customName, setCustomName] = useState('');
  const [customGroup, setCustomGroup] = useState('Piernas');

  const filtered = PREDEFINED_EXERCISES.filter(ex => 
    ex.name.toLowerCase().includes(search.toLowerCase()) ||
    ex.muscle_group.toLowerCase().includes(search.toLowerCase())
  );

  const toggleSelect = (ex: CustomExerciseOption) => {
    if (selectedExercises.find(s => s.id === ex.id)) {
      setSelectedExercises(selectedExercises.filter(s => s.id !== ex.id));
    } else {
      setSelectedExercises([...selectedExercises, ex]);
    }
  };

  const handleCreateCustom = (e: React.FormEvent) => {
    e.preventDefault();
    if (customName.trim().length === 0) return;
    const newEx = {
      id: `custom_${Date.now()}`,
      name: customName,
      muscle_group: customGroup,
      type: 'Custom'
    };
    setSelectedExercises([...selectedExercises, newEx]);
    setIsCreatingCustom(false);
    setCustomName('');
  };

  return (
    <div className="w-full bg-surface-container rounded-2xl border border-outline-variant/10 p-6 flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-headline font-bold text-on-surface flex items-center gap-2">
            <Dumbbell className="text-primary" />
            Configurador de Rutinas
          </h2>
          <p className="text-xs text-on-surface-variant mt-1">Arma tu entrenamiento personalizado o selecciona del catálogo.</p>
        </div>
        <button 
          onClick={() => setIsCreatingCustom(!isCreatingCustom)}
          className="flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary rounded-xl font-bold text-sm hover:bg-primary/20 transition-colors"
        >
          {isCreatingCustom ? <X size={16} /> : <Plus size={16} />}
          {isCreatingCustom ? 'Cancelar' : 'Crear Propio'}
        </button>
      </div>

      <AnimatePresence>
        {isCreatingCustom && (
          <motion.form 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            onSubmit={handleCreateCustom}
            className="mb-6 p-4 bg-surface-container-high border border-primary/20 rounded-xl space-y-4"
          >
            <div className="flex flex-col sm:flex-row gap-4">
              <input
                type="text"
                placeholder="Nombre del Ejercicio..."
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                className="flex-1 bg-surface-variant border-none rounded-lg px-4 py-2 text-sm text-on-surface focus:ring-1 focus:ring-primary outline-none"
                autoFocus
              />
              <select 
                value={customGroup}
                onChange={(e) => setCustomGroup(e.target.value)}
                className="bg-surface-variant border-none rounded-lg px-4 py-2 text-sm text-on-surface focus:ring-1 focus:ring-primary outline-none"
              >
                <option value="Pecho">Pecho</option>
                <option value="Espalda">Espalda</option>
                <option value="Piernas">Piernas</option>
                <option value="Hombros">Hombros</option>
                <option value="Brazos">Brazos</option>
                <option value="Core">Core</option>
                <option value="Full Body">Full Body</option>
              </select>
              <button 
                type="submit"
                className="px-6 py-2 bg-primary text-on-primary rounded-lg font-bold text-sm hover:brightness-110 transition-all"
              >
                Añadir
              </button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" size={18} />
        <input
          type="text"
          placeholder="Buscar por nombre o músculo..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-surface-variant/50 border border-outline-variant/10 rounded-xl pl-10 pr-4 py-3 text-sm focus:border-primary/50 focus:ring-1 focus:ring-primary outline-none transition-all"
        />
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar mb-6 pr-2">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map(ex => {
            const isSelected = selectedExercises.some(s => s.id === ex.id);
            return (
              <motion.div
                key={ex.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => toggleSelect(ex)}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  isSelected 
                    ? 'bg-primary/10 border-primary text-primary' 
                    : 'bg-surface-container-low border-outline-variant/10 hover:border-primary/30'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-bold text-sm">{ex.name}</h4>
                  {isSelected && <div className="w-4 h-4 bg-primary rounded-full flex items-center justify-center">
                    <svg className="w-2.5 h-2.5 text-on-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>}
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full ${isSelected ? 'bg-primary/20' : 'bg-surface-variant'}`}>
                    {ex.muscle_group}
                  </span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full ${isSelected ? 'bg-primary/20' : 'bg-surface-variant'}`}>
                    {ex.type}
                  </span>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      <div className="bg-surface-variant/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <h4 className="text-sm font-bold flex items-center gap-2">
            <Flame size={16} className="text-orange-500" />
            Rutina Lista
          </h4>
          <p className="text-xs text-on-surface-variant">
            {selectedExercises.length} ejercicios seleccionados
          </p>
        </div>
        <button 
          disabled={selectedExercises.length === 0}
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-3 bg-gradient-to-r from-primary to-teal-500 text-on-primary rounded-xl font-bold hover:shadow-lg hover:shadow-primary/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Play size={18} fill="currentColor" />
          Empezar Entrenamiento
        </button>
      </div>
    </div>
  );
};
