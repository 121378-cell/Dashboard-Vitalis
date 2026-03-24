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
  Activity
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import axios from 'axios';

// Modular Components
import { BiometricsWidget } from './components/BiometricsWidget';
import { ProfileForm } from './components/ProfileForm';
import { Chat } from './components/Chat';
import { PDFManager } from './components/PDFManager';
import { Setup } from './components/Setup';

// Services & Types
import { callAI } from './services/aiService';
import { Biometrics, AthleteProfile, Message, PDFDocument, Workout } from './types';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

const App: React.FC = () => {
  // --- State ---
  const [activeTab, setActiveTab] = useState<'chat' | 'profile' | 'docs' | 'setup'>('chat');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isGarminConnected, setIsGarminConnected] = useState(false);
  const [biometrics, setBiometrics] = useState<Biometrics | null>(null);
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [loadingBiometrics, setLoadingBiometrics] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingAI, setLoadingAI] = useState(false);
  const [documents, setDocuments] = useState<PDFDocument[]>([]);
  const [profile, setProfile] = useState<AthleteProfile>({
    name: "Atleta ATLAS",
    age: 30,
    weight: 75,
    height: 180,
    goal: "Rendimiento deportivo",
    experience: "intermedio",
    daysPerWeek: 4,
    medicalHistory: "Ninguna relevante"
  });

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
      if (res.data.authenticated) fetchBiometrics();
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
        fetchBiometrics();
      }
    } catch (e: any) {
      const msg = e.response?.data?.details || e.response?.data?.error || "Error al conectar con Garmin. Revisa tus credenciales.";
      alert(msg);
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
      await axios.post(`${BACKEND_URL}/api/settings/services`, {
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
      const res = await axios.get(`${BACKEND_URL}/api/settings/services`, {
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
          await axios.post(`${BACKEND_URL}/api/sync/garmin`, {}, {
            headers: { 'x-user-id': 'default_user' }
          });
          results.push("Garmin ✅");
        } catch (e) {
          results.push("Garmin ❌");
        }
      }
      
      // Sync Wger
      if (wgerKey) {
        try {
          await axios.post(`${BACKEND_URL}/api/sync/wger`, {}, {
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
          await axios.post(`${BACKEND_URL}/api/sync/hevy`, {}, {
            headers: { 'x-user-id': 'default_user' }
          });
          results.push("Hevy ✅");
        } catch (e) {
          results.push("Hevy ❌");
        }
      }

      setLastSync(new Date().toLocaleTimeString());
      fetchBiometrics();
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

  const fetchWorkouts = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/workouts`, {
        headers: { "x-user-id": "default_user" }
      });
      setWorkouts(res.data);
    } catch (e) {
      console.error("Error fetching workouts", e);
    }
  };

  // --- Biometrics Sync (REQ-F07, F08) ---
  const fetchBiometrics = async () => {
    setLoadingBiometrics(true);
    try {
      const res = await axios.get(`${BACKEND_URL}/api/biometrics`, {
        headers: { "x-user-id": "default_user" }
      });
      setBiometrics(res.data);
    } catch (e) {
      console.error("Error fetching biometrics", e);
    } finally {
      setLoadingBiometrics(false);
    }
  };

  // --- AI Chat Logic (REQ-F15, F16, F17) ---
  const handleSendMessage = async (content: string) => {
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
      const systemPrompt = `
        Eres ATLAS, un entrenador de élite con IA. 
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
        ${workouts.slice(0, 5).map(w => `- [${w.source}] ${w.name} (${w.date}): ${w.description}`).join('\n')}
        
        DOCUMENTOS ANALIZADOS:
        ${documents.map(d => `- ${d.name}: ${d.summary}`).join('\n')}
        
        INSTRUCCIONES:
        1. Sé técnico pero motivador.
        2. Prioriza la seguridad y la prevención de lesiones.
        3. Usa los datos biométricos para justificar tus recomendaciones.
        4. Si hay riesgo de sobreentrenamiento, recomienda descanso activo.
      `;

      const result = await callAI(newMessages, systemPrompt);
      
      const assistantMsg: Message = {
        role: 'assistant',
        content: result.content,
        timestamp: new Date().toISOString(),
        provider: result.provider
      };
      
      setMessages(prev => [...prev, assistantMsg]);
    } catch (e) {
      const errorMsg: Message = {
        role: 'assistant',
        content: "Lo siento, he tenido un problema conectando con mis neuronas digitales. Por favor, inténtalo de nuevo.",
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
    checkAuthStatus();
    fetchServiceSettings();
    fetchWorkouts();
    // REQ-F07: Auto-sync every 5 minutes
    const interval = setInterval(fetchBiometrics, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [checkAuthStatus, fetchServiceSettings]);

  // Handle OAuth callback in URL
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('auth') === 'success') {
      checkAuthStatus();
      // Clean URL
      window.history.replaceState({}, document.title, "/");
    }
  }, [checkAuthStatus]);

  return (
    <div className="flex h-screen bg-background text-on-surface overflow-hidden font-body">
      {/* --- Sidebar (REQ-F01, F02) --- */}
      <AnimatePresence mode="wait">
        {isSidebarOpen && (
          <motion.aside 
            initial={{ x: -300 }}
            animate={{ x: 0 }}
            exit={{ x: -300 }}
            className="w-80 bg-surface-container border-r border-outline-variant/10 flex flex-col z-20"
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
                
                {isGarminConnected ? (
                  <BiometricsWidget data={biometrics} />
                ) : (
                  <div className="bg-surface-container-high p-6 rounded-xl border border-outline-variant/10 text-center space-y-4">
                    <div className="w-12 h-12 bg-surface-variant rounded-full flex items-center justify-center mx-auto text-on-surface-variant">
                      <LayoutDashboard size={24} />
                    </div>
                    <p className="text-xs text-on-surface-variant">Conecta tu Garmin para ver tus métricas en tiempo real.</p>
                    <button 
                      onClick={() => setActiveTab('setup')}
                      className="w-full bg-primary text-on-primary py-2 rounded-lg text-xs font-bold uppercase tracking-widest hover:brightness-110 transition-all"
                    >
                      Conectar Garmin
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
        <header className="h-16 bg-surface-container/50 backdrop-blur-md border-b border-outline-variant/10 flex items-center justify-between px-6 z-10">
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
        <div className="flex-1 overflow-hidden p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="h-full"
            >
              {activeTab === 'chat' && (
                <Chat 
                  messages={messages} 
                  onSendMessage={handleSendMessage} 
                  loading={loadingAI}
                  quickActions={quickActions}
                />
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
