import React, { useState, useCallback } from 'react';
import type { SessionPlan, Exercise, ExerciseSet } from '../types';

interface SessionTableProps {
  plan: SessionPlan;
  sessionId?: string;
  onSave?: (sessionId: string, data: any[]) => Promise<void>;
  onAnalyze?: (sessionId: string) => Promise<void>;
}

const STATUS_OPTIONS = [
  { value: 'pending', label: '⏳ Pendiente', color: '#9ca3af' },
  { value: 'completed', label: '✅ Completado', color: '#22c55e' },
  { value: 'partial', label: '⚠️ Parcial', color: '#f59e0b' },
  { value: 'failed', label: '❌ Fallado', color: '#ef4444' },
];

export const SessionTable: React.FC<SessionTableProps> = ({ 
  plan, 
  sessionId,
  onSave,
  onAnalyze 
}) => {
  // Format session date
  const sessionDate = plan.date 
    ? new Date(plan.date).toLocaleDateString('es-ES', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      })
    : new Date().toLocaleDateString('es-ES', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      });
  const [editData, setEditData] = useState<Record<string, Partial<ExerciseSet>>>(() => {
    const initial: Record<string, Partial<ExerciseSet>> = {};
    plan.exercises.forEach((exercise, exIndex) => {
      exercise.sets.forEach((set, setIndex) => {
        const key = `${exIndex}-${setIndex}`;
        initial[key] = {
          actual_reps: set.reps,
          actual_weight_kg: set.weight_kg,
          actual_rpe: undefined,
          status: 'pending',
        };
      });
    });
    return initial;
  });

  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleInputChange = useCallback((
    exerciseIndex: number,
    setIndex: number,
    field: keyof ExerciseSet,
    value: number | string | undefined
  ) => {
    const key = `${exerciseIndex}-${setIndex}`;
    setEditData(prev => ({
      ...prev,
      [key]: {
        ...prev[key],
        [field]: value,
      },
    }));
  }, []);

  const handleSave = async () => {
    if (!sessionId && !plan.session_id) {
      setSaveError('No hay session_id disponible');
      return;
    }

    const targetSessionId = sessionId || plan.session_id;
    if (!targetSessionId) {
      setSaveError('ID de sesión no disponible');
      return;
    }

    setIsSaving(true);
    setSaveError(null);

    try {
      // Build actual_data array
      const actualData: any[] = [];
      plan.exercises.forEach((exercise, exIndex) => {
        exercise.sets.forEach((set, setIndex) => {
          const key = `${exIndex}-${setIndex}`;
          const edited = editData[key];
          actualData.push({
            exercise_name: exercise.name,
            set_number: set.set_number,
            actual_reps: edited?.actual_reps ?? set.reps,
            actual_weight_kg: edited?.actual_weight_kg ?? set.weight_kg,
            actual_rpe: edited?.actual_rpe,
            status: edited?.status || 'pending',
          });
        });
      });

      // Call save endpoint
      const response = await fetch(`/api/v1/sessions/${targetSessionId}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ actual_data: actualData }),
      });

      if (!response.ok) {
        throw new Error(`Error guardando sesión: ${response.status}`);
      }

      // Call analyze endpoint
      const analyzeResponse = await fetch(`/api/v1/sessions/${targetSessionId}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!analyzeResponse.ok) {
        throw new Error(`Error analizando sesión: ${analyzeResponse.status}`);
      }

      const analysisData = await analyzeResponse.json();

      // ----------------------------------------------------
      // Integración con Health Connect & Offline Logger
      // ----------------------------------------------------
      try {
        const { workoutLogger } = await import('../services/workoutLogger');
        // Estimamos la hora de inicio basándonos en la duración
        const durationMin = plan.estimated_duration_min || 45;
        const startedAt = new Date(Date.now() - durationMin * 60000);
        
        await workoutLogger.onWorkoutComplete({
          sessionName: plan.session_name,
          startedAt: startedAt,
          completedAt: new Date(),
          sessionType: 'Strength', // Por defecto para las tablas de musculación de ATLAS
          totalCalories: durationMin * 7.5 // Estimación dinámica de calorías quemadas
        });
      } catch (logErr) {
        console.warn('Error en el flujo paralelo de Workout Logger', logErr);
      }
      
      // Call the onAnalyze callback with the analysis result
      if (onAnalyze) {
        await onAnalyze(targetSessionId);
      }

    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setIsSaving(false);
    }
  };

  const getRowStyle = (status: string | undefined): React.CSSProperties => {
    switch (status) {
      case 'completed':
        return { backgroundColor: '#dcfce7' }; // green-100
      case 'partial':
        return { backgroundColor: '#fef3c7' }; // amber-100
      case 'failed':
        return { backgroundColor: '#fee2e2' }; // red-100
      default:
        return { backgroundColor: '#f3f4f6' }; // gray-100
    }
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h3 style={styles.title}>{plan.session_name}</h3>
        <p style={styles.date}>{sessionDate}</p>
        <div style={styles.meta}>
          <span style={styles.badge}>⏱️ {plan.estimated_duration_min} min</span>
          <span style={styles.badge}>📊 Readiness: {plan.readiness}/10</span>
        </div>
        {plan.coach_notes && (
          <div style={styles.notes}>
            <strong>💡 Notas del Coach:</strong> {plan.coach_notes}
          </div>
        )}
      </div>

      {/* Warmup */}
      {plan.warmup && (
        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>🔥 Calentamiento</h4>
          <p style={styles.sectionText}>{plan.warmup}</p>
        </div>
      )}

      {/* Exercises Table */}
      <div style={styles.tableWrapper}>
        {plan.exercises.map((exercise, exIndex) => (
          <div key={exIndex} style={styles.exerciseBlock}>
            <div style={styles.exerciseHeader}>
              <strong>{exercise.name}</strong>
              <span style={styles.muscleGroup}>{exercise.muscle_group}</span>
            </div>
            
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Serie</th>
                  <th style={styles.th}>Reps Obj.</th>
                  <th style={styles.th}>Peso Obj.</th>
                  <th style={styles.th}>RPE Obj.</th>
                  <th style={styles.th}>Reps Real</th>
                  <th style={styles.th}>Peso Real</th>
                  <th style={styles.th}>RPE Real</th>
                  <th style={styles.th}>Descanso</th>
                  <th style={styles.th}>Tempo</th>
                  <th style={styles.th}>Estado</th>
                </tr>
              </thead>
              <tbody>
                {exercise.sets.map((set, setIndex) => {
                  const key = `${exIndex}-${setIndex}`;
                  const edited = editData[key];
                  const status = edited?.status || 'pending';
                  
                  return (
                    <tr key={setIndex} style={getRowStyle(status)}>
                      <td style={styles.tdCenter}>{set.set_number}</td>
                      <td style={styles.tdCenter}>{set.reps}</td>
                      <td style={styles.tdCenter}>{set.weight_kg}kg</td>
                      <td style={styles.tdCenter}>@{set.rpe_target}</td>
                      <td style={styles.tdInput}>
                        <input
                          type="number"
                          min="0"
                          value={edited?.actual_reps ?? ''}
                          onChange={(e) => handleInputChange(exIndex, setIndex, 'actual_reps', 
                            e.target.value === '' ? undefined : parseInt(e.target.value))}
                          placeholder={set.reps.toString()}
                          style={styles.input}
                        />
                      </td>
                      <td style={styles.tdInput}>
                        <input
                          type="number"
                          min="0"
                          step="0.5"
                          value={edited?.actual_weight_kg ?? ''}
                          onChange={(e) => handleInputChange(exIndex, setIndex, 'actual_weight_kg', 
                            e.target.value === '' ? undefined : parseFloat(e.target.value))}
                          placeholder={set.weight_kg.toString()}
                          style={styles.input}
                        />
                      </td>
                      <td style={styles.tdInput}>
                        <input
                          type="number"
                          min="1"
                          max="10"
                          step="0.5"
                          value={edited?.actual_rpe ?? ''}
                          onChange={(e) => handleInputChange(exIndex, setIndex, 'actual_rpe', 
                            e.target.value === '' ? undefined : parseFloat(e.target.value))}
                          placeholder="RPE"
                          style={{ ...styles.input, width: '50px' }}
                        />
                      </td>
                      <td style={styles.tdCenter}>{set.rest_seconds}s</td>
                      <td style={styles.tdCenter}><small>{set.tempo}</small></td>
                      <td style={styles.tdInput}>
                        <select
                          value={status}
                          onChange={(e) => handleInputChange(exIndex, setIndex, 'status', e.target.value)}
                          style={styles.select}
                        >
                          {STATUS_OPTIONS.map(opt => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ))}
      </div>

      {/* Cooldown */}
      {plan.cooldown && (
        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>🧘 Enfriamiento</h4>
          <p style={styles.sectionText}>{plan.cooldown}</p>
        </div>
      )}

      {/* Save Button */}
      <div style={styles.footer}>
        {saveError && (
          <div style={styles.error}>❌ {saveError}</div>
        )}
        <button
          onClick={handleSave}
          disabled={isSaving}
          style={{
            ...styles.saveButton,
            opacity: isSaving ? 0.6 : 1,
          }}
        >
          {isSaving ? '💾 Guardando...' : '💾 Guardar Sesión'}
        </button>
      </div>
    </div>
  );
};

// Inline styles for the component
const styles: Record<string, React.CSSProperties> = {
  container: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    padding: '16px',
    margin: '12px 0',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    maxWidth: '100%',
  },
  header: {
    marginBottom: '16px',
    paddingBottom: '12px',
    borderBottom: '2px solid #e5e7eb',
  },
  date: {
    fontSize: '14px',
    color: '#666666',
    marginBottom: '8px',
    fontWeight: 400,
  },
  meta: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
    marginBottom: '8px',
  },
  badge: {
    backgroundColor: '#e0e7ff',
    color: '#3730a3',
    padding: '4px 12px',
    borderRadius: '16px',
    fontSize: '0.875rem',
    fontWeight: 500,
  },
  notes: {
    backgroundColor: '#fef3c7',
    padding: '8px 12px',
    borderRadius: '6px',
    fontSize: '0.875rem',
    color: '#92400e',
  },
  section: {
    marginBottom: '16px',
    padding: '12px',
    backgroundColor: '#f9fafb',
    borderRadius: '8px',
  },
  sectionTitle: {
    margin: '0 0 8px 0',
    fontSize: '1rem',
    fontWeight: 600,
    color: '#374151',
  },
  sectionText: {
    margin: 0,
    fontSize: '0.875rem',
    color: '#4b5563',
    lineHeight: 1.5,
  },
  tableWrapper: {
    overflowX: 'auto',
    marginBottom: '16px',
  },
  exerciseBlock: {
    marginBottom: '20px',
  },
  exerciseHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '8px',
    padding: '8px 12px',
    backgroundColor: '#e0e7ff',
    borderRadius: '6px',
    fontSize: '0.95rem',
  },
  muscleGroup: {
    fontSize: '0.8rem',
    color: '#6b7280',
    backgroundColor: '#fff',
    padding: '2px 8px',
    borderRadius: '12px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.85rem',
    minWidth: '700px',
  },
  th: {
    backgroundColor: '#2c3e50',
    color: '#ffffff',
    padding: '8px 6px',
    textAlign: 'center',
    fontWeight: 600,
    fontSize: '0.75rem',
    whiteSpace: 'nowrap',
  },
  tdCenter: {
    padding: '6px',
    textAlign: 'center',
    borderBottom: '1px solid #e5e7eb',
    color: '#1a1a1a',
    backgroundColor: '#f5f5f5',
    fontWeight: 500,
    borderRadius: '4px',
  },
  tdInput: {
    padding: '4px',
    textAlign: 'center',
    borderBottom: '1px solid #e5e7eb',
  },
  input: {
    width: '60px',
    padding: '4px 6px',
    border: '1px solid #cccccc',
    borderRadius: '4px',
    fontSize: '0.8rem',
    textAlign: 'center',
    color: '#1a1a1a',
    backgroundColor: '#ffffff',
  },
  select: {
    padding: '4px 8px',
    border: '1px solid #cccccc',
    borderRadius: '4px',
    fontSize: '0.8rem',
    backgroundColor: '#ffffff',
    cursor: 'pointer',
    color: '#1a1a1a',
  },
  footer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '12px',
    paddingTop: '16px',
    borderTop: '2px solid #e5e7eb',
  },
  saveButton: {
    backgroundColor: '#22c55e',
    color: '#fff',
    padding: '12px 32px',
    border: 'none',
    borderRadius: '8px',
    fontSize: '1rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  error: {
    color: '#dc2626',
    fontSize: '0.875rem',
    padding: '8px 12px',
    backgroundColor: '#fee2e2',
    borderRadius: '6px',
  },
};

export default SessionTable;
