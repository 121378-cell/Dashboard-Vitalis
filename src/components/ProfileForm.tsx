import React, { useState } from 'react';
import { AthleteProfile } from '../types';

interface Props {
  profile: AthleteProfile;
  onSave: (profile: AthleteProfile) => void;
}

export const ProfileForm: React.FC<Props> = ({ profile, onSave }) => {
  const [formData, setFormData] = useState<AthleteProfile>(profile);

  const goals = [
    "Pérdida de grasa",
    "Ganancia muscular",
    "Resistencia aeróbica",
    "Fuerza máxima",
    "Rendimiento deportivo",
    "Salud general",
    "Flexibilidad",
    "Rehabilitación"
  ];

  const isValid = formData.name.trim() !== "" && formData.age > 0 && formData.goal !== "";

  return (
    <div className="bg-surface-container p-6 rounded-xl space-y-6 max-w-2xl mx-auto">
      <h2 className="text-2xl font-headline font-bold">Perfil del Atleta</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase text-on-surface-variant">Nombre</label>
          <input 
            type="text" 
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full bg-surface-container-low border border-outline-variant/20 rounded-lg p-2 outline-none focus:border-primary"
          />
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase text-on-surface-variant">Edad</label>
          <input 
            type="number" 
            value={formData.age}
            onChange={(e) => setFormData({ ...formData, age: parseInt(e.target.value) || 0 })}
            className="w-full bg-surface-container-low border border-outline-variant/20 rounded-lg p-2 outline-none focus:border-primary"
          />
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase text-on-surface-variant">Peso (kg)</label>
          <input 
            type="number" 
            value={formData.weight}
            onChange={(e) => setFormData({ ...formData, weight: parseFloat(e.target.value) || 0 })}
            className="w-full bg-surface-container-low border border-outline-variant/20 rounded-lg p-2 outline-none focus:border-primary"
          />
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase text-on-surface-variant">Altura (cm)</label>
          <input 
            type="number" 
            value={formData.height}
            onChange={(e) => setFormData({ ...formData, height: parseFloat(e.target.value) || 0 })}
            className="w-full bg-surface-container-low border border-outline-variant/20 rounded-lg p-2 outline-none focus:border-primary"
          />
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase text-on-surface-variant">Objetivo Principal</label>
          <select 
            value={formData.goal}
            onChange={(e) => setFormData({ ...formData, goal: e.target.value })}
            className="w-full bg-surface-container-low border border-outline-variant/20 rounded-lg p-2 outline-none focus:border-primary"
          >
            <option value="">Seleccionar...</option>
            {goals.map(g => <option key={g} value={g}>{g}</option>)}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase text-on-surface-variant">Nivel de Experiencia</label>
          <select 
            value={formData.experience}
            onChange={(e) => setFormData({ ...formData, experience: e.target.value as any })}
            className="w-full bg-surface-container-low border border-outline-variant/20 rounded-lg p-2 outline-none focus:border-primary"
          >
            <option value="principiante">Principiante</option>
            <option value="intermedio">Intermedio</option>
            <option value="avanzado">Avanzado</option>
            <option value="élite">Élite</option>
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase text-on-surface-variant">Días Disponibles / Semana</label>
          <input 
            type="number" 
            value={formData.daysPerWeek}
            onChange={(e) => setFormData({ ...formData, daysPerWeek: parseInt(e.target.value) || 0 })}
            className="w-full bg-surface-container-low border border-outline-variant/20 rounded-lg p-2 outline-none focus:border-primary"
          />
        </div>
      </div>

      <div className="space-y-1">
        <label className="text-[10px] font-bold uppercase text-on-surface-variant">Historial Médico / Lesiones</label>
        <textarea 
          value={formData.medicalHistory}
          onChange={(e) => setFormData({ ...formData, medicalHistory: e.target.value })}
          className="w-full bg-surface-container-low border border-outline-variant/20 rounded-lg p-2 outline-none focus:border-primary h-24 resize-none"
        />
      </div>

      <button 
        onClick={() => onSave(formData)}
        disabled={!isValid}
        className="w-full bg-primary text-on-primary py-3 rounded-lg font-bold uppercase tracking-widest hover:brightness-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Guardar Perfil
      </button>
    </div>
  );
};
