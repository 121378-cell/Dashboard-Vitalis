import React, { useState } from 'react';
import { Play, CheckCircle2, Plus, Trash2, Save, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface Set {
  id: string;
  set_number: number;
  reps: number;
  weight_kg: number;
  rpe_target: number;
  rpe_real?: number;
  completed: boolean;
}

interface Exercise {
  name: string;
  sets: Set[];
}

interface WorkoutSession {
  name: string;
  exercises: Exercise[];
}

interface Props {
  session: WorkoutSession;
  onSave: (session: WorkoutSession) => void;
}

export const WorkoutLogger: React.FC<Props> = ({ session: initialSession, onSave }) => {
  const [session, setSession] = useState<WorkoutSession>(initialSession);

  const updateSet = (exerciseIndex: number, setIndex: number, updates: Partial<Set>) => {
    const newSession = { ...session };
    newSession.exercises[exerciseIndex].sets[setIndex] = {
      ...newSession.exercises[exerciseIndex].sets[setIndex],
      ...updates
    };
    setSession(newSession);
  };

  const addSet = (exerciseIndex: number) => {
    const newSession = { ...session };
    const lastSet = newSession.exercises[exerciseIndex].sets[newSession.exercises[exerciseIndex].sets.length - 1];
    const newSet: Set = {
      id: Math.random().toString(36).substr(2, 9),
      set_number: lastSet ? lastSet.set_number + 1 : 1,
      reps: lastSet ? lastSet.reps : 10,
      weight_kg: lastSet ? lastSet.weight_kg : 0,
      rpe_target: lastSet ? lastSet.rpe_target : 7,
      completed: false
    };
    newSession.exercises[exerciseIndex].sets.push(newSet);
    setSession(newSession);
  };

  const deleteSet = (exerciseIndex: number, setIndex: number) => {
    const newSession = { ...session };
    newSession.exercises[exerciseIndex].sets.splice(setIndex, 1);
    setSession(newSession);
  };

  return (
    <div className="space-y-6 pb-20">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-primary">{session.name}</h2>
        <button 
          onClick={() => onSave(session)}
          className="flex items-center gap-2 bg-primary text-on-primary px-4 py-2 rounded-xl text-sm font-bold shadow-lg shadow-primary/20 hover:scale-105 transition-transform"
        >
          <Save size={18} />
          GUARDAR SESIÓN
        </button>
      </div>

      <div className="space-y-8">
        {session.exercises.map((exercise, exIdx) => (
          <div key={exIdx} className="bg-surface-container rounded-2xl border border-outline-variant/10 overflow-hidden shadow-sm">
            <div className="bg-primary/5 p-4 border-b border-outline-variant/10 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-primary/20 rounded-lg flex items-center justify-center text-primary">
                  <Play size={16} fill="currentColor" />
                </div>
                <h3 className="font-bold text-on-surface">{exercise.name}</h3>
              </div>
              <button 
                onClick={() => addSet(exIdx)}
                className="text-xs font-bold text-primary flex items-center gap-1 hover:underline"
              >
                <Plus size={14} /> AÑADIR SERIE
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant bg-surface-container-low/50">
                  <tr>
                    <th className="px-4 py-3 w-16 text-center">Serie</th>
                    <th className="px-4 py-3">Peso (kg)</th>
                    <th className="px-4 py-3">Reps</th>
                    <th className="px-4 py-3 w-20">RPE</th>
                    <th className="px-4 py-3 w-16 text-center">Status</th>
                    <th className="px-4 py-3 w-12"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/5">
                  {exercise.sets.map((set, setIdx) => (
                    <tr key={set.id} className={`${set.completed ? 'bg-green-500/5' : ''} transition-colors`}>
                      <td className="px-4 py-3 text-center font-bold text-on-surface-variant">{set.set_number}</td>
                      <td className="px-4 py-3 text-center">
                        <input 
                          type="number" 
                          value={set.weight_kg}
                          onChange={(e) => updateSet(exIdx, setIdx, { weight_kg: parseFloat(e.target.value) })}
                          className="w-20 bg-surface-container-high border border-outline-variant/20 rounded-lg px-2 py-1 text-center font-bold focus:ring-1 focus:ring-primary outline-none"
                        />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <input 
                          type="number" 
                          value={set.reps}
                          onChange={(e) => updateSet(exIdx, setIdx, { reps: parseInt(e.target.value) })}
                          className="w-16 bg-surface-container-high border border-outline-variant/20 rounded-lg px-2 py-1 text-center font-bold focus:ring-1 focus:ring-primary outline-none"
                        />
                      </td>
                      <td className="px-4 py-3">
                         <div className="flex items-center gap-1">
                           <span className="text-[10px] text-on-surface-variant">Tgt: {set.rpe_target}</span>
                           <input 
                             type="number" 
                             placeholder="Real"
                             value={set.rpe_real || ''}
                             onChange={(e) => updateSet(exIdx, setIdx, { rpe_real: parseFloat(e.target.value) })}
                             className="w-12 bg-transparent border-b border-outline-variant/20 text-xs text-center outline-none"
                           />
                         </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button 
                          onClick={() => updateSet(exIdx, setIdx, { completed: !set.completed })}
                          className={`p-2 rounded-full transition-all ${set.completed ? 'text-green-400 bg-green-400/10' : 'text-on-surface-variant/30 hover:bg-surface-variant'}`}
                        >
                          <CheckCircle2 size={24} />
                        </button>
                      </td>
                      <td className="px-4 py-3">
                        <button 
                          onClick={() => deleteSet(exIdx, setIdx)}
                          className="text-on-surface-variant/20 hover:text-red-400 transition-colors"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
      
      <div className="p-4 bg-primary/10 rounded-2xl border border-primary/20 flex gap-4">
        <Info className="text-primary shrink-0" />
        <p className="text-xs text-on-surface-variant leading-relaxed">
          <strong>Pro-Tip de ATLAS:</strong> Esta plantilla está optimizada para tu 
          <strong> Proyecto 31/07</strong>. Cada serie es editable en tiempo real. 
          Al terminar, guarda la sesión para que tu ACWR y Readiness se actualicen.
        </p>
      </div>
    </div>
  );
};
