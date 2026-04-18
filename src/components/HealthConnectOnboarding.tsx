/**
 * HealthConnectOnboarding
 * 
 * Pantalla de onboarding para solicitar permisos de Health Connect.
 * Muestra qué datos se necesitarán y gestiona el flujo de permisos.
 */

import { useState, useEffect } from 'react';
import { healthConnectService } from '../services/healthConnectService';
import { syncService } from '../services/syncService';

// ============================================================================
// TYPES
// ============================================================================

interface HealthConnectOnboardingProps {
  onComplete: () => void;
  onSkip?: () => void;
}

interface PermissionState {
  isChecking: boolean;
  isAvailable: boolean;
  isGranted: boolean;
  permissions: { [key: string]: boolean };
  error: string | null;
}

// ============================================================================
// COMPONENT
// ============================================================================

export function HealthConnectOnboarding({ onComplete, onSkip }: HealthConnectOnboardingProps) {
  const [state, setState] = useState<PermissionState>({
    isChecking: true,
    isAvailable: false,
    isGranted: false,
    permissions: {},
    error: null,
  });

  // ========================================================================
  // CHECK INITIAL STATE
  // ========================================================================

  useEffect(() => {
    checkHealthConnect();
  }, []);

  const checkHealthConnect = async () => {
    setState(prev => ({ ...prev, isChecking: true, error: null }));

    try {
      // Inicializar el servicio
      await healthConnectService.initialize();

      // Verificar disponibilidad
      const available = await healthConnectService.isAvailable();

      if (!available) {
        setState({
          isChecking: false,
          isAvailable: false,
          isGranted: false,
          permissions: {},
          error: 'Health Connect no está disponible en este dispositivo',
        });
        return;
      }

      // Verificar permisos
      const permissionStatus = await healthConnectService.checkPermissions();

      setState({
        isChecking: false,
        isAvailable: true,
        isGranted: permissionStatus.granted,
        permissions: permissionStatus.permissions,
        error: null,
      });

      // Si ya tiene permisos, continuar
      if (permissionStatus.granted) {
        onComplete();
      }
    } catch (error) {
      setState({
        isChecking: false,
        isAvailable: false,
        isGranted: false,
        permissions: {},
        error: error instanceof Error ? error.message : 'Error desconocido',
      });
    }
  };

  // ========================================================================
  // REQUEST PERMISSIONS
  // ========================================================================

  const handleRequestPermissions = async () => {
    setState(prev => ({ ...prev, isChecking: true, error: null }));

    try {
      const result = await healthConnectService.requestPermissions();

      if (result.granted) {
        // Iniciar sync en background
        syncService.startBackgroundSync();
        
        setState(prev => ({
          ...prev,
          isChecking: false,
          isGranted: true,
          permissions: result.permissions,
        }));

        onComplete();
      } else {
        setState(prev => ({
          ...prev,
          isChecking: false,
          isGranted: false,
          permissions: result.permissions,
          error: 'Permisos no concedidos completamente',
        }));
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        isChecking: false,
        error: error instanceof Error ? error.message : 'Error al solicitar permisos',
      }));
    }
  };

  const handleOpenSettings = async () => {
    await healthConnectService.openSettings();
  };

  const handleShowInPlayStore = async () => {
    await healthConnectService.showInPlayStore();
  };

  // ========================================================================
  // RENDER HELPERS
  // ============================================================================

  if (state.isChecking) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white p-6">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4" />
        <p className="text-gray-400">Verificando Health Connect...</p>
      </div>
    );
  }

  if (!state.isAvailable) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white p-6">
        <div className="text-6xl mb-6">📱</div>
        <h2 className="text-2xl font-bold mb-4">Health Connect no disponible</h2>
        <p className="text-gray-400 text-center max-w-md mb-6">
          {state.error || 'No se detectó Health Connect en este dispositivo. Instala Health Connect desde Google Play.'}
        </p>
        <button
          onClick={handleShowInPlayStore}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition-colors"
        >
          Instalar Health Connect
        </button>
        {onSkip && (
          <button
            onClick={onSkip}
            className="mt-4 text-gray-400 hover:text-white transition-colors"
          >
            Usar solo datos de Garmin
          </button>
        )}
      </div>
    );
  }

  // Pantalla de permisos
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white p-6">
      <div className="text-6xl mb-6">🏃</div>
      <h2 className="text-2xl font-bold mb-2">Conecta tu salud</h2>
      <p className="text-gray-400 text-center max-w-md mb-8">
        Para darte el mejor consejo, Vitalis necesita acceso a tus datos de salud
      </p>

      {/* Lista de permisos */}
      <div className="w-full max-w-md bg-gray-800 rounded-xl p-6 mb-8">
        <div className="space-y-4">
          <PermissionItem
            icon="❤️"
            label="Ritmo cardíaco"
            description="Frecuencia cardíaca y variabilidad"
            granted={state.permissions['READ_HEART_RATE']}
          />
          <PermissionItem
            icon="😴"
            label="Sueño"
            description="Duración y calidad del descanso"
            granted={state.permissions['READ_WORKOUTS']}
          />
          <PermissionItem
            icon="👟"
            label="Pasos"
            description="Actividad diaria y ejercicio"
            granted={state.permissions['READ_STEPS']}
          />
          <PermissionItem
            icon="🔥"
            label="Calorías"
            description="Calorías activas y totales"
            granted={state.permissions['READ_TOTAL_CALORIES']}
          />
          <PermissionItem
            icon="📊"
            label="Entrenamientos"
            description="Ejercicios completados"
            granted={state.permissions['READ_WORKOUTS']}
          />
        </div>
      </div>

      {state.error && (
        <div className="w-full max-w-md bg-red-900/50 border border-red-700 rounded-lg p-4 mb-6">
          <p className="text-red-400 text-sm">{state.error}</p>
        </div>
      )}

      {/* Botones de acción */}
      <div className="w-full max-w-md space-y-3">
        <button
          onClick={handleRequestPermissions}
          className="w-full px-6 py-4 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold text-lg transition-colors"
        >
          Conectar Health Connect
        </button>

        <div className="flex items-center justify-center">
          <span className="text-gray-500 text-sm">ó</span>
        </div>

        {onSkip && (
          <button
            onClick={onSkip}
            className="w-full px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium transition-colors"
          >
            Usar solo Garmin
          </button>
        )}

        <button
          onClick={handleOpenSettings}
          className="w-full text-gray-500 hover:text-gray-300 text-sm transition-colors py-2"
        >
          Abrir configuración de Health Connect
        </button>
      </div>

      <p className="text-gray-600 text-xs mt-8 text-center max-w-md">
        Vitalis solo lee datos de tu salud. No almacenamos ni compartimos tu información personal.
      </p>
    </div>
  );
}

// ============================================================================
// HELPER: Permission Item
// ============================================================================

function PermissionItem({
  icon,
  label,
  description,
  granted,
}: {
  icon: string;
  label: string;
  description: string;
  granted?: boolean;
}) {
  return (
    <div className="flex items-center gap-4">
      <div className="text-2xl">{icon}</div>
      <div className="flex-1">
        <div className="font-medium">{label}</div>
        <div className="text-sm text-gray-500">{description}</div>
      </div>
      <div className={`text-lg ${granted ? 'text-green-500' : 'text-gray-600'}`}>
        {granted ? '✓' : '○'}
      </div>
    </div>
  );
}

export default HealthConnectOnboarding;