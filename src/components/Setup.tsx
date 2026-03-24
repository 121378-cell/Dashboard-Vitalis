import React from 'react';
import { ShieldCheck, Server, Globe, Smartphone, LogIn, LogOut, Loader2 } from 'lucide-react';

interface SetupProps {
  isConnected: boolean;
  onLogin: (e: React.FormEvent) => void;
  onDisconnect: () => void;
  email: string;
  setEmail: (val: string) => void;
  password: string;
  setPassword: (val: string) => void;
  isLoggingIn: boolean;
  wgerKey: string;
  setWgerKey: (val: string) => void;
  hevyUser: string;
  setHevyUser: (val: string) => void;
  onSaveServices: () => void;
}

export const Setup: React.FC<SetupProps> = ({
  isConnected,
  onLogin,
  onDisconnect,
  email,
  setEmail,
  password,
  setPassword,
  isLoggingIn,
  wgerKey,
  setWgerKey,
  hevyUser,
  setHevyUser,
  onSaveServices
}) => {
  const steps = [
    {
      title: "1. Conexión Directa",
      desc: "Usa tus credenciales de Garmin Connect para sincronizar tus datos biométricos de forma segura.",
      icon: ShieldCheck
    },
    {
      title: "2. Privacidad de Datos",
      desc: "Tus credenciales se almacenan localmente en el servidor para automatizar la sincronización diaria.",
      icon: Server
    },
    {
      title: "3. Análisis de IA",
      desc: "Una vez conectado, ATLAS analizará tu HRV, Sueño y Estrés para optimizar tu entrenamiento.",
      icon: Globe
    },
    {
      title: "4. Sincronización Automática",
      desc: "Los datos se actualizan cada 5 minutos. No necesitas importar archivos manualmente.",
      icon: Smartphone
    }
  ];

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div className="text-center space-y-2">
        <h2 className="text-3xl font-headline font-bold">Configuración de ATLAS</h2>
        <p className="text-on-surface-variant">Conecta tu ecosistema Garmin para activar el análisis inteligente.</p>
      </div>

      {/* Garmin Login Form */}
      <div className="bg-surface-container p-8 rounded-2xl border border-outline-variant/20 shadow-lg">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center text-primary">
            <Smartphone size={24} />
          </div>
          <div>
            <h3 className="text-xl font-bold">Garmin Connect</h3>
            <p className="text-sm text-on-surface-variant">
              {isConnected ? "Conectado correctamente" : "Introduce tus credenciales para sincronizar"}
            </p>
          </div>
        </div>

        {isConnected ? (
          <div className="flex items-center justify-between bg-green-500/10 p-4 rounded-xl border border-green-500/20">
            <div className="flex items-center gap-3 text-green-400">
              <ShieldCheck size={20} />
              <span className="font-medium text-sm">Sincronización Activa</span>
            </div>
            <button 
              onClick={onDisconnect}
              className="flex items-center gap-2 px-4 py-2 bg-error/10 text-error rounded-lg hover:bg-error/20 transition-colors text-sm font-bold"
            >
              <LogOut size={16} />
              Desconectar
            </button>
          </div>
        ) : (
          <form onSubmit={onLogin} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-bold text-on-surface-variant uppercase ml-1">Email</label>
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="usuario@email.com"
                  className="w-full bg-surface-container-high border border-outline-variant/30 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary/50"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-bold text-on-surface-variant uppercase ml-1">Contraseña</label>
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-surface-container-high border border-outline-variant/30 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary/50"
                  required
                />
              </div>
            </div>
            <button 
              type="submit"
              disabled={isLoggingIn}
              className="w-full bg-primary text-on-primary py-4 rounded-xl font-bold flex items-center justify-center gap-2 hover:opacity-90 transition-all disabled:opacity-50"
            >
              {isLoggingIn ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  Conectando...
                </>
              ) : (
                <>
                  <LogIn size={20} />
                  Conectar con Garmin Connect
                </>
              )}
            </button>
            <p className="text-[10px] text-center text-on-surface-variant opacity-60">
              Tus datos están protegidos. ATLAS no comparte tus credenciales con terceros.
            </p>
          </form>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {steps.map((step, i) => (
          <div key={i} className="bg-surface-container p-6 rounded-xl border border-outline-variant/10 space-y-4">
            <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center text-primary">
              <step.icon size={24} />
            </div>
            <h4 className="font-bold">{step.title}</h4>
            <p className="text-sm text-on-surface-variant leading-relaxed">{step.desc}</p>
          </div>
        ))}
      </div>

      <div className="bg-surface-container-high p-6 rounded-xl border border-outline-variant/10">
        <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4">Otros Servicios (Wger & Hevy)</h4>
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-on-surface-variant uppercase ml-1">Wger API Key</label>
              <input 
                type="password" 
                value={wgerKey}
                onChange={(e) => setWgerKey(e.target.value)}
                placeholder="Tu API Key de Wger"
                className="w-full bg-surface-container border border-outline-variant/30 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-on-surface-variant uppercase ml-1">Hevy Username</label>
              <input 
                type="text" 
                value={hevyUser}
                onChange={(e) => setHevyUser(e.target.value)}
                placeholder="Tu usuario de Hevy"
                className="w-full bg-surface-container border border-outline-variant/30 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>
          <button 
            onClick={onSaveServices}
            className="px-6 py-2 bg-surface-variant text-on-surface rounded-lg text-xs font-bold uppercase tracking-widest hover:bg-primary hover:text-on-primary transition-all"
          >
            Guardar Configuración
          </button>
        </div>
      </div>

      <div className="bg-surface-container-high p-6 rounded-xl border border-outline-variant/10">
        <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4">Tabla de Compatibilidad</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-outline-variant/20 text-on-surface-variant">
                <th className="py-2">Modelo Forerunner</th>
                <th className="py-2">Métricas Soportadas</th>
                <th className="py-2">HRV Nocturno</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/10">
              <tr>
                <td className="py-2 font-bold">955 / 965 / 255 / 265</td>
                <td className="py-2">Todas (Full Stack)</td>
                <td className="py-2 text-green-400">✅ Sí</td>
              </tr>
              <tr>
                <td className="py-2 font-bold">245 / 745 / 945</td>
                <td className="py-2">Básicas + Sueño</td>
                <td className="py-2 text-orange-400">⚠️ Limitado</td>
              </tr>
              <tr>
                <td className="py-2 font-bold">45 / 55</td>
                <td className="py-2">FC + Pasos</td>
                <td className="py-2 text-red-400">❌ No</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
