import React, { useState, useEffect } from 'react';
import { healthConnectService, HCBiometrics, HCWorkout } from '../services/healthConnectService';
import { X, RefreshCw, Activity, Heart, Footprints, Flame, Moon } from 'lucide-react';

interface DebugPanelProps {
  isOpen: boolean;
  onClose: () => void;
  biometrics: HCBiometrics | null;
  workouts: any[];
}

export const DebugPanel: React.FC<DebugPanelProps> = ({ isOpen, onClose, biometrics, workouts }) => {
  const [hcAvailable, setHcAvailable] = useState<boolean>(false);
  const [hcPermissions, setHcPermissions] = useState<Record<string, boolean>>({});
  const [hcRawWorkouts, setHcRawWorkouts] = useState<HCWorkout[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadDebugData();
    }
  }, [isOpen]);

  const loadDebugData = async () => {
    setLoading(true);
    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] Cargando datos de debug...`]);
    
    try {
      // Verificar HC disponible
      await healthConnectService.initialize();
      const available = await healthConnectService.isAvailable();
      setHcAvailable(available);
      setLogs(prev => [...prev, `Health Connect disponible: ${available}`]);

      if (available) {
        // Verificar permisos
        const perms = await healthConnectService.checkPermissions();
        setHcPermissions(perms.permissions);
        setLogs(prev => [...prev, `Permisos: ${JSON.stringify(perms.permissions)}`]);

        // Cargar workouts directamente
        const rawWorkouts = await healthConnectService.readTodayWorkouts();
        setHcRawWorkouts(rawWorkouts);
        setLogs(prev => [...prev, `Workouts encontrados: ${rawWorkouts.length}`]);
        
        if (rawWorkouts.length > 0) {
          rawWorkouts.forEach((w, i) => {
            setLogs(prev => [...prev, `  [${i}] ${w.title} | ${w.exerciseType} | ${Math.round(w.duration/60)}min | ${w.calories}kcal`]);
          });
        }
      }
    } catch (e) {
      setLogs(prev => [...prev, `ERROR: ${e}`]);
    }
    
    setLoading(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm overflow-auto">
      <div className="min-h-screen p-4">
        <div className="max-w-lg mx-auto bg-gray-900 rounded-2xl shadow-2xl overflow-hidden">
          {/* Header */}
          <div className="bg-emerald-600 px-4 py-3 flex items-center justify-between">
            <h2 className="text-white font-bold flex items-center gap-2">
              <Activity size={20} />
              Debug Panel - Health Connect
            </h2>
            <div className="flex items-center gap-2">
              <button 
                onClick={loadDebugData}
                className="p-2 bg-emerald-700 rounded-lg hover:bg-emerald-600 transition-colors"
                disabled={loading}
              >
                <RefreshCw size={18} className={`text-white ${loading ? 'animate-spin' : ''}`} />
              </button>
              <button 
                onClick={onClose}
                className="p-2 bg-emerald-700 rounded-lg hover:bg-emerald-600 transition-colors"
              >
                <X size={18} className="text-white" />
              </button>
            </div>
          </div>

          <div className="p-4 space-y-4">
            {/* Status */}
            <div className="bg-gray-800 rounded-xl p-3">
              <h3 className="text-emerald-400 font-semibold mb-2">Estado Health Connect</h3>
              <div className="space-y-1 text-sm">
                <div className="flex items-center gap-2">
                  <span className={hcAvailable ? 'text-green-400' : 'text-red-400'}>
                    {hcAvailable ? '●' : '○'}
                  </span>
                  <span className="text-gray-300">
                    {hcAvailable ? 'Disponible' : 'No disponible'}
                  </span>
                </div>
              </div>
            </div>

            {/* Permisos */}
            {hcAvailable && (
              <div className="bg-gray-800 rounded-xl p-3">
                <h3 className="text-emerald-400 font-semibold mb-2">Permisos</h3>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(hcPermissions).map(([key, granted]) => (
                    <div key={key} className="flex items-center gap-2">
                      <span className={granted ? 'text-green-400' : 'text-red-400'}>
                        {granted ? '✓' : '✗'}
                      </span>
                      <span className="text-gray-300 truncate">{key}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Biométricos */}
            {biometrics && (
              <div className="bg-gray-800 rounded-xl p-3">
                <h3 className="text-emerald-400 font-semibold mb-2 flex items-center gap-2">
                  <Heart size={16} /> Biométricos Actuales
                </h3>
                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div className="bg-gray-700 rounded-lg p-2 text-center">
                    <Footprints size={14} className="mx-auto mb-1 text-blue-400" />
                    <div className="text-gray-400">Pasos</div>
                    <div className="text-white font-bold">{biometrics.steps ?? '-'}</div>
                  </div>
                  <div className="bg-gray-700 rounded-lg p-2 text-center">
                    <Heart size={14} className="mx-auto mb-1 text-red-400" />
                    <div className="text-gray-400">FC</div>
                    <div className="text-white font-bold">{biometrics.heartRate ?? '-'}</div>
                  </div>
                  <div className="bg-gray-700 rounded-lg p-2 text-center">
                    <Flame size={14} className="mx-auto mb-1 text-orange-400" />
                    <div className="text-gray-400">Kcal</div>
                    <div className="text-white font-bold">{biometrics.calories ?? '-'}</div>
                  </div>
                  <div className="bg-gray-700 rounded-lg p-2 text-center">
                    <Moon size={14} className="mx-auto mb-1 text-purple-400" />
                    <div className="text-gray-400">Sueño</div>
                    <div className="text-white font-bold">{biometrics.sleepHours ?? '-'}h</div>
                  </div>
                  <div className="bg-gray-700 rounded-lg p-2 text-center">
                    <Activity size={14} className="mx-auto mb-1 text-green-400" />
                    <div className="text-gray-400">HRV</div>
                    <div className="text-white font-bold">{biometrics.hrv ?? '-'}</div>
                  </div>
                  <div className="bg-gray-700 rounded-lg p-2 text-center">
                    <div className="text-gray-400">Fuente</div>
                    <div className="text-white font-bold text-xs">{biometrics.source}</div>
                  </div>
                </div>
              </div>
            )}

            {/* Workouts */}
            <div className="bg-gray-800 rounded-xl p-3">
              <h3 className="text-emerald-400 font-semibold mb-2">
                Workouts ({workouts.length} en app / {hcRawWorkouts.length} en HC)
              </h3>
              
              {hcRawWorkouts.length === 0 && workouts.length === 0 ? (
                <div className="text-gray-500 text-sm italic">No hay workouts registrados</div>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {/* Workouts de HC */}
                  {hcRawWorkouts.map((w, i) => (
                    <div key={`hc-${i}`} className="bg-emerald-900/30 border border-emerald-700/30 rounded-lg p-2 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-emerald-300">{w.title}</span>
                        <span className="text-xs text-emerald-500">HEALTH_CONNECT</span>
                      </div>
                      <div className="text-gray-400 text-xs mt-1">
                        {w.exerciseType} • {Math.round(w.duration / 60)} min • {Math.round(w.calories)} kcal
                        {w.steps ? ` • ${w.steps} pasos` : ''}
                      </div>
                      <div className="text-gray-500 text-xs">
                        {new Date(w.startTime).toLocaleString()}
                      </div>
                    </div>
                  ))}
                  
                  {/* Workouts de la app */}
                  {workouts.map((w, i) => (
                    <div key={`app-${i}`} className="bg-gray-700/50 rounded-lg p-2 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-gray-300">{w.name}</span>
                        <span className="text-xs text-gray-500">{w.source}</span>
                      </div>
                      <div className="text-gray-400 text-xs">{w.description}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Logs */}
            <div className="bg-gray-800 rounded-xl p-3">
              <h3 className="text-emerald-400 font-semibold mb-2">Logs</h3>
              <div className="bg-black rounded-lg p-2 font-mono text-xs h-32 overflow-y-auto">
                {logs.map((log, i) => (
                  <div key={i} className="text-gray-400 border-b border-gray-800 py-1">
                    {log}
                  </div>
                ))}
                {logs.length === 0 && (
                  <div className="text-gray-600 italic">Sin logs</div>
                )}
              </div>
            </div>

            {/* Botón para abrir Health Connect */}
            <button
              onClick={() => healthConnectService.openSettings()}
              className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-medium transition-colors"
            >
              Abrir Health Connect
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
