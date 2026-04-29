import React from 'react';
import { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useAtlasStore } from './store/atlasStore';
import { useAtlasData } from './hooks/useAtlasData';
import { useHealthConnect } from './hooks/useHealthConnect';

// Layout
import { MobileNav } from './components/layout/MobileNav';

// Dashboard
import { DailyBriefing } from './components/dashboard/DailyBriefing';

// Biometrics
import { BiometricsWidget } from './components/biometrics/BiometricsWidget';

// Chat
import { Chat } from './components/chat/Chat';

// Components for each tab
const HomeTab = () => {
  const { biometrics, readiness, briefing, loadBriefing, isLoading } = useAtlasStore();
  const { refreshAll } = useAtlasData();
  
  return (
    <div className="space-y-4 p-4 pb-24">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-[var(--color-text)]">
            ATLAS
          </h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            {new Date().toLocaleDateString('es-ES', { 
              weekday: 'long', 
              day: 'numeric',
              month: 'short'
            })}
          </p>
        </div>
        <button
          onClick={refreshAll}
          disabled={isLoading}
          className="w-10 h-10 rounded-xl glass flex items-center justify-center text-[var(--color-text-muted)] hover:text-[var(--color-primary)]"
        >
          {isLoading ? (
            <span className="animate-spin">↻</span>
          ) : (
            <span>↻</span>
          )}
        </button>
      </div>
      
      {/* Daily Briefing */}
      <DailyBriefing 
        briefing={briefing} 
        onRefresh={loadBriefing}
        isLoading={isLoading}
      />
      
      {/* Biometrics */}
      <BiometricsWidget 
        biometrics={biometrics} 
        readiness={readiness}
      />
    </div>
  );
};

const ChatTab = () => (
  <div className="h-full pb-20">
    <Chat />
  </div>
);

const TrainTab = () => (
  <div className="p-4 pb-24">
    <h2 className="text-xl font-display font-bold text-[var(--color-text)] mb-4">
      Entrenamiento
    </h2>
    <p className="text-sm text-[var(--color-text-muted)]">
      Aquí aparecerá tu sesión de hoy
    </p>
  </div>
);

const ProgressTab = () => (
  <div className="p-4 pb-24">
    <h2 className="text-xl font-display font-bold text-[var(--color-text)] mb-4">
      Progreso
    </h2>
    <p className="text-sm text-[var(--color-text-muted)]">
      Aquí verás tu progreso
    </p>
  </div>
);

const SetupTab = () => (
  <div className="p-4 pb-24">
    <h2 className="text-xl font-display font-bold text-[var(--color-text)] mb-4">
      Configuración
    </h2>
    <p className="text-sm text-[var(--color-text-muted)]">
      Configura tus servicios aquí
    </p>
  </div>
);

const TAB_COMPONENTS: Record<string, React.FC> = {
  home: HomeTab,
  chat: ChatTab,
  train: TrainTab,
  progress: ProgressTab,
  setup: SetupTab,
};

export const MobileApp = () => {
  const { activeTab, setHcAvailable } = useAtlasStore();
  const { isAvailable, requestPermissions } = useHealthConnect();
  const { refreshAll } = useAtlasData();
  
  // Initialize Health Connect
  useEffect(() => {
    const initHC = async () => {
      if (isAvailable) {
        setHcAvailable(true);
        const granted = await requestPermissions();
        if (granted) {
          refreshAll();
        }
      }
    };
    initHC();
  }, [isAvailable, setHcAvailable, requestPermissions, refreshAll]);
  
  const ActiveComponent = TAB_COMPONENTS[activeTab] || HomeTab;
  
  return (
    <div className="h-full w-full bg-[var(--color-background)] flex flex-col">
      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            <ActiveComponent />
          </motion.div>
        </AnimatePresence>
      </main>
      
      {/* Mobile Navigation */}
      <MobileNav />
    </div>
  );
};