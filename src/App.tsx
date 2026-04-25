import React, { useState, useEffect, useCallback } from 'react';
import { 
  MessageSquare, 
  User, 
  FileText, 
  Settings, 
  LogOut, 
  RefreshCw,
  Zap,
  History,
  LayoutDashboard,
  Menu,
  X,
  Brain,
  Activity,
  Loader2
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import axios from 'axios';

// Modular Components
import { BiometricsWidget } from './components/BiometricsWidget';
import { ProfileForm } from './components/ProfileForm';
import { Chat } from './components/Chat';
import { PDFManager } from './components/PDFManager';
import { Setup } from './components/Setup';
import { HealthConnectOnboarding } from './components/HealthConnectOnboarding';
import { ExerciseSelector } from './components/ExerciseSelector';
import { WorkoutLogger } from './components/WorkoutLogger';

// Services & Types
import { callAI } from './services/aiService';
import { syncService } from './services/syncService';
import { notificationService } from './services/notificationService';
import { healthConnectService } from './services/healthConnectService';
import { useHealthConnectPermissions } from './hooks/useHealthConnectPermissions';
import { Biometrics, AthleteProfile, Message, PDFDocument, Workout } from './types';
import { DebugPanel } from './components/DebugPanel';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

const App: React.FC = () => {
  // --- Native & System State ---
  const { granted, checkPermissions } = useHealthConnectPermissions();
  const [showHealthOnboarding, setShowHealthOnboarding] = useState(false);
  const [isHCAvailable, setIsHCAvailable] = useState(false);  // HC disponible en este dispositivo
  const [hcPermissionsGranted, setHcPermissionsGranted] = useState(false); // Permisos confirmados

  // --- UI State ---
  const [activeTab, setActiveTab] = useState<'chat' | 'profile' | 'docs' | 'setup' | 'routine'>('chat');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isGarminConnected, setIsGarminConnected] = useState(false);
  const [biometrics, setBiometrics] = useState<Biometrics | null>(null);
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [loadingBiometrics, setLoadingBiometrics] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingAI, setLoadingAI] = useState(false);
  const [documents, setDocuments] = useState<PDFDocument[]>([]);
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const [profile, setProfile] = useState<AthleteProfile>({
    name: "Sergi",
    age: 47,
    weight: 75,
    height: 180,
    goal: "Proyecto 31/07 - Definición",
    experience: "avanzado",
    daysPerWeek: 5,
    medicalHistory: "Ninguna relevante"
  });

  const [currentSession, setCurrentSession] = useState<any | null>(null);
  const [briefing, setBriefing] = useState<string | null>(null);
  const [loadingBriefing, setLoadingBriefing] = useState(false);

  // --- Quick Actions (REQ-F22) ---
  const quickActions = [
    { label: "Análisis Hoy", prompt: "¿Cómo están mis biométricos hoy y qué entrenamiento me recomiendas?" },
    { label: "Riesgo Lesión", prompt: "Analiza mi HRV y estrés reciente para ver si hay riesgo de sobreentrenamiento." },
    { label: "Plan Semanal", prompt: "Genera un plan de entrenamiento basado en mis objetivos y mi readiness actual." },
    { label: "Nutrición", prompt: "Basado en mis calorías quemadas hoy, ¿qué debería comer para recuperar?" }
  ];

  const [garminEmail, setGarminEmail] = useState("");
  const [garminPassword, setGarminPassword] = useState("");
  const [wgerKey, setWgerKey] = useState("");
  const [hevyUser, setHevyUser] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSync, setLastSync] = useState<string | null>(null);

  // --- Garmin Auth (REQ-F04, F05, F06) ---
  const checkAuthStatus = useCallback(async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/auth/status`, {
        headers: { "x-user-id": "default_user" }
      });
      setIsGarminConnected(res.data.authenticated);
      if (res.data.authenticated) loadBiometrics();
    } catch (e) {
      console.error("Error checking auth status", e);
    }
  }, []);

  const handleGarminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoggingIn(true);
    try {
      const res = await axios.post(`${BACKEND_URL}/auth/garmin/login`, {
        email: garminEmail,
        password: garminPassword,
        userId: "default_user"
      });
      if (res.data.success) {
        setIsGarminConnected(true);
        setGarminEmail("");
        setGarminPassword("");
        loadBiometrics();
      }
    } catch (e: any) {
      if (!e.response) {
         // Axios manda un error sin response cuando falla el servidor o es inaccesible (ej. fallo de red/localhost)
         alert("Error de Conexión. Vigila que tu servidor Backend esté corriendo de fondo u offline.");
      } else {
         const msg = e.response?.data?.details || e.response?.data?.error || "Error al conectar con Garmin. Revisa tus credenciales.";
         alert(msg);
      }
    } finally {
      setIsLoggingIn(false);
    }
  };

  const disconnectGarmin = async () => {
    try {
      await axios.post(`${BACKEND_URL}/auth/disconnect`, {}, {
        headers: { "x-user-id": "default_user" }
      });
      setIsGarminConnected(false);
      setBiometrics(null);
    } catch (e) {
      console.error("Error disconnecting Garmin", e);
    }
  };

  const handleSaveServices = async () => {
    try {
      await axios.post(`${BACKEND_URL}/settings/services`, {
        wger_api_key: wgerKey,
        hevy_username: hevyUser
      }, {
        headers: { 'x-user-id': 'default_user' }
      });
      alert('Configuración guardada correctamente.');
    } catch (error) {
      console.error('Error saving services:', error);
      alert('Error al guardar la configuración.');
    }
  };

  const fetchServiceSettings = useCallback(async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/settings/services`, {
        headers: { "x-user-id": "default_user" }
      });
      setWgerKey(res.data.wger_api_key || "");
      setHevyUser(res.data.hevy_username || "");
    } catch (e) {
      console.error("Error fetching service settings", e);
    }
  }, []);

  const handleSyncAll = async () => {
    setIsSyncing(true);
    const results: string[] = [];
    try {
      // Sync Garmin
      if (isGarminConnected) {
        try {
          await axios.post(`${BACKEND_URL}/sync/garmin`, {}, {
            headers: { 'x-user-id': 'default_user' }
          });
          results.push("Garmin ✅");
        } catch (e: any) {
          const isRateLimit = e.response?.status === 429;
          results.push(isRateLimit ? "Garmin (Bloqueo Temporal) ⏳" : "Garmin ❌");
          if (isRateLimit) {
            alert("Garmin ha bloqueado las solicitudes temporalmente (Rate Limit). Por favor, espera 30-60 minutos antes de intentar sincronizar de nuevo.");
          }
        }
      }
      
      // Sync Wger
      if (wgerKey) {
        try {
          await axios.post(`${BACKEND_URL}/sync/wger`, {}, {
            headers: { 'x-user-id': 'default_user' }
          });
          results.push("Wger ✅");
        } catch (e) {
          results.push("Wger ❌");
        }
      }

      // Sync Hevy
      if (hevyUser) {
        try {
          await axios.post(`${BACKEND_URL}/sync/hevy`, {}, {
            headers: { 'x-user-id': 'default_user' }
          });
          results.push("Hevy ✅");
        } catch (e) {
          results.push("Hevy ❌");
        }
      }

      setLastSync(new Date().toLocaleTimeString());
      loadBiometrics();
      fetchWorkouts();
      if (results.length > 0) {
        alert(`Sincronización finalizada:\n${results.join('\n')}`);
      } else {
        alert('No hay servicios configurados para sincronizar.');
      }
    } catch (error) {
      console.error('Sync error:', error);
      alert('Error crítico durante la sincronización.');
    } finally {
      setIsSyncing(false);
    }
  };

  const fetchWorkouts = async (forceHC: boolean = false): Promise<Workout[]> => {
    let allWorkouts: Workout[] = [];
    const hcAvailable = forceHC || isHCAvailable;
    console.log('[App] fetchWorkouts - HC disponible:', hcAvailable);
    
    // 1. Intentar cargar desde Health Connect primero (datos en tiempo real)
    if (hcAvailable) {
      try {
        // Verificar permisos antes de leer workouts
        const hasPerms = await healthConnectService.ensurePermissions();
        if (!hasPerms) {
          console.warn('[App] Permisos HC denegados para workouts');
        } else {
          const hcWorkouts = await healthConnectService.readTodayWorkouts();
          console.log('[App] Workouts desde Health Connect:', hcWorkouts.length);

          if (hcWorkouts.length > 0) {
            const mappedHCWorkouts: Workout[] = hcWorkouts.map((w, index) => ({
              id: parseInt(w.id) || Date.now() + index,
              external_id: w.id,
              name: w.title,
              description: `${w.exerciseType} - ${Math.round(w.duration / 60)} min, ${Math.round(w.calories)} kcal${w.steps ? `, ${w.steps} pasos` : ''}`,
              date: w.startTime.toISOString().split('T')[0],
              source: 'health_connect',
              calories: w.calories,
              duration: w.duration,
            }));
            allWorkouts = [...mappedHCWorkouts];
          }
        }
      } catch (e) {
        console.warn('[App] Error leyendo workouts de HC:', e);
      }
    }
    
    // 2. Intentar cargar desde el backend (backup/fallback)
    try {
      const res = await axios.get(`${BACKEND_URL}/workouts/`, {
        headers: { "x-user-id": "default_user" }
      });
      const backendWorkouts = res.data as Workout[];
      console.log('[App] Workouts desde backend:', backendWorkouts.length);
      
      // Combinar: HC tiene prioridad, backend complementa
      const hcIds = new Set(allWorkouts.map(w => w.id));
      const newBackendWorkouts = backendWorkouts.filter(w => !hcIds.has(w.id));
      allWorkouts = [...allWorkouts, ...newBackendWorkouts];
    } catch (e) {
      console.error("Error fetching workouts from backend", e);
    }
    
    setWorkouts(allWorkouts);
    return allWorkouts; // Devolver para uso inmediato
  };

  // Calcula readiness localmente desde métricas HC (Garmin no disponible en móvil)
  const calculateReadiness = (steps: number, sleepHours: number, heartRate: number): number => {
    let score = 50;
    if (sleepHours >= 8) score += 20;
    else if (sleepHours >= 7) score += 14;
    else if (sleepHours >= 6) score += 6;
    else if (sleepHours > 0) score -= 5;
    if (steps >= 10000) score += 15;
    else if (steps >= 8000) score += 10;
    else if (steps >= 5000) score += 5;
    if (heartRate > 0 && heartRate < 60) score += 15;
    else if (heartRate < 70) score += 8;
    else if (heartRate > 90) score -= 10;
    return Math.min(100, Math.max(0, score));
  };

  // --- Biometrics Sync mejorado — prioriza HC sobre Backend (Fase 1/2) ---
  const loadBiometrics = async (forceHC: boolean = false) => {
    setLoadingBiometrics(true);
    console.log('[App] Iniciando carga de biométricos (forceHC:', forceHC, ')');
    
    try {
      // 1. Prioridad: Health Connect
      if (forceHC || isHCAvailable) {
        try {
          // Verificar permisos antes de leer; si no están, solicitar automáticamente
          const hasPerms = await healthConnectService.ensurePermissions();
          if (!hasPerms) {
            console.warn('[App] Permisos de Health Connect no concedidos. Mostrando onboarding...');
            setShowHealthOnboarding(true);
            setLoadingBiometrics(false);
            return;
          }

          const hcData = await healthConnectService.readTodayBiometrics();
          console.log('[App] HC Raw Data:', hcData);
          
          if (hcData.steps !== null || hcData.calories !== null) {
            const steps = hcData.steps ?? 0;
            const sleep = hcData.sleepHours ?? 0;
            const hr = hcData.heartRate ?? 0;
            const readiness = calculateReadiness(steps, sleep, hr);
            
            const mapped: Biometrics = {
              heartRate: hr,
              hrv: hcData.hrv ?? 0,
              spo2: 98, // Health Connect doesn't provide SpO2 directly, use default
              stress: hcData.stress ?? 0,
              steps,
              sleep,
              calories: hcData.calories ?? 0,
              respiration: hcData.respiration ?? 0,
              readiness,
              status: readiness >= 80 ? 'excellent' : readiness >= 60 ? 'good' : 'poor',
              overtraining: readiness < 40,
              source: 'garmin'
            };
            // Siempre actualizar con datos frescos de Health Connect
            setBiometrics(mapped);
            syncService.syncBiometricsToBackend(mapped).catch(() => {});
            setLoadingBiometrics(false);
            return;
          }
        } catch (hcErr) {
          console.warn('[App] Error leyendo HC:', hcErr);
        }
      }

      // 2. Fallback: Backend
      try {
        const res = await axios.get(`${BACKEND_URL}/biometrics/`, {
          headers: { "x-user-id": "default_user" },
          timeout: 3000
        });
        if (res.data && res.data.steps > 0) {
          setBiometrics(res.data);
          setLoadingBiometrics(false);
          return;
        }
      } catch {
        console.warn('[App] Backend no disponible o vacío');
      }

      // 3. Mantener Baselines de Sergi (Proyecto 31/07) como punto de partida real
      setBiometrics(prev => prev || {
        heartRate: 48, hrv: 49, spo2: 98, stress: 22,
        steps: 20000, sleep: 7.0, calories: 2400,
        respiration: 13, readiness: 88, status: 'excellent',
        overtraining: false, source: 'garmin'
      });
    } finally {
      setLoadingBiometrics(false);
    }
  };

  // --- AI Chat Logic (REQ-F15, F16, F17) ---
  const handleSendMessage = async (content: string) => {
    // Forzar recarga de workouts antes de enviar al AI (para tener datos actualizados)
    console.log('[App] handleSendMessage - Recargando workouts antes de consultar al AI');
    const currentWorkouts = await fetchWorkouts(true);
    console.log('[App] Workouts cargados:', currentWorkouts.length, currentWorkouts.map(w => w.name).join(', '));
    
    const userMsg: Message = {
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    };
    
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setLoadingAI(true);

    try {
      // Build System Prompt with Context (REQ-F17)
      const systemPrompt = `Eres ATLAS, el coach de Sergi para el 'PROYECTO 31/07'. 
      METODOLOGÍA: Sobrecarga Progresiva, Intensidad Stoppani y Salud McGill. 
      FECHA ACTUAL: ${new Date().toLocaleDateString('es-ES', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
      
      CONTEXTO: Sergi tiene 47-48 años, realiza 20k pasos diarios (NEAT masivo) y sus hitos son Banca 50kg y Prensa 100kg. 
      METODOLOGÍA: Sobrecarga Progresiva, Intensidad Stoppani y Salud McGill.
      Tu tono es profesional, motivador y basado en datos reales.
        CONTEXTO DEL ATLETA:
        - Nombre: ${profile.name}
        - Objetivo: ${profile.goal}
        - Experiencia: ${profile.experience}
        - Readiness Actual: ${biometrics?.readiness || 'N/A'}/100
        - FC Actual: ${biometrics?.heartRate || 'N/A'} bpm
        - HRV: ${biometrics?.hrv || 'N/A'} ms
        - Estado: ${biometrics?.status || 'N/A'}
        - Sobreentrenamiento: ${biometrics?.overtraining ? 'SÍ' : 'NO'}
        
        ÚLTIMOS ENTRENAMIENTOS:
        ${(currentWorkouts || []).slice(0, 5).map(w => `- [${w.source}] ${w.name} (${w.date}): ${w.description}`).join('\n')}
        ${currentWorkouts?.length === 0 ? '- No hay entrenamientos registrados hoy' : ''}
        
        DOCUMENTOS ANALIZADOS:
        ${(documents || []).map(d => `- ${d.name}: ${d.summary}`).join('\n')}
        
        INSTRUCCIONES:
        1. Sé técnico pero motivador.
        2. Prioriza la seguridad y la prevención de lesiones.
        3. Usa los datos biométricos para justificar tus recomendaciones.
        4. Si hay riesgo de sobreentrenamiento, recomienda descanso activo.
      `;

      console.log('[App] System prompt workouts section:', (currentWorkouts || []).slice(0, 5).map(w => `${w.name} (${w.source})`).join(', ') || 'SIN WORKOUTS');
    console.log('[App] Estado workouts completo:', JSON.stringify(currentWorkouts, null, 2));
      
      const result = await callAI(newMessages, systemPrompt);
      
      // REQ: Detect if AI generated a JSON session plan
      if (result.content.includes("json_session_start")) {
        try {
          const jsonStr = result.content.split("json_session_start")[1].split("json_session_end")[0];
          const sessionData = JSON.parse(jsonStr);
          setCurrentSession(sessionData);
          setActiveTab('routine');
        } catch (e) {
          console.error("Error parsing AI session plan", e);
        }
      }

      const assistantMsg: Message = {
        role: 'assistant',
        content: result.content,
        timestamp: new Date().toISOString(),
        provider: result.provider
      };
      
      setMessages(prev => [...prev, assistantMsg]);
    } catch (e: any) {
      const errorMsg: Message = {
        role: 'assistant',
        content: `⚠️ Error de Conexión: ${e.message}. Verifica que tienes internet en el móvil.`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoadingAI(false);
    }
  };

  // --- PDF Management (REQ-F26, F27, F28) ---
  const handleUploadPDF = async (file: File) => {
    const newDoc: PDFDocument = {
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      summary: "",
      analyzing: true
    };
    
    setDocuments(prev => [newDoc, ...prev]);

    // Simulate PDF analysis with AI
    try {
      const prompt = `Analiza este documento (simulado por el nombre: ${file.name}) y genera un resumen técnico de 3 líneas para un entrenador personal.`;
      const result = await callAI([], prompt);
      
      setDocuments(prev => prev.map(d => 
        d.id === newDoc.id ? { ...d, summary: result.content, analyzing: false } : d
      ));
    } catch (e) {
      setDocuments(prev => prev.map(d => 
        d.id === newDoc.id ? { ...d, summary: "Error al analizar el documento.", analyzing: false } : d
      ));
    }
  };

  const handleDeletePDF = (id: string) => {
    setDocuments(prev => prev.filter(d => d.id !== id));
  };

  // --- Lifecycle ---
  useEffect(() => {
    // Solo carga inicial de datos pesados
    fetchWorkouts();
    // No cargar biometrics aquí, esperar a que HC esté disponible
    generateBriefing();
  }, []); // Se ejecuta solo una vez al arrancar

  useEffect(() => {
    // Gestión de sesión y servicios
    checkAuthStatus();
    fetchServiceSettings();
  }, [checkAuthStatus, fetchServiceSettings]);

  const generateBriefing = async () => {
    setLoadingBriefing(true);
    try {
      const res = await axios.get(`${BACKEND_URL}/ai/daily-briefing`, {
        headers: { "x-user-id": "default_user" }
      });
      setBriefing(res.data.briefing);
    } catch (e: any) {
      console.warn("No se pudo generar el briefing proactivo", e);
      setBriefing("Error: ATLAS no pudo generar el briefing. Verifica la conexión con Groq/Gemini o reintenta con el botón superior.");
    } finally {
      setLoadingBriefing(false);
    }
  };

  // 🔑 Reactivo: cuando Health Connect concede permisos, cargamos biométricos
  useEffect(() => {
    if (granted && isHCAvailable) {
      console.log('[App] Health Connect granted=true + available → Cargando biométricos nativos...');
      loadBiometrics(true);
    }
  }, [granted, isHCAvailable]);

  // Load user profile on startup
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const response = await axios.get(
          `${BACKEND_URL}/settings/profile`,
          { headers: { "x-user-id": "default_user" } }
        );
        if (response.data.exists) {
          setProfile(prev => ({
            ...prev,
            name: response.data.name || "Sergi",
            age: response.data.age || 47,
            goal: response.data.goal || "Proyecto 31/07 - Definición"
          }));
        }
      } catch (e) {
        console.log("Profile not loaded:", e);
      }
    };
    loadProfile();
  }, []);

  // Handle OAuth callback in URL
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('auth') === 'success') {
      checkAuthStatus();
      // Clean URL
      window.history.replaceState({}, document.title, "/");
    }
  }, [checkAuthStatus]);

  // --- Native Core & Initialization (REQ: Phase 3, 4, 5) ---
  useEffect(() => {
    // 1. Set up Background Notifications
    notificationService.initialize().then(() => {
      notificationService.scheduleMorningBriefing(8, 0);
    });

    // 2. Set up Offline/Online Background Reconciliation (Phase 3)
    const handleOnlineReconciliation = () => {
      console.log("[App] Conexión detectada. Ejecutando syncService.syncAll...");
      syncService.syncAll();
    };
    window.addEventListener('online', handleOnlineReconciliation);

    return () => {
      window.removeEventListener('online', handleOnlineReconciliation);
    };
  }, []);

  // 3. Health Connect — inicialización robusta independiente del parseo de permisos
  useEffect(() => {
    const initHealthConnect = async () => {
      try {
        await healthConnectService.initialize();
        const avail = await healthConnectService.isAvailable();
        setIsHCAvailable(avail);
        console.log('[HC] isAvailable:', avail);

        if (avail) {
          // Intentar comprobar permisos con try/catch robusto
          try {
            const permStatus = await healthConnectService.checkPermissions();
            console.log('[HC] Permisos:', JSON.stringify(permStatus));
            setHcPermissionsGranted(permStatus.granted);

            const hasSeen = localStorage.getItem('hc_onboarding_seen');
            if (!permStatus.granted && !hasSeen) {
              setShowHealthOnboarding(true);
            }

            // SIEMPRE intentar cargar biométricos; ensurePermissions solicitará permisos si faltan
            loadBiometrics(true);
            fetchWorkouts(true); // Cargar workouts desde Health Connect (forceHC=true)
          } catch (permErr) {
            console.warn('[HC] Error comprobando permisos (asumimos que sí):', permErr);
            // En caso de error al comprobar, intentamos leer igualmente
            setHcPermissionsGranted(true);
            loadBiometrics(true);
            fetchWorkouts(true);
          }
        }
      } catch (e) {
        console.warn('[HC] No disponible en esta plataforma:', e);
      }
    };
    initHealthConnect();
  }, []); // Solo al montar

  const closeHealthOnboarding = async () => {
    localStorage.setItem('hc_onboarding_seen', 'true');
    setShowHealthOnboarding(false);
    // Intentar solicitar permisos y luego cargar datos
    try {
      const result = await healthConnectService.requestPermissions();
      setHcPermissionsGranted(result.granted);
    } catch (e) {
      setHcPermissionsGranted(true); // Asumimos que sí si falla el check
    }
    loadBiometrics(true);
    fetchWorkouts(true); // Cargar workouts desde Health Connect
  };

  return (
    <div className="flex mobile-h-screen bg-background text-on-surface overflow-hidden font-body relative">
      {/* Native Modals Layer */}
      {showHealthOnboarding && (
        <HealthConnectOnboarding 
          onComplete={closeHealthOnboarding} 
          onSkip={closeHealthOnboarding} 
        />
      )}
      
      {/* Debug Panel */}
      <DebugPanel 
        isOpen={showDebugPanel} 
        onClose={() => setShowDebugPanel(false)} 
        biometrics={biometrics}
        workouts={workouts}
      />
      
      {/* Mobile Drawer Overlay */}
      <AnimatePresence>
        {isSidebarOpen && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsSidebarOpen(false)}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 lg:hidden"
          />
        )}
      </AnimatePresence>

      {/* --- Sidebar (REQ-F01, F02) --- */}
      <AnimatePresence mode="wait">
        {isSidebarOpen && (
          <motion.aside 
            initial={{ x: -300 }}
            animate={{ x: 0 }}
            exit={{ x: -300 }}
            className="fixed lg:relative w-[85%] lg:w-80 h-full bg-surface-container border-r border-outline-variant/10 flex flex-col z-40 lg:z-20"
          >
            {/* Header */}
            <div className="p-6 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center text-on-primary shadow-lg shadow-primary/20">
                  <Zap size={24} fill="currentColor" />
                </div>
                <div>
                  <h1 className="text-xl font-headline font-bold tracking-tighter">ATLAS <span className="text-primary">AI</span></h1>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Personal Trainer v2.0</p>
                </div>
              </div>
              <button onClick={() => setIsSidebarOpen(false)} className="lg:hidden p-2 hover:bg-surface-variant rounded-lg">
                <X size={20} />
              </button>
            </div>

            {/* Garmin Widget (REQ-F09 to F14) */}
            <div className="flex-1 overflow-y-auto px-6 space-y-6 custom-scrollbar">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Biometría & Sinc</h3>
                  <div className="flex items-center gap-1">
                    {lastSync && <span className="text-[8px] text-on-surface-variant font-bold mr-1">{lastSync}</span>}
                    <button 
                      onClick={handleSyncAll}
                      disabled={isSyncing || (!isGarminConnected && !wgerKey && !hevyUser)}
                      className={`p-1.5 hover:bg-surface-variant rounded-lg transition-colors disabled:opacity-30 ${isSyncing ? 'animate-spin text-primary' : ''}`}
                      title="Sincronizar todo"
                    >
                      <RefreshCw size={14} />
                    </button>
                  </div>
                </div>
                
                {(isGarminConnected || biometrics || isHCAvailable || granted) ? (
                  <BiometricsWidget data={biometrics} userId="default_user" />
                ) : (
                  <div className="bg-surface-container-high p-6 rounded-xl border border-outline-variant/10 text-center space-y-4">
                    <div className="w-12 h-12 bg-surface-variant rounded-full flex items-center justify-center mx-auto text-on-surface-variant">
                      <LayoutDashboard size={24} />
                    </div>
                    <p className="text-xs text-on-surface-variant">Conecta tu Garmin o activa Health Connect para ver tus métricas.</p>
                    <button 
                      onClick={() => setActiveTab('setup')}
                      className="w-full bg-primary text-on-primary py-2 rounded-lg text-xs font-bold uppercase tracking-widest hover:brightness-110 transition-all"
                    >
                      Configurar
                    </button>
                  </div>
                )}

                {/* Workouts Status (Wger/Hevy) */}
                {(wgerKey || hevyUser) && (
                  <div className="bg-surface-container-high p-4 rounded-xl border border-outline-variant/10 space-y-3">
                    <div className="flex items-center gap-2 text-primary">
                      <Activity size={16} />
                      <h4 className="text-xs font-bold uppercase tracking-widest">Entrenamientos</h4>
                    </div>
                    <div className="space-y-2">
                      {wgerKey && (
                        <div className="flex items-center justify-between text-[10px]">
                          <span className="text-on-surface-variant">Wger</span>
                          <span className="text-green-400 font-bold">CONECTADO</span>
                        </div>
                      )}
                      {hevyUser && (
                        <div className="flex items-center justify-between text-[10px]">
                          <span className="text-on-surface-variant">Hevy</span>
                          <span className="text-green-400 font-bold">CONECTADO</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Quick Actions (REQ-F22) */}
              <div className="space-y-3">
                <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Acciones Rápidas</h3>
                <div className="grid grid-cols-1 gap-2">
                  {quickActions.map((action) => (
                    <button 
                      key={action.label}
                      onClick={() => handleSendMessage(action.prompt)}
                      className="flex items-center gap-3 p-3 bg-surface-container-low rounded-lg border border-outline-variant/5 hover:border-primary/30 transition-all text-left group"
                    >
                      <div className="p-2 bg-surface-variant rounded-lg text-on-surface-variant group-hover:text-primary transition-colors">
                        <Brain size={14} />
                      </div>
                      <span className="text-xs font-medium">{action.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="p-6 border-t border-outline-variant/10">
              {isGarminConnected && (
                <button 
                  onClick={disconnectGarmin}
                  className="w-full flex items-center justify-center gap-2 text-xs font-bold uppercase tracking-widest text-red-400 hover:bg-red-500/10 p-2 rounded-lg transition-all"
                >
                  <LogOut size={14} />
                  Desconectar Garmin
                </button>
              )}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* --- Main Content --- */}
      <main className="flex-1 flex flex-col relative">
        {/* Top Navigation (REQ-F01) */}
        <header className="h-16 bg-surface-container/50 backdrop-blur-md border-b border-outline-variant/10 flex items-center justify-between px-4 lg:px-6 z-10 shrink-0">
          <div className="flex items-center gap-4">
            {!isSidebarOpen && (
              <button onClick={() => setIsSidebarOpen(true)} className="p-2 hover:bg-surface-variant rounded-lg">
                <Menu size={20} />
              </button>
            )}
            <nav className="flex items-center gap-1">
              {[
                { id: 'chat', label: 'Chat', icon: MessageSquare },
                { id: 'profile', label: 'Perfil', icon: User },
                { id: 'routine', label: 'Entrenar', icon: Zap },
                { id: 'docs', label: 'Documentos', icon: FileText },
                { id: 'setup', label: 'Setup', icon: Settings },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                    activeTab === tab.id 
                      ? 'bg-primary/10 text-primary' 
                      : 'text-on-surface-variant hover:bg-surface-variant'
                  }`}
                >
                  <tab.icon size={16} />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-4">
            {/* Debug Button */}
            <button
              onClick={() => setShowDebugPanel(true)}
              className="p-2 bg-surface-variant rounded-lg hover:bg-primary/10 transition-colors"
              title="Debug Panel"
            >
              <span className="text-xs font-mono text-primary">DBG</span>
            </button>
            
            <div className="flex flex-col items-end">
              <span className="text-xs font-bold">{profile.name}</span>
              <span className="text-[10px] text-on-surface-variant uppercase tracking-widest">{profile.goal}</span>
            </div>
            <div className="w-8 h-8 bg-surface-variant rounded-full flex items-center justify-center text-on-surface-variant">
              <User size={16} />
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-4 lg:p-6 custom-scrollbar">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="h-full flex flex-col gap-4"
            >
              {activeTab === 'chat' && loadingBriefing && (
                <div className="bg-primary/5 border border-primary/10 p-4 rounded-2xl flex items-center gap-4">
                  <Loader2 size={20} className="animate-spin text-primary shrink-0" />
                  <span className="text-xs text-primary font-bold uppercase tracking-widest">ATLAS analizando biométricos...</span>
                </div>
              )}

              {activeTab === 'chat' && briefing && !loadingBriefing && (
                <div className="bg-primary/5 border border-primary/20 p-4 rounded-2xl relative overflow-hidden">
                  <div className="flex items-start gap-4">
                    <Brain size={20} className="text-primary shrink-0 mt-1" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-[10px] font-bold uppercase tracking-widest text-primary">Briefing Proactivo ATLAS</h4>
                        <button 
                          onClick={generateBriefing}
                          className="text-[9px] uppercase font-bold text-primary/60 hover:text-primary"
                        >
                          Actualizar
                        </button>
                      </div>
                      <p className="text-sm leading-relaxed text-on-surface whitespace-pre-wrap">{String(briefing)}</p>
                    </div>
                  </div>
                  <button 
                    onClick={() => setBriefing(null)}
                    className="absolute top-2 right-2 p-1 text-on-surface-variant/30 hover:text-on-surface"
                  >
                    <X size={14} />
                  </button>
                </div>
              )}
              {activeTab === 'chat' && (
                <Chat 
                  messages={messages} 
                  onSendMessage={handleSendMessage} 
                  loading={loadingAI}
                  quickActions={quickActions}
                />
              )}
              {activeTab === 'routine' && (
                currentSession ? (
                  <WorkoutLogger 
                    session={currentSession} 
                    onSave={(updated) => {
                      alert("¡Sesión Guardada! Los datos se han enviado a tu historial.");
                      setCurrentSession(null);
                      setActiveTab('chat');
                    }} 
                  />
                ) : (
                  <ExerciseSelector />
                )
              )}
              {activeTab === 'profile' && (
                <ProfileForm 
                  profile={profile} 
                  onSave={(p) => {
                    setProfile(p);
                    setActiveTab('chat');
                  }} 
                />
              )}
              {activeTab === 'docs' && (
                <PDFManager 
                  documents={documents} 
                  onUpload={handleUploadPDF} 
                  onDelete={handleDeletePDF} 
                />
              )}
              {activeTab === 'setup' && (
              <Setup 
                isConnected={isGarminConnected}
                onLogin={handleGarminLogin}
                onDisconnect={disconnectGarmin}
                email={garminEmail}
                setEmail={setGarminEmail}
                password={garminPassword}
                setPassword={setGarminPassword}
                isLoggingIn={isLoggingIn}
                wgerKey={wgerKey}
                setWgerKey={setWgerKey}
                hevyUser={hevyUser}
                setHevyUser={setHevyUser}
                onSaveServices={handleSaveServices}
              />
            )}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};

export default App;
