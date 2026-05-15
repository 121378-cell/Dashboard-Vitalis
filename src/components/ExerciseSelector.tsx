import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Search, Plus, Play, Dumbbell, Flame, X, Check, Loader2 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getExercises, createCustomExercise, Exercise } from '../services/exerciseService';

export const ExerciseSelector: React.FC = () => {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [selectedExercises, setSelectedExercises] = useState<Exercise[]>([]);
  const [isCreatingCustom, setIsCreatingCustom] = useState(false);
  
  // Create Form State
  const [customName, setCustomName] = useState('');
  const [customGroup, setCustomGroup] = useState('chest');
  const [customType, setCustomType] = useState('strength');

  // Fetch Exercises
  const { data: exercises, isLoading } = useQuery({
    queryKey: ['exercises'],
    queryFn: () => getExercises()
  });

  // Create Custom Exercise Mutation
  const mutation = useMutation({
    mutationFn: createCustomExercise,
    onSuccess: (newEx) => {
      queryClient.invalidateQueries({ queryKey: ['exercises'] });
      setSelectedExercises(prev => [...prev, newEx]);
      setIsCreatingCustom(false);
      setCustomName('');
    }
  });

  const filtered = exercises?.filter(ex => 
    ex.name.toLowerCase().includes(search.toLowerCase()) ||
    ex.primary_muscle.toLowerCase().includes(search.toLowerCase())
  ) || [];

  const toggleSelect = (ex: Exercise) => {
    if (selectedExercises.find(s => s.id === ex.id)) {
      setSelectedExercises(selectedExercises.filter(s => s.id !== ex.id));
    } else {
      setSelectedExercises([...selectedExercises, ex]);
    }
  };

  const handleCreateCustom = (e: React.FormEvent) => {
    e.preventDefault();
    if (customName.trim().length === 0) return;
    mutation.mutate({
      name: customName,
      primary_muscle: customGroup,
      exercise_type: customType,
      difficulty_level: 1
    });
  };

  const formatMuscle = (val: string) => {
    const translation: Record<string, string> = {
      'chest': 'Pecho',
      'back': 'Espalda',
      'shoulders': 'Hombros',
      'biceps': 'Bíceps',
      'triceps': 'Tríceps',
      'legs_quads': 'Cuádriceps',
      'legs_hamstrings': 'Isquiotibiales',
      'legs_glutes': 'Glúteos',
      'calves': 'Gemelos',
      'core': 'Core',
      'full_body': 'Full Body'
    };
    return translation[val] || val.replace('_', ' ');
  };

  const formatType = (val: string) => {
    const translation: Record<string, string> = {
      'strength': 'Fuerza',
      'hypertrophy': 'Hipertrofia',
      'power': 'Potencia',
      'endurance': 'Resistencia',
      'recovery': 'Recuperación',
      'deload': 'Descarga'
    };
    return translation[val] || val;
  };

  return (
    <div className="w-full h-full min-h-[600px] flex flex-col bg-gradient-to-br from-surface-container/90 to-surface-container-high/80 backdrop-blur-2xl rounded-[32px] border border-white/5 shadow-2xl overflow-hidden p-8 relative">
      {/* Decorative Blob */}
      <div className="absolute top-[-100px] right-[-100px] w-[300px] h-[300px] bg-primary/20 blur-[100px] rounded-full pointer-events-none" />
      
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 relative z-10">
        <div>
          <h2 className="text-3xl font-headline font-black bg-gradient-to-r from-on-surface to-on-surface-variant bg-clip-text text-transparent flex items-center gap-3 tracking-tight">
            <div className="p-3 bg-primary/10 rounded-2xl">
              <Dumbbell className="text-primary" size={28} />
            </div>
            Librería de Ejercicios
          </h2>
          <p className="text-on-surface-variant/80 mt-2 text-sm font-medium">Diseña tu plan perfecto o crea movimientos únicos.</p>
        </div>
        
        <motion.button 
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setIsCreatingCustom(!isCreatingCustom)}
          className={`flex items-center gap-2 px-6 py-3 rounded-2xl font-bold text-sm transition-all shadow-lg ${
            isCreatingCustom 
            ? 'bg-error/10 text-error hover:bg-error/20 border border-error/20' 
            : 'bg-primary text-on-primary hover:shadow-primary/30 border border-primary/50'
          }`}
        >
          {isCreatingCustom ? <X size={18} /> : <Plus size={18} />}
          {isCreatingCustom ? 'Cancelar' : 'Nuevo Ejercicio'}
        </motion.button>
      </div>

      <AnimatePresence>
        {isCreatingCustom && (
          <motion.div 
            initial={{ opacity: 0, height: 0, y: -20 }}
            animate={{ opacity: 1, height: 'auto', y: 0 }}
            exit={{ opacity: 0, height: 0, y: -20 }}
            className="mb-8 relative z-10"
          >
            <form 
              onSubmit={handleCreateCustom}
              className="p-6 bg-surface-variant/30 backdrop-blur-md border border-primary/30 rounded-3xl space-y-5 shadow-inner"
            >
              <h3 className="text-sm font-bold text-primary flex items-center gap-2">
                <Flame size={16} /> Crear Ejercicio Personalizado
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <input
                  type="text"
                  placeholder="Nombre del Ejercicio (ej: Curl Araña)"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  className="w-full bg-surface-container/50 border border-white/5 rounded-xl px-5 py-3 text-sm text-on-surface focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all placeholder:text-on-surface-variant/50"
                  autoFocus
                  disabled={mutation.isPending}
                />
                
                <div className="relative">
                  <select 
                    value={customGroup}
                    onChange={(e) => setCustomGroup(e.target.value)}
                    className="w-full bg-surface-container/50 border border-white/5 rounded-xl px-5 py-3 text-sm text-on-surface focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all appearance-none cursor-pointer"
                    disabled={mutation.isPending}
                  >
                    <option value="chest">Pecho</option>
                    <option value="back">Espalda</option>
                    <option value="shoulders">Hombros</option>
                    <option value="biceps">Bíceps</option>
                    <option value="triceps">Tríceps</option>
                    <option value="legs_quads">Cuádriceps</option>
                    <option value="legs_hamstrings">Isquiotibiales</option>
                    <option value="legs_glutes">Glúteos</option>
                    <option value="calves">Gemelos</option>
                    <option value="core">Core</option>
                    <option value="full_body">Full Body</option>
                  </select>
                </div>

                <div className="relative">
                  <select 
                    value={customType}
                    onChange={(e) => setCustomType(e.target.value)}
                    className="w-full bg-surface-container/50 border border-white/5 rounded-xl px-5 py-3 text-sm text-on-surface focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all appearance-none cursor-pointer"
                    disabled={mutation.isPending}
                  >
                    <option value="strength">Fuerza</option>
                    <option value="hypertrophy">Hipertrofia</option>
                    <option value="power">Potencia</option>
                    <option value="endurance">Resistencia</option>
                  </select>
                </div>
              </div>
              
              <div className="flex justify-end">
                <motion.button 
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  disabled={mutation.isPending || customName.trim().length === 0}
                  className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-primary to-primary-container text-on-primary rounded-xl font-bold text-sm shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {mutation.isPending ? <Loader2 size={18} className="animate-spin" /> : <Check size={18} />}
                  Guardar Ejercicio
                </motion.button>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="relative mb-8 z-10">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant/50" size={20} />
        <input
          type="text"
          placeholder="Busca cualquier ejercicio o grupo muscular..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-surface-container/30 backdrop-blur-md border border-white/10 rounded-2xl pl-12 pr-6 py-4 text-sm text-on-surface focus:bg-surface-container/60 focus:border-primary/50 focus:ring-4 focus:ring-primary/10 outline-none transition-all placeholder:text-on-surface-variant/40 font-medium"
        />
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar mb-8 pr-4 -mr-4 relative z-10">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-40 text-primary">
            <Loader2 className="animate-spin mb-4" size={32} />
            <p className="text-sm font-medium animate-pulse">Cargando biblioteca muscular...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-on-surface-variant text-center px-4">
            <Dumbbell className="opacity-20 mb-3" size={48} />
            <p className="text-sm font-medium">No encontramos resultados para tu búsqueda.</p>
            <p className="text-xs opacity-70 mt-1">Prueba creando un ejercicio personalizado.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-4">
            <AnimatePresence>
              {filtered.map(ex => {
                const isSelected = selectedExercises.some(s => s.id === ex.id);
                return (
                  <motion.div
                    layout
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    whileHover={{ y: -4, scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => toggleSelect(ex)}
                    key={ex.id}
                    className={`relative p-5 rounded-3xl border-2 cursor-pointer transition-all duration-300 overflow-hidden ${
                      isSelected 
                        ? 'bg-primary/10 border-primary shadow-lg shadow-primary/10' 
                        : 'bg-surface-container/50 border-white/5 hover:border-primary/30 hover:bg-surface-container-high'
                    }`}
                  >
                    {isSelected && (
                      <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-primary to-transparent opacity-20 pointer-events-none" />
                    )}
                    
                    <div className="flex items-start justify-between mb-3 relative z-10">
                      <h4 className={`font-bold leading-tight pr-6 ${isSelected ? 'text-primary' : 'text-on-surface'}`}>
                        {ex.name}
                        {ex.is_custom && (
                          <span className="ml-2 inline-flex items-center text-[9px] uppercase tracking-wider font-black px-2 py-0.5 rounded-md bg-secondary/20 text-secondary align-middle">
                            Custom
                          </span>
                        )}
                      </h4>
                      <div className={`absolute right-0 top-0 w-6 h-6 rounded-full flex items-center justify-center transition-all ${
                        isSelected ? 'bg-primary scale-100' : 'bg-surface-variant scale-0 opacity-0'
                      }`}>
                        <Check className="text-on-primary" size={14} strokeWidth={3} />
                      </div>
                    </div>
                    
                    <div className="flex flex-wrap items-center gap-2 mt-4 relative z-10">
                      <span className={`text-[11px] font-bold px-3 py-1 rounded-lg ${isSelected ? 'bg-primary/20 text-primary-container' : 'bg-surface-variant/80 text-on-surface-variant'}`}>
                        {formatMuscle(ex.primary_muscle)}
                      </span>
                      <span className={`text-[11px] font-bold px-3 py-1 rounded-lg ${isSelected ? 'bg-primary/20 text-primary-container' : 'bg-surface-variant/80 text-on-surface-variant'}`}>
                        {formatType(ex.exercise_type)}
                      </span>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>

      <div className="relative z-10 mt-auto">
        <div className="absolute inset-0 bg-gradient-to-t from-surface-container via-surface-container to-transparent opacity-80 pointer-events-none -top-12 bottom-0" />
        
        <div className="relative bg-surface-variant/20 backdrop-blur-xl border border-white/10 rounded-[24px] p-5 flex flex-col sm:flex-row items-center justify-between gap-5 shadow-xl">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-orange-400 to-red-500 flex items-center justify-center shadow-lg shadow-orange-500/20">
              <Flame size={24} className="text-white" />
            </div>
            <div>
              <h4 className="text-lg font-black text-on-surface">Rutina Lista</h4>
              <p className="text-sm font-medium text-on-surface-variant">
                {selectedExercises.length} {selectedExercises.length === 1 ? 'ejercicio seleccionado' : 'ejercicios seleccionados'}
              </p>
            </div>
          </div>
          
          <motion.button 
            whileHover={selectedExercises.length > 0 ? { scale: 1.05 } : {}}
            whileTap={selectedExercises.length > 0 ? { scale: 0.95 } : {}}
            disabled={selectedExercises.length === 0}
            className="w-full sm:w-auto flex items-center justify-center gap-3 px-8 py-4 bg-gradient-to-r from-primary to-primary-container text-on-primary rounded-2xl font-bold text-base shadow-xl hover:shadow-primary/40 transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:shadow-none"
          >
            <Play size={20} fill="currentColor" />
            Iniciar Sesión
          </motion.button>
        </div>
      </div>
    </div>
  );
};
