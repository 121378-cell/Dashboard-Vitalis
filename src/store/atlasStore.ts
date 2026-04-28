// ATLAS Global Store
// ==================
// Zustand store for global state management

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { 
  Biometrics, 
  ReadinessScore, 
  DailyBriefing, 
  TrainingSessionFull,
  Message,
  AppTab,
  MemoryEntry 
} from '../types';
import { CACHE_KEYS } from '../config';

interface AtlasState {
  // UI State
  activeTab: AppTab;
  isLoading: boolean;
  isOffline: boolean;
  
  // Data State
  biometrics: Biometrics | null;
  readiness: ReadinessScore | null;
  briefing: DailyBriefing | null;
  todaySession: TrainingSessionFull | null;
  chatHistory: Message[];
  memories: MemoryEntry[];
  
  // Health Connect State
  hcAvailable: boolean;
  hcPermissionsGranted: boolean;
  
  // Actions
  setActiveTab: (tab: AppTab) => void;
  setLoading: (loading: boolean) => void;
  setOffline: (offline: boolean) => void;
  setBiometrics: (data: Biometrics | null) => void;
  setReadiness: (data: ReadinessScore | null) => void;
  setBriefing: (data: DailyBriefing | null) => void;
  setTodaySession: (session: TrainingSessionFull | null) => void;
  addChatMessage: (message: Message) => void;
  clearChatHistory: () => void;
  setHcAvailable: (available: boolean) => void;
  setHcPermissionsGranted: (granted: boolean) => void;
  setMemories: (memories: MemoryEntry[]) => void;
}

export const useAtlasStore = create<AtlasState>()(
  persist(
    (set, get) => ({
      // Initial State
      activeTab: 'home',
      isLoading: false,
      isOffline: false,
      biometrics: null,
      readiness: null,
      briefing: null,
      todaySession: null,
      chatHistory: [],
      memories: [],
      hcAvailable: false,
      hcPermissionsGranted: false,
      
      // Actions
      setActiveTab: (tab) => set({ activeTab: tab }),
      setLoading: (loading) => set({ isLoading: loading }),
      setOffline: (offline) => set({ isOffline: offline }),
      setBiometrics: (data) => set({ biometrics: data }),
      setReadiness: (data) => set({ readiness: data }),
      setBriefing: (data) => set({ briefing: data }),
      setTodaySession: (session) => set({ todaySession: session }),
      
      addChatMessage: (message) => {
        const current = get().chatHistory;
        // Keep last 50 messages
        const updated = [...current, message].slice(-50);
        set({ chatHistory: updated });
      },
      
      clearChatHistory: () => set({ chatHistory: [] }),
      setHcAvailable: (available) => set({ hcAvailable: available }),
      setHcPermissionsGranted: (granted) => set({ hcPermissionsGranted: granted }),
      setMemories: (memories) => set({ memories }),
    }),
    {
      name: 'atlas-storage',
      partialize: (state) => ({
        chatHistory: state.chatHistory,
        briefing: state.briefing,
        memories: state.memories,
      }),
    }
  )
);

export default useAtlasStore;
